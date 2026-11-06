"""Deterministic, layout-generic parsers for born-digital and OCR'd documents.

These parsers do not know any specific bank. They rely on: valid ISINs, the
multilingual fee vocabulary, amount/percent patterns and table headers. Anything
they cannot place lands as a warning for human review, never as a guessed value.
"""

from __future__ import annotations

import re
from decimal import Decimal

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from ..finance.isin import ISIN_RE, is_valid_isin
from ..finance.money import parse_amount, parse_percent
from .layout import Line, PageInfo, read_pdf
from .models import DocType, DocumentProfile, Evidence, ExtractionResult, Fact
from .vocab import (
    AMOUNT,
    DOC_TYPE_KEYWORDS,
    FEE_SECTION,
    FX_RATE,
    JURISDICTION_HINTS,
    LANG_HINTS,
    PERCENT,
    QUARTER_WORDS,
    find_dates,
    map_fee_label,
)

EXTRACTOR_VERSION = "pce-rules-0.1"
CURRENCIES = ("CHF", "EUR", "USD", "GBP")


def _ev(line: Line, page: PageInfo, cells=None) -> Evidence:
    bbox = line.bbox_of(cells) if cells else line.bbox
    return Evidence(
        page=line.page,
        bbox=[round(v, 2) for v in bbox],
        page_width=page.width,
        page_height=page.height,
        snippet=line.text[:300],
        engine=line.engine,
        confidence=line.confidence,
    )


_CCY_SYMBOL = re.compile(r"^([-−(]?)\s*(?:[£$€]|GBP)\s*")
_SYMBOL_CCY = {"£": "GBP", "€": "EUR", "$": "USD"}
_QTY_PRICE_VALUE = re.compile(r"quantit|stück|menge|nombre|units", re.I)
_PRICE_4DP = re.compile(r"^[£$€]?\s*(\d{1,3}(?:,\d{3})*\.\d{2,6})$")


def _amount_cells(line: Line) -> list[tuple[int, Decimal]]:
    out = []
    for i, c in enumerate(line.cells):
        t = _CCY_SYMBOL.sub(r"\1", c.text.strip())  # "£9,399.51", "-£21.59", "$ 44.37"
        if AMOUNT.match(t) and any(ch.isdigit() for ch in t):
            try:
                out.append((i, parse_amount(t)))
            except ValueError:
                continue
    return out


def _fx_facts(pages: list[PageInfo]) -> list[Fact]:
    """Exchange rates printed on the document ("FX rate USD/CHF ...: 0.8000"): the only rates the
    engine uses to convert, so every converted amount traces back to a rate on a page."""
    facts: list[Fact] = []
    for page in pages:
        for ln in page.lines:
            m = FX_RATE.search(ln.text)
            if not m:
                continue
            base, quote = m.group(1).upper(), m.group(2).upper()
            try:
                rate = parse_amount(m.group(3).rstrip(".,"))
            except ValueError:
                continue
            facts.append(
                Fact(
                    key=f"fx:{base}{quote}",
                    kind="meta",
                    field="fx_rate",
                    label=f"{base}/{quote}",
                    value=str(rate),
                    extra={"base": base, "quote": quote},
                    evidence=_ev(ln, page),
                )
            )
    return facts


def _isin_at(line: Line) -> tuple[int, str, str] | None:
    """(cell index, ISIN, text before the ISIN in that cell). The ISIN may share a cell with the
    name when the columns sit close together."""
    for i, c in enumerate(line.cells):
        for m in ISIN_RE.finditer(c.text.upper()):
            if is_valid_isin(m.group(0)):
                return i, m.group(0), c.text[: m.start()].strip()
    return None


def _fee_fact(label: str, value: Decimal, ln: Line, page: PageInfo, prof: DocumentProfile) -> Fact | None:
    code = map_fee_label(label)
    if not code:
        return None
    return Fact(
        key=f"fee:{code}",
        kind="fee_observed",
        field="annual_amount",
        label=label,
        value=str(value),
        currency=prof.currency or "CHF",
        fee_code=code,
        measurement="observed",
        extra={"period_start": prof.period_start, "period_end": prof.period_end},
        evidence=_ev(ln, page),
    )


# ---------------------------------------------------------------- classification
_FACTSHEET = re.compile(
    r"\bfact ?sheet\b|\bmonthly report\b|\bscheda prodotto\b|\bfonds-?portrait\b|\breporting mensuel\b"
)
_AS_OF = re.compile(
    r"valuation|valuta|bewertung|évaluation|as of|stichtag|valid from|production|gültig ab|"
    r"valido dal|erstellt|realizzazione",
    re.I,
)
_LEGAL_ENTITY = re.compile(
    r"\b[A-Z][\w&.\-]*(?: [A-Z(][\w&.()\-]*){0,6} "
    r"(?:Limited|Ltd\.?|S\.A\.|SA|AG|GmbH|plc|S\.p\.A\.|SGR S\.p\.A\.|LLC)(?!\w)"
)


def classify(pages: list[PageInfo]) -> DocumentProfile:
    first = " ".join(ln.text for ln in pages[0].lines).replace("’", "'") if pages else ""
    alltext = " ".join(ln.text for p in pages for ln in p.lines).replace("’", "'")
    low_first, low_all = first.lower(), alltext.lower()
    scores: dict[str, float] = {}
    for dt, kws in DOC_TYPE_KEYWORDS.items():
        scores[dt] = sum(2.0 if k in low_first else (0.5 if k in low_all else 0.0) for k in kws)
    if ISIN_RE.search(alltext) and "market value" in low_all:
        scores["portfolio_statement"] += 1.0
    if any(
        re.search(r"(?:quantity|units)\W+price\W+(?:\(\W\)\s*)?(?:market )?value", ln.text.lower())
        for p in pages
        for ln in p.lines
    ):
        scores["portfolio_statement"] += 1.0  # a holdings table header, as UK/US statements print it
    best = max(scores, key=lambda k: scores[k]) if scores else "unknown"
    score = scores.get(best, 0.0)
    doc_type = DocType(best) if score >= 2.0 else DocType.UNKNOWN
    warnings = []
    if _FACTSHEET.search(low_first) and doc_type in (DocType.PORTFOLIO_STATEMENT, DocType.KID):
        # A fund factsheet lists a fund's holdings and costs, not the client's: never a statement or a KID.
        doc_type = DocType.UNKNOWN
        warnings.append(
            "Looks like a fund factsheet: use the KID for costs and the bank statement for holdings."
        )
    ranked = sorted(scores.values(), reverse=True)
    if doc_type != DocType.UNKNOWN and len(ranked) > 1 and ranked[1] >= score - 0.5 and ranked[1] > 0:
        warnings.append("Document type is close between two candidates; please confirm.")
    institution = None
    for ln in pages[0].lines if pages else []:
        t = ln.cells[0].text
        letters = sum(ch.isalpha() for ch in t)
        if ln.confidence >= 0.6 and letters >= 0.6 * len(t.replace(" ", "")) and len(t) > 3:
            institution = t
            break
    if pages and not (institution and _LEGAL_ENTITY.search(institution)):
        # A KID or price list often opens with its title; the legal entity is named in the text.
        m = _LEGAL_ENTITY.search(first)
        institution = m.group(0) if m else institution
    header = " ".join(ln.text for ln in pages[0].lines[:12]) if pages else ""
    jurisdiction = None
    for code, pat in JURISDICTION_HINTS:
        if pat.search(header):
            jurisdiction = code
            break
    lang = max(LANG_HINTS, key=lambda k: len(LANG_HINTS[k].findall(alltext)))
    if not LANG_HINTS[lang].search(alltext):
        lang = "en"
    as_of = period_start = period_end = None
    seq = [ln.text for p in pages for ln in p.lines]
    for i, t in enumerate(seq):
        ds = find_dates(t)
        if not ds and _AS_OF.search(t) and i + 1 < len(seq):
            ds = find_dates(seq[i + 1])  # "Dieses Dokument wurde erstellt / am 03 September 2026."
        if not ds:
            continue
        if re.search(r"period|periodo|zeitraum|période", t, re.I) and len(ds) >= 2 and not period_start:
            period_start, period_end = ds[0], ds[1]
        elif _AS_OF.search(t) and not as_of:
            as_of = ds[0]
    currency = None
    m = re.search(
        r"(?:reference currency|currency|values in|valori in|währung)\s*:?\s*(CHF|EUR|USD|GBP)", alltext, re.I
    )
    if m:
        currency = m.group(1).upper()
    return DocumentProfile(
        doc_type=doc_type,
        type_score=score,
        institution=institution,
        jurisdiction=jurisdiction,
        language=lang,
        as_of=as_of or period_end,
        period_start=period_start,
        period_end=period_end,
        currency=currency,
        page_count=len(pages),
        engines=sorted({p.engine for p in pages}),
        warnings=warnings,
    )


# ---------------------------------------------------------------- PDF parsers
def _no_isin_position(ln: Line, name: str | None = None) -> tuple[str, Decimal, Decimal, Decimal] | None:
    """Name | quantity | price | value (more columns, such as cost and change, may follow), accepted
    only when quantity x price matches the value (±1%), so a row of unrelated numbers is never
    mistaken for a holding. UK and US statements often print no ISIN; the holding is kept and its
    product costs stay unknown until it is identified."""
    first = 0 if name else 1
    name = (name or ln.cells[0].text).strip()
    if not re.search(r"[A-Za-z]{3}", name) or re.search(r"^total|^cash|^money held", name, re.I):
        return None
    texts = [c.text.strip() for c in ln.cells]
    for j in range(first, len(texts) - 2):
        try:
            qty = parse_amount(_CCY_SYMBOL.sub(r"\1", texts[j]))
            pm = _PRICE_4DP.match(texts[j + 1])
            mv = parse_amount(_CCY_SYMBOL.sub(r"\1", texts[j + 2]))
        except (ValueError, ArithmeticError):
            continue
        price = Decimal(pm.group(1).replace(",", "")) if pm else None
        if price is not None and mv > 0 and abs(qty * price - mv) <= mv * Decimal("0.01"):
            return name, qty, price, mv
    return None


def parse_positions_pdf(pages: list[PageInfo], prof: DocumentProfile) -> list[Fact]:
    facts: list[Fact] = _fx_facts(pages)
    ccy = prof.currency or "CHF"
    in_table = in_fees = no_isin_table = False
    in_weights: int | None = None
    for page in pages:
        for li, ln in enumerate(page.lines):
            low = ln.text.lower()
            if FEE_SECTION.search(ln.text) and len(ln.cells) == 1:
                in_fees, in_table = True, False  # activity statements also list the fees charged
                continue
            if in_fees:
                amounts = _amount_cells(ln)
                if amounts and len(ln.cells) >= 2 and not re.search(r"^total", ln.cells[0].text, re.I):
                    ff = _fee_fact(ln.cells[0].text, amounts[-1][1], ln, page, prof)
                    if ff:
                        facts.append(ff)
                continue
            if "isin" in low and re.search(r"weight|gewicht|peso|poids|proceeds|profit/loss|realised", low):
                in_weights = page.number  # X-ray weights and disposal (capital gains) tables are not holdings
                continue
            if in_weights == page.number and _isin_at(ln) is not None:
                continue
            if no_isin_table and re.search(r"\bweight\b|\(%\)", low) and not _QTY_PRICE_VALUE.search(low):
                in_table = no_isin_table = False  # an allocation table follows: its numbers are not holdings
                continue
            if "isin" in low and ("value" in low or "valore" in low or "wert" in low):
                in_table = True
                m = re.search(r"(?:value|valore|wert)\s+(CHF|EUR|USD)", ln.text, re.I)
                if m:
                    ccy = m.group(1).upper()
                continue
            if _QTY_PRICE_VALUE.search(low) and re.search(r"price|prezzo|kurs|cours", low) and not in_fees:
                in_table, no_isin_table = True, True  # "Quantity | Price | Value" without an ISIN column
                sym = next((k for k in _SYMBOL_CCY if k in ln.text), None)
                ccy = _SYMBOL_CCY[sym] if sym else ccy  # "Price (£) | Value (£)": the rows carry no symbol
                continue
            hit = _isin_at(ln)
            amounts = _amount_cells(ln)
            wrapped = (  # long names wrap: "MI Somerset … Accumulation" / "5,649.12 | £1.52 | £8,593.18"
                page.lines[li - 1].text
                if li and len(ln.cells) == 3 and len(page.lines[li - 1].cells) == 1
                else None
            )
            if (
                hit is None
                and no_isin_table
                and (len(ln.cells) >= 4 or wrapped)
                and (pos := _no_isin_position(ln, wrapped))
            ):
                name, qty, price, mv = pos
                sym = next((k for k in _SYMBOL_CCY if k in ln.text), None)
                facts.append(
                    Fact(
                        key=f"position:name:{name}",
                        kind="position",
                        field="market_value",
                        label=name,
                        value=str(mv),
                        currency=_SYMBOL_CCY[sym] if sym else ccy,
                        isin=None,
                        extra={"quantity": str(qty), "price": str(price), "no_isin": True},
                        evidence=_ev(ln, page),
                    )
                )
                continue
            if hit is not None and amounts:
                isin_idx, isin, prefix = hit
                name = " ".join([*(c.text for c in ln.cells[:isin_idx]), prefix]).strip()
                nums = [a for a in amounts if a[0] > isin_idx]
                qty = nums[0][1] if len(nums) >= 3 else None
                price = nums[1][1] if len(nums) >= 3 else None
                _mv_idx, mv = nums[-1] if nums else amounts[-1]
                facts.append(
                    Fact(
                        key=f"position:{isin}",
                        kind="position",
                        field="market_value",
                        label=name,
                        value=str(mv),
                        currency=ccy,
                        isin=isin,
                        extra={
                            "quantity": str(qty) if qty is not None else None,
                            "price": str(price) if price is not None else None,
                        },
                        evidence=_ev(ln, page),
                    )
                )
                continue
            if no_isin_table and in_table and re.match(r"money held as cash|cash (?:balance|held)", low):
                # Cash rows wrap: "Money held as cash within your … (see" / "£24,409.75" on the next line.
                src = ln if amounts else (page.lines[li + 1] if li + 1 < len(page.lines) else ln)
                cash = amounts or _amount_cells(src)
                if cash:
                    sym = next((k for k in _SYMBOL_CCY if k in src.text), None)
                    facts.append(
                        Fact(
                            key=f"position:cash:{page.number}:{li}",
                            kind="position",
                            field="market_value",
                            label=ln.cells[0].text,
                            value=str(cash[-1][1]),
                            currency=_SYMBOL_CCY[sym] if sym else ccy,
                            extra={"asset_class": "CASH"},
                            evidence=_ev(src, page),
                        )
                    )
                continue
            # "Total | 388,714.25 | 374,716.14 | 3.74": value, then cost and change columns
            wide_total = no_isin_table and len(ln.cells) > 3 and low.startswith("total")
            if in_table and amounts and (len(ln.cells) <= 3 or wide_total):
                label = ln.cells[0].text
                sym = next((k for k in _SYMBOL_CCY if k in ln.text), None)
                if re.search(r"^total", label, re.I):
                    prev = next((f for f in facts if f.key == "total:assets"), None)
                    value = amounts[0 if wide_total else -1][1] + (
                        Decimal(prev.value) if prev and no_isin_table else 0
                    )
                    if prev and no_isin_table:  # one statement, several accounts: their totals add up
                        facts.remove(prev)
                    facts.append(
                        Fact(
                            key="total:assets",
                            kind="doc_total",
                            field="total_assets",
                            label=label,
                            value=str(value),
                            currency=_SYMBOL_CCY[sym] if sym else ccy,
                            extra={"sum_of_account_totals": True} if prev and no_isin_table else {},
                            evidence=_ev(ln, page),
                        )
                    )
                    in_table = False
                elif re.search(r"account|cash|liquid|conto|konto|compte", label, re.I):
                    facts.append(
                        Fact(
                            key=f"position:cash:{label}",
                            kind="position",
                            field="market_value",
                            label=label,
                            value=str(amounts[-1][1]),
                            currency=ccy,
                            extra={"asset_class": "CASH"},
                            evidence=_ev(ln, page),
                        )
                    )
    return facts


def parse_cost_report(pages: list[PageInfo], prof: DocumentProfile) -> list[Fact]:
    facts: list[Fact] = _fx_facts(pages)
    section = "service"
    for page in pages:
        for ln in page.lines:
            low = ln.text.lower()
            if (
                "third-party" in low
                or "product cost" in low
                or "costi di prodotto" in low
                or "produktkosten" in low
            ):
                section = "product"
            elif re.search(r"inducement|incentiv", low) or ("retrocession" in low and len(ln.cells) == 1):
                section = "inducements"
            amounts = _amount_cells(ln)
            if not amounts or len(ln.cells) < 2:
                if amounts and re.search(r"average assets|patrimonio medio|durchschnittliches", low):
                    pass
                else:
                    continue
            label = ln.cells[0].text
            value = amounts[-1][1]
            if re.search(r"average assets|patrimonio medio|durchschnittliches vermögen", label, re.I):
                facts.append(
                    Fact(
                        key="meta:average_assets",
                        kind="meta",
                        field="average_assets",
                        label=label,
                        value=str(value),
                        currency=prof.currency or "CHF",
                        evidence=_ev(ln, page),
                    )
                )
                continue
            if re.search(r"^total", label, re.I):
                facts.append(
                    Fact(
                        key=f"total:{section}",
                        kind="doc_total",
                        field=f"total_{section}",
                        label=label,
                        value=str(value),
                        currency=prof.currency or "CHF",
                        evidence=_ev(ln, page),
                    )
                )
                continue
            if (
                re.search(
                    r"retrocession|retrozession|rétrocession|retrocessioni|inducement|incentiv", label, re.I
                )
                or section == "inducements"
            ):
                facts.append(
                    Fact(
                        key="reported:retrocessions",
                        kind="reported",
                        field="retrocessions_received",
                        label=label,
                        value=str(value),
                        currency=prof.currency or "CHF",
                        fee_code="RETRO_RECEIVED",
                        measurement="observed",
                        evidence=_ev(ln, page),
                    )
                )
                continue
            if section == "product":
                facts.append(
                    Fact(
                        key="reported:product_costs",
                        kind="reported",
                        field="reported_product_costs",
                        label=label,
                        value=str(value),
                        currency=prof.currency or "CHF",
                        measurement="estimated",
                        evidence=_ev(ln, page),
                    )
                )
                continue
            ff = _fee_fact(label, value, ln, page, prof)
            if ff:
                facts.append(ff)
    return facts


def parse_cash_statement(pages: list[PageInfo], prof: DocumentProfile) -> list[Fact]:
    facts: list[Fact] = []
    ccy = prof.currency
    for page in pages:
        for ln in page.lines:
            if not ccy:
                m = re.search(r"\b(CHF|EUR|USD)\b", ln.text)
                if m and re.search(r"conto|account|konto|compte", ln.text, re.I):
                    ccy = m.group(1)
            dates = find_dates(ln.cells[0].text) if ln.cells else []
            amounts = _amount_cells(ln)
            if not dates or not amounts or len(ln.cells) < 3:
                continue
            desc = " ".join(c.text for c in ln.cells[1 : amounts[-1][0]])
            code = map_fee_label(desc)
            if not code:
                continue
            per_year = 4 if QUARTER_WORDS.search(desc) else None
            facts.append(
                Fact(
                    key=f"debit:{dates[0]}:{code}",
                    kind="cash_debit",
                    field="debit_amount",
                    label=desc,
                    value=str(amounts[-1][1]),
                    currency=ccy or "CHF",
                    fee_code=code,
                    measurement="observed",
                    extra={"booking_date": dates[0], "periods_per_year": per_year},
                    evidence=_ev(ln, page),
                )
            )
    return facts


_RULE_PATTERNS = [
    (re.compile(r"advisory|consulenza|beratung", re.I), "ADVISORY_FEE", "aum"),
    (
        re.compile(r"management fee|mandate fee|gestione|vermögensverwaltung|asset management", re.I),
        "MGMT_DISCRETIONARY",
        "aum",
    ),
    (  # before custody: "commissione sul controvalore dell'operazione" is a trading fee
        re.compile(r"brokerage|courtage|intermediazione|negoziazione|transaction fee|dell'operazione", re.I),
        "BROKERAGE",
        "trade_notional",
    ),
    (re.compile(r"custody|custodia|depot|garde", re.I), "CUSTODY_FEE", "custody_eligible"),
    (
        re.compile(r"foreign exchange|devisen|cambi\b|opérations de change", re.I),
        "FX_COMMISSION",
        "fx_notional",
    ),
    (
        re.compile(r"transfer of securities|trasferimento|übertrag|transfert", re.I),
        "TRANSFER_OUT",
        "per_position",
    ),
]
# Rows that carry a % or an amount but are not the fee itself (corpus spot check, 2026-11-06).
_NOT_A_RATE = re.compile(
    r"zuschl|surcharge|supplement|maggiorazion|corporate action|operazioni sul capitale|kapitalma(ss|ß)nahm|"
    r"mindestbetrag|minimum investment|investimento minimo|^total|^gesamt|^max\b|\bmax\.? \d",
    re.I,
)
_NUMBERING = re.compile(r"^\d+(?:\.\d+)*\.?\s+")
_BAND_FIRST = re.compile(r"^(?:up to|bis|fino a|für die ersten|first|jusqu'à)\b", re.I)
_BAND_OPEN = re.compile(r"^(?:\+\s*)?(?:over|above|über|oltre|au-delà|für beträge über)\b", re.I)
_NUM = r"\d{1,3}(?:[ '’.,]\d{3})*(?:[.,]\d+)?"
_BAND_RANGE = re.compile(rf"{_NUM}\s*(?:m|mio|k)?\s*[–-]\s*({_NUM})\s*(m|mio|k)?\b", re.I)
_BAND_NUM = re.compile(rf"({_NUM})\s*(m|mio|k)?\b", re.I)
_MAX_RATE_PCT = Decimal("5")  # above this a "rate" is a discount, a surcharge or a misread
_CCY_AMOUNT = re.compile(r"\b(CHF|EUR|USD|GBP)\s*(\d[\d'’.,]*)")
_ENTITY = re.compile(
    r"issued by ([A-Z][\w&.\- ]{2,80}?(?:S\.A\.|SA|AG|plc|Ltd|S\.p\.A\.|Genossenschaft))", re.I
)
_BANKISH = re.compile(r"\bbank|banca|banque|raiffeisen|kantonalbank|sparkasse", re.I)


def _band_upper(label: str) -> tuple[bool, Decimal | None]:
    """(is a band row, upper bound in units; None = open-ended top band)."""

    def num(raw: str, unit: str | None) -> Decimal:
        v = parse_amount(raw.rstrip(".,"))
        return v * {"m": 1_000_000, "mio": 1_000_000, "k": 1_000}.get((unit or "").lower(), 1)

    t = label.strip()
    if _BAND_OPEN.search(t):
        return True, None
    try:  # "250,000" alone is ambiguous: not a band we can bound, never a reason to drop the document
        if _BAND_FIRST.search(t) and (m := _BAND_NUM.search(t)):
            return True, num(m.group(1), m.group(2))
        if m := _BAND_RANGE.search(t):
            return True, num(m.group(1), m.group(2))
    except ValueError:
        return False, None
    return False, None


def _rule_for(label: str) -> tuple[str | None, str | None]:
    for pat, c, b in _RULE_PATTERNS:
        if pat.search(label):
            return c, b
    return None, None


def parse_tariff(pages: list[PageInfo], prof: DocumentProfile) -> list[Fact]:
    """Price lists: rates, bands, minimums and the issuing legal entity. A row without its own fee
    label inherits the section heading above it (e.g. "Depotgebühren" → "Grundgebühr pro Jahr").
    When a section offers several prices (columns or packages) only the first is used as the rate;
    the others are kept as alternatives for the analyst, never silently chosen."""
    facts: list[Fact] = []
    seen: set[str] = set()
    section = section_base = last_code = None
    entity_fact: Fact | None = None
    alltext = " ".join(ln.text for p in pages for ln in p.lines)
    booked = re.search(r"booked in (\w+)", alltext, re.I)

    def add(f: Fact) -> None:
        if f.key in seen:
            f.key = f"{f.key}:alt{sum(k.startswith(f.key) for k in seen)}"
            f.field = "rate_alternative" if f.field == "rate_pct" else f.field
        seen.add(f.key)
        facts.append(f)

    for page in pages:
        for ln in page.lines:
            label = ln.cells[0].text if ln.cells else ""
            if entity_fact is None and (m := _ENTITY.search(ln.text)):
                ent = m.group(1).strip()
                juris = next((c for c, p in JURISDICTION_HINTS if p.search(ent)), None)
                if not juris and booked:
                    juris = next((c for c, p in JURISDICTION_HINTS if p.search(booked.group(1))), None)
                entity_fact = Fact(
                    key="meta:issuing_entity",
                    kind="meta",
                    field="issuing_entity",
                    label="Issuing entity",
                    value=None,
                    extra={"entity": ent, "jurisdiction": juris or prof.jurisdiction},
                    evidence=_ev(ln, page),
                )
                add(entity_fact)
            if re.search(r"issuing entity|entità|herausgeber|émetteur", label, re.I) and len(ln.cells) > 1:
                ent = ln.cells[1].text
                juris = next((c for c, p in JURISDICTION_HINTS if p.search(ent)), None)
                facts[:] = [f for f in facts if f.key != "meta:issuing_entity"]
                seen.discard("meta:issuing_entity")
                entity_fact = Fact(
                    key="meta:issuing_entity",
                    kind="meta",
                    field="issuing_entity",
                    label=label,
                    value=None,
                    extra={"entity": ent, "jurisdiction": juris},
                    evidence=_ev(ln, page),
                )
                add(entity_fact)
                continue
            pm = PERCENT.search(" ".join(c.text for c in ln.cells[1:])) if len(ln.cells) > 1 else None
            numbered = bool(_NUMBERING.match(label))  # "2.1 Courtage für Aktien, andere …" is a heading
            if len(ln.cells) == 1 and not PERCENT.search(label) and len(label) < (100 if numbered else 60):
                hl = _NUMBERING.sub("", label)
                heading = (numbered or hl.isupper() or not re.search(r"[()‘’'\".,:;•]|^\W", hl)) and not (
                    "|" in hl or hl[:1].islower()  # running page headers and wrapped sentences
                )
                hcode, hbase = _rule_for(hl) if heading else (None, None)
                if hcode:  # a fee heading opens a section; sub-headings ("Standard model") keep it
                    section, section_base, last_code = hcode, hbase, hcode
                continue
            if _NOT_A_RATE.search(label) or _NOT_A_RATE.search(" ".join(c.text for c in ln.cells[1:2])):
                continue
            code, base = _rule_for(label)
            is_min = re.search(r"minimum|minimo|mindest", label, re.I)
            if is_min and (last_code or section) and len(ln.cells) > 1:
                target = last_code or section
                amt = _amount_cells(ln)
                cm = _CCY_AMOUNT.search(" ".join(c.text for c in ln.cells[1:]))
                try:
                    value = amt[0][1] if amt else (parse_amount(cm.group(2).rstrip(".,")) if cm else None)
                except ValueError:  # ambiguous separator: skip this value, keep the document
                    value = None
                if value is not None:
                    per = (
                        "quarter"
                        if re.search(r"quarter|trimestr|quartal", label, re.I)
                        else "trade"
                        if re.search(r"per trade|per ordine|pro auftrag|par ordre", label, re.I)
                        or target == "BROKERAGE"
                        else "year"
                    )
                    ccy = cm.group(1) if cm else next((c for c in CURRENCIES if c in ln.text), prof.currency)
                    add(
                        Fact(
                            key=f"rule:{target}:minimum",
                            kind="fee_rule",
                            field="minimum",
                            label=label,
                            value=str(value),
                            currency=ccy,
                            fee_code=target,
                            measurement="contractual",
                            extra={"per": per},
                            evidence=_ev(ln, page),
                        )
                    )
                continue
            is_band, upper = _band_upper(label)
            all_pct = [str(parse_percent(x)) for x in PERCENT.findall(" ".join(c.text for c in ln.cells[1:]))]
            if pm and parse_percent(pm.group(0)) > _MAX_RATE_PCT:
                continue
            if is_band and pm and section:
                add(
                    Fact(
                        key=f"rule:{section}:tier:{upper if upper is not None else 'open'}",
                        kind="fee_rule",
                        field="tier_rate_pct",
                        label=label,
                        value=str(parse_percent(pm.group(0))),
                        fee_code=section,
                        measurement="contractual",
                        extra={
                            "up_to": str(upper) if upper is not None else None,
                            "base": section_base,
                            "columns": len(all_pct),
                            "all_columns_pct": all_pct,
                        },
                        evidence=_ev(ln, page, [ln.cells[0], ln.cells[1]]),
                    )
                )
                last_code = section
                continue
            if (
                not code
                and not label[:1].islower()
                and pm
                and len(label) < 60
                and re.search(r"fee|gebühr|commission|p\.a\.|pro jahr", label, re.I)
            ):
                code = section
            base = base or section_base
            if code and code != "TRANSFER_OUT" and pm:
                add(
                    Fact(
                        key=f"rule:{code}:rate",
                        kind="fee_rule",
                        field="rate_pct",
                        label=label,
                        value=str(parse_percent(pm.group(0))),
                        fee_code=code,
                        measurement="contractual",
                        extra={
                            "base": base,
                            "cash_excluded": bool(
                                re.search(r"cash excluded|esclusa liquidità|ohne liquidität", label, re.I)
                            ),
                            "columns": len(all_pct),
                            "all_columns_pct": all_pct,
                        },
                        evidence=_ev(ln, page),
                    )
                )
                last_code = code
            elif code == "TRANSFER_OUT":
                amt = [a for a in _amount_cells(ln) if a[1] > 0]  # "(2)" is a footnote, not -2
                if amt:
                    ccy = next((c for c in CURRENCIES if c in ln.text), prof.currency)
                    add(
                        Fact(
                            key="rule:TRANSFER_OUT:per_position",
                            kind="fee_rule",
                            field="per_position",
                            label=label,
                            value=str(amt[-1][1]),
                            currency=ccy,
                            fee_code="TRANSFER_OUT",
                            measurement="contractual",
                            evidence=_ev(ln, page),
                        )
                    )
    if entity_fact is None and prof.institution and _BANKISH.search(prof.institution) and pages:
        first = next((ln for ln in pages[0].lines if prof.institution in ln.text), None)
        if first:
            add(
                Fact(
                    key="meta:issuing_entity",
                    kind="meta",
                    field="issuing_entity",
                    label="Issuing entity (document header)",
                    value=None,
                    extra={"entity": prof.institution, "jurisdiction": prof.jurisdiction, "inferred": True},
                    evidence=_ev(first, pages[0]),
                )
            )
            entity_fact = facts[-1]
    if entity_fact is None:
        prof.warnings.append(
            "Issuing legal entity not found: the tariff's jurisdiction must be confirmed manually."
        )
    if any(f.field == "rate_alternative" or (f.extra or {}).get("columns", 1) > 1 for f in facts):
        prof.warnings.append("Several price columns or packages: confirm which one applies to this client.")
    return facts


def parse_kid(pages: list[PageInfo], prof: DocumentProfile) -> list[Fact]:
    facts: list[Fact] = []
    isin = None
    for page in pages:
        for ln in page.lines:
            for m in ISIN_RE.findall(ln.text.upper()):
                if is_valid_isin(m):
                    isin = isin or m
    if not isin:
        prof.warnings.append("No valid ISIN found in the KID: product costs cannot be linked to a holding.")
        return facts
    mapping = [
        (
            re.compile(r"of which.*management fee|davon verwaltungs|di cui.*gestione", re.I),
            "FUND_MGMT_FEE",
            "estimated",
        ),
        (
            re.compile(
                # KID tables wrap the label, so the first cell often holds only its first words.
                r"^management fees and|ongoing charges|spese correnti|laufende kosten|"
                r"^verwaltungsgebühren|^commissioni di gestione|^frais de gestion",
                re.I,
            ),
            "FUND_ONGOING",
            "estimated",
        ),
        (
            re.compile(r"^transaction costs|costi di transazione|transaktionskosten", re.I),
            "FUND_TRANSACTION",
            "estimated",
        ),
        (
            re.compile(
                r"performance fee|commissioni di performance|erfolgsgebühr|commissions liées aux", re.I
            ),
            "FUND_PERFORMANCE",
            "estimated",
        ),
        (re.compile(r"entry costs|costi di ingresso|einstiegskosten", re.I), "FUND_ENTRY_CHARGE", "maximum"),
        (re.compile(r"exit costs|costi di uscita|ausstiegskosten", re.I), "FUND_EXIT_CHARGE", "maximum"),
    ]
    for page in pages:
        for li, ln in enumerate(page.lines):
            label = ln.cells[0].text if ln.cells else ""
            if re.search(
                r"total costs if you exit after 1 year|^gesamtkosten$|^costi totali$|^coûts totaux$",
                label,
                re.I,
            ):
                amt = _amount_cells(ln)
                if not amt and len(ln.cells) > 1:  # "20 USD": amount with a trailing currency
                    m = re.match(r"([\d'’.,]+)\s*(?:USD|EUR|CHF|GBP)$", ln.cells[1].text.strip())
                    try:
                        amt = [(1, parse_amount(m.group(1)))] if m else []
                    except ValueError:
                        amt = []
                if amt:
                    facts.append(
                        Fact(
                            key="kid:illustration_1y",
                            kind="product_cost",
                            field="illustration_amount",
                            label=label,
                            value=str(amt[-1][1]),
                            isin=isin,
                            fee_code="KID_ILLUSTRATION",
                            measurement="illustrative",
                            extra={"example_investment": "10000"},
                            evidence=_ev(ln, page),
                        )
                    )
                continue
            pm = PERCENT.search(" ".join(c.text for c in ln.cells[1:])) if len(ln.cells) > 1 else None
            src = ln
            if not pm and li + 1 < len(page.lines) and any(p.search(label) for p, _c, _m in mapping):
                # The value sits on the line below its wrapped label ("Commissioni di gestione e" / "1,20 %").
                nxt = page.lines[li + 1]
                nlabel = nxt.cells[0].text if nxt.cells else ""
                if not any(p.search(nlabel) for p, _c, _m in mapping):
                    pm, src = PERCENT.search(nxt.text), nxt
            if not pm:
                continue
            for pat, code, meas in mapping:
                if pat.search(label) and not any(f.key == f"kid:{code}" for f in facts):
                    facts.append(
                        Fact(
                            key=f"kid:{code}",
                            kind="product_cost",
                            field="rate_pct",
                            label=label,
                            value=str(parse_percent(pm.group(0))),
                            isin=isin,
                            fee_code=code,
                            measurement=meas,
                            extra={
                                "included_in": "FUND_ONGOING" if code == "FUND_MGMT_FEE" else None,
                                "document_date": prof.as_of,
                            },
                            evidence=_ev(src, page),
                        )
                    )
                    break
    return facts


def parse_termsheet(pages: list[PageInfo], prof: DocumentProfile) -> list[Fact]:
    facts: list[Fact] = []
    isin = None
    for page in pages:
        for ln in page.lines:
            for m in ISIN_RE.findall(ln.text.upper()):
                if is_valid_isin(m):
                    isin = isin or m
    for page in pages:
        for ln in page.lines:
            label = ln.cells[0].text if ln.cells else ""
            rest = " ".join(c.text for c in ln.cells[1:])
            if re.search(r"distribution fee|commissione di distribuzione|vertriebs", label, re.I):
                pm = PERCENT.search(rest)
                if pm:
                    facts.append(
                        Fact(
                            key="sp:distribution",
                            kind="product_cost",
                            field="rate_pct",
                            label=label,
                            value=str(parse_percent(pm.group(0))),
                            isin=isin,
                            fee_code="SP_ONGOING",
                            measurement="maximum"
                            if re.search(r"up to|fino a|bis zu", rest, re.I)
                            else "estimated",
                            extra={"note": "distribution fee embedded in product price"},
                            evidence=_ev(ln, page),
                        )
                    )
            if re.search(r"margin|estimated value|fair value", label, re.I) and len(ln.cells) > 1:
                undisclosed = re.search(r"not disclosed|non comunicat|nicht ausgewiesen", rest, re.I)
                pm = PERCENT.search(rest)
                facts.append(
                    Fact(
                        key="sp:entry_cost",
                        kind="product_cost",
                        field="rate_pct",
                        label=label,
                        value=None if undisclosed or not pm else str(parse_percent(pm.group(0))),
                        isin=isin,
                        fee_code="SP_ENTRY_COST",
                        measurement="unknown" if undisclosed or not pm else "estimated",
                        evidence=_ev(ln, page),
                    )
                )
    return facts


# ---------------------------------------------------------------- spreadsheet
def parse_positions_xlsx(data: bytes) -> ExtractionResult:
    import io

    wb = load_workbook(io.BytesIO(data), data_only=True, read_only=False)
    facts: list[Fact] = []
    prof = DocumentProfile(
        doc_type=DocType.PORTFOLIO_STATEMENT,
        type_score=0.0,
        page_count=len(wb.worksheets),
        engines=["openpyxl"],
    )
    for ws in wb.worksheets:
        header_row, cols = None, {}
        for r in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 40)):
            vals = [str(c.value).strip().lower() if c.value is not None else "" for c in r]
            if "isin" in vals:
                header_row = r[0].row
                for c, v in zip(r, vals, strict=False):
                    cols[v] = c.column
                break
            if r[0].value and r[0].row == 1:
                prof.institution = str(r[0].value)
            joined = " ".join(vals)
            for code, pat in JURISDICTION_HINTS:
                if pat.search(joined) and not prof.jurisdiction:
                    prof.jurisdiction = code
            if vals and vals[0].startswith("valuation date") and len(vals) > 1:
                ds = find_dates(str(r[1].value))
                prof.as_of = ds[0] if ds else None
            if vals and vals[0].startswith("reference currency") and len(vals) > 1:
                prof.currency = str(r[1].value).upper()
            if vals and vals[0].startswith("fx rate") and len(vals) > 1:
                facts.append(
                    Fact(
                        key=f"fx:{vals[0]}",
                        kind="meta",
                        field="fx_rate",
                        label=str(r[0].value),
                        value=_cell_decimal(r[1].value),
                        evidence=Evidence(
                            sheet=ws.title,
                            cell=r[1].coordinate,
                            snippet=f"{r[0].value} {r[1].value}",
                            engine="openpyxl",
                        ),
                    )
                )
        if not header_row:
            continue
        prof.doc_type = DocType.PORTFOLIO_STATEMENT
        prof.type_score = 3.0
        mv_col = next(
            (
                c
                for k, c in cols.items()
                if "market value" in k and ("chf" in k or (prof.currency or "").lower() in k)
            ),
            None,
        )
        name_col = next((c for k, c in cols.items() if k in ("description", "name", "security", "titolo")), 1)
        isin_col = cols["isin"]
        cls_col = next((c for k, c in cols.items() if "asset class" in k), None)
        for r in ws.iter_rows(min_row=header_row + 1, max_row=ws.max_row):
            name = r[name_col - 1].value
            if name is None:
                continue
            mv_cell = r[mv_col - 1] if mv_col else None
            if mv_cell is None or mv_cell.value is None:
                continue
            isin = (r[isin_col - 1].value or "").strip()
            ev = Evidence(
                sheet=ws.title,
                cell=mv_cell.coordinate,
                snippet=f"{name} | {isin} | {mv_cell.value}",
                engine="openpyxl",
                bbox=None,
                page=None,
            )
            ev_row = f"A{mv_cell.row}:{get_column_letter(ws.max_column)}{mv_cell.row}"
            if str(name).strip().lower().startswith("total"):
                facts.append(
                    Fact(
                        key="total:assets",
                        kind="doc_total",
                        field="total_assets",
                        label=str(name),
                        value=_cell_decimal(mv_cell.value),
                        currency=prof.currency or "CHF",
                        extra={"row_range": ev_row},
                        evidence=ev,
                    )
                )
                continue
            asset_class = str(r[cls_col - 1].value).upper() if cls_col else None
            if isin and not is_valid_isin(isin):
                prof.warnings.append(f"Row {mv_cell.row}: '{isin}' fails the ISIN check digit; needs review.")
            facts.append(
                Fact(
                    key=f"position:{isin or 'cash:' + str(name)}",
                    kind="position",
                    field="market_value",
                    label=str(name),
                    value=_cell_decimal(mv_cell.value),
                    currency=prof.currency or "CHF",
                    isin=isin or None,
                    extra={"asset_class": asset_class, "row_range": ev_row},
                    evidence=ev,
                )
            )
    return ExtractionResult(profile=prof, facts=facts, extractor_version=EXTRACTOR_VERSION)


def _cell_decimal(v) -> str | None:
    """Spreadsheet numbers arrive as binary floats; round-trip via repr at 10 dp then normalise."""
    if v is None:
        return None
    if isinstance(v, (int,)):
        return str(Decimal(v))
    if isinstance(v, float):
        return str(Decimal(repr(v)).quantize(Decimal("0.0000000001")).normalize())
    return str(parse_amount(str(v)))


# ---------------------------------------------------------------- entry point
PARSERS = {
    DocType.PORTFOLIO_STATEMENT: parse_positions_pdf,
    DocType.COST_REPORT: parse_cost_report,
    DocType.CASH_STATEMENT: parse_cash_statement,
    DocType.TARIFF: parse_tariff,
    DocType.KID: parse_kid,
    DocType.TERMSHEET: parse_termsheet,
}


def extract(filename: str, data: bytes) -> tuple[ExtractionResult, list[PageInfo]]:
    name = filename.lower()
    if name.endswith((".xlsx", ".xlsm")):
        return parse_positions_xlsx(data), []
    if not name.endswith(".pdf") and not data.startswith(b"%PDF"):
        raise ValueError("unsupported file type: upload PDF or XLSX")
    pages = read_pdf(data)
    prof = classify(pages)
    parser = PARSERS.get(prof.doc_type)
    facts = parser(pages, prof) if parser else []
    ent = next(
        (f.extra for f in facts if f.key == "meta:issuing_entity" and not f.extra.get("inferred")), None
    )
    if ent:  # the stated legal entity beats a title line picked up as the header
        prof.institution = ent["entity"]
    if prof.doc_type == DocType.UNKNOWN:
        prof.warnings.append("Could not classify this document; choose its type manually.")
    if "tesseract-ocr" in prof.engines:
        prof.warnings.append("Scanned pages were read with OCR: confirm each value against the image.")
    return ExtractionResult(profile=prof, facts=facts, extractor_version=EXTRACTOR_VERSION), pages
