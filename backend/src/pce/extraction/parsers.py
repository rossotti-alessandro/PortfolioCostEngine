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

from ..engine.isin import ISIN_RE, is_valid_isin
from ..engine.money import parse_amount, parse_percent
from .layout import Line, PageInfo, read_pdf
from .models import DocType, DocumentProfile, Evidence, ExtractionResult, Fact
from .vocab import (
    AMOUNT,
    DOC_TYPE_KEYWORDS,
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
    return Evidence(page=line.page, bbox=[round(v, 2) for v in bbox], page_width=page.width, page_height=page.height,
                    snippet=line.text[:300], engine=line.engine, confidence=line.confidence)


def _amount_cells(line: Line) -> list[tuple[int, Decimal]]:
    out = []
    for i, c in enumerate(line.cells):
        t = c.text.strip()
        if AMOUNT.match(t) and any(ch.isdigit() for ch in t):
            try:
                out.append((i, parse_amount(t)))
            except ValueError:
                continue
    return out


# ---------------------------------------------------------------- classification
def classify(pages: list[PageInfo]) -> DocumentProfile:
    first = " ".join(ln.text for ln in pages[0].lines) if pages else ""
    alltext = " ".join(ln.text for p in pages for ln in p.lines)
    low_first, low_all = first.lower(), alltext.lower()
    scores: dict[str, float] = {}
    for dt, kws in DOC_TYPE_KEYWORDS.items():
        scores[dt] = sum(2.0 if k in low_first else (0.5 if k in low_all else 0.0) for k in kws)
    if ISIN_RE.search(alltext) and "market value" in low_all:
        scores["portfolio_statement"] += 1.0
    best = max(scores, key=lambda k: scores[k]) if scores else "unknown"
    score = scores.get(best, 0.0)
    doc_type = DocType(best) if score >= 2.0 else DocType.UNKNOWN
    warnings = []
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
    for ln in (ln for p in pages for ln in p.lines):
        t = ln.text
        ds = find_dates(t)
        if not ds:
            continue
        if re.search(r"period|periodo|zeitraum|période", t, re.I) and len(ds) >= 2 and not period_start:
            period_start, period_end = ds[0], ds[1]
        elif re.search(r"valuation|valuta|bewertung|évaluation|as of|stichtag|valid from|production", t, re.I) and not as_of:
            as_of = ds[0]
    currency = None
    m = re.search(r"(?:reference currency|currency|values in|valori in|währung)\s*:?\s*(CHF|EUR|USD|GBP)", alltext, re.I)
    if m:
        currency = m.group(1).upper()
    return DocumentProfile(doc_type=doc_type, type_score=score, institution=institution, jurisdiction=jurisdiction,
                           language=lang, as_of=as_of or period_end, period_start=period_start, period_end=period_end,
                           currency=currency, page_count=len(pages),
                           engines=sorted({p.engine for p in pages}), warnings=warnings)


# ---------------------------------------------------------------- PDF parsers
def parse_positions_pdf(pages: list[PageInfo], prof: DocumentProfile) -> list[Fact]:
    facts: list[Fact] = []
    ccy = prof.currency or "CHF"
    in_table = False
    for page in pages:
        for ln in page.lines:
            low = ln.text.lower()
            if "isin" in low and ("value" in low or "valore" in low or "wert" in low):
                in_table = True
                m = re.search(r"(?:value|valore|wert)\s+(CHF|EUR|USD)", ln.text, re.I)
                if m:
                    ccy = m.group(1).upper()
                continue
            isin_idx = next((i for i, c in enumerate(ln.cells) if is_valid_isin(c.text.strip())), None)
            amounts = _amount_cells(ln)
            if isin_idx is not None and amounts:
                isin = ln.cells[isin_idx].text.strip()
                name = " ".join(c.text for c in ln.cells[:isin_idx]).strip()
                nums = [a for a in amounts if a[0] > isin_idx]
                qty = nums[0][1] if len(nums) >= 3 else None
                price = nums[1][1] if len(nums) >= 3 else None
                mv_idx, mv = nums[-1] if nums else amounts[-1]
                facts.append(Fact(key=f"position:{isin}", kind="position", field="market_value", label=name, value=str(mv),
                                  currency=ccy, isin=isin,
                                  extra={"quantity": str(qty) if qty is not None else None,
                                         "price": str(price) if price is not None else None},
                                  evidence=_ev(ln, page)))
                continue
            if in_table and amounts and len(ln.cells) <= 3:
                label = ln.cells[0].text
                if re.search(r"^total", label, re.I):
                    facts.append(Fact(key="total:assets", kind="doc_total", field="total_assets", label=label,
                                      value=str(amounts[-1][1]), currency=ccy, evidence=_ev(ln, page)))
                    in_table = False
                elif re.search(r"account|cash|liquid|conto|konto|compte", label, re.I):
                    facts.append(Fact(key=f"position:cash:{label}", kind="position", field="market_value", label=label,
                                      value=str(amounts[-1][1]), currency=ccy, extra={"asset_class": "CASH"},
                                      evidence=_ev(ln, page)))
    return facts


def parse_cost_report(pages: list[PageInfo], prof: DocumentProfile) -> list[Fact]:
    facts: list[Fact] = []
    section = "service"
    for page in pages:
        for ln in page.lines:
            low = ln.text.lower()
            if "third-party" in low or "product cost" in low or "costi di prodotto" in low or "produktkosten" in low:
                section = "product"
            elif "inducement" in low or "retrocession" in low and len(ln.cells) == 1:
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
                facts.append(Fact(key="meta:average_assets", kind="meta", field="average_assets", label=label,
                                  value=str(value), currency=prof.currency or "CHF", evidence=_ev(ln, page)))
                continue
            if re.search(r"^total", label, re.I):
                facts.append(Fact(key=f"total:{section}", kind="doc_total", field=f"total_{section}", label=label,
                                  value=str(value), currency=prof.currency or "CHF", evidence=_ev(ln, page)))
                continue
            if section == "product":
                facts.append(Fact(key="reported:product_costs", kind="reported", field="reported_product_costs",
                                  label=label, value=str(value), currency=prof.currency or "CHF",
                                  measurement="estimated", evidence=_ev(ln, page)))
                continue
            if re.search(r"retrocession|retrozession|rétrocession|retrocessioni|inducement", label, re.I):
                facts.append(Fact(key="reported:retrocessions", kind="reported", field="retrocessions_received",
                                  label=label, value=str(value), currency=prof.currency or "CHF",
                                  fee_code="RETRO_RECEIVED", measurement="observed", evidence=_ev(ln, page)))
                continue
            code = map_fee_label(label)
            if code:
                facts.append(Fact(key=f"fee:{code}", kind="fee_observed", field="annual_amount", label=label,
                                  value=str(value), currency=prof.currency or "CHF", fee_code=code,
                                  measurement="observed",
                                  extra={"period_start": prof.period_start, "period_end": prof.period_end},
                                  evidence=_ev(ln, page)))
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
            desc = " ".join(c.text for c in ln.cells[1:amounts[-1][0]])
            code = map_fee_label(desc)
            if not code:
                continue
            per_year = 4 if QUARTER_WORDS.search(desc) else None
            facts.append(Fact(key=f"debit:{dates[0]}:{code}", kind="cash_debit", field="debit_amount", label=desc,
                              value=str(amounts[-1][1]), currency=ccy or "CHF", fee_code=code, measurement="observed",
                              extra={"booking_date": dates[0], "periods_per_year": per_year},
                              evidence=_ev(ln, page)))
    return facts


_RULE_PATTERNS = [
    (re.compile(r"advisory|consulenza|beratung", re.I), "ADVISORY_FEE", "aum"),
    (re.compile(r"management fee|mandate fee|gestione", re.I), "MGMT_DISCRETIONARY", "aum"),
    (re.compile(r"custody|custodia|depot|garde", re.I), "CUSTODY_FEE", "custody_eligible"),
    (re.compile(r"brokerage|courtage|intermediazione", re.I), "BROKERAGE", "trade_notional"),
    (re.compile(r"transfer of securities|trasferimento|übertrag|transfert", re.I), "TRANSFER_OUT", "per_position"),
]


def parse_tariff(pages: list[PageInfo], prof: DocumentProfile) -> list[Fact]:
    facts: list[Fact] = []
    last_code = None
    entity = None
    for page in pages:
        for ln in page.lines:
            label = ln.cells[0].text if ln.cells else ""
            if re.search(r"issuing entity|entità|herausgeber|émetteur", label, re.I) and len(ln.cells) > 1:
                entity = ln.cells[1].text
                juris = next((c for c, p in JURISDICTION_HINTS if p.search(entity)), None)
                facts.append(Fact(key="meta:issuing_entity", kind="meta", field="issuing_entity", label=label,
                                  value=None, extra={"entity": entity, "jurisdiction": juris}, evidence=_ev(ln, page)))
                continue
            pm = PERCENT.search(ln.text)
            is_min = re.search(r"minimum|minimo|mindest", label, re.I)
            code = base = None
            for pat, c, b in _RULE_PATTERNS:
                if pat.search(label):
                    code, base = c, b
                    break
            if is_min and last_code and len(ln.cells) > 1:
                amt = _amount_cells(ln)
                if amt:
                    per = ("quarter" if re.search(r"quarter|trimestr|quartal", label, re.I)
                           else "trade" if re.search(r"per trade|per ordine|pro auftrag|par ordre", label, re.I) else "year")
                    ccy = next((c for c in CURRENCIES if c in ln.text), prof.currency)
                    facts.append(Fact(key=f"rule:{last_code}:minimum", kind="fee_rule", field="minimum", label=label,
                                      value=str(amt[-1][1]), currency=ccy, fee_code=last_code,
                                      measurement="contractual", extra={"per": per}, evidence=_ev(ln, page)))
                continue
            if code and pm:
                facts.append(Fact(key=f"rule:{code}:rate", kind="fee_rule", field="rate_pct", label=label,
                                  value=str(parse_percent(pm.group(0))), fee_code=code, measurement="contractual",
                                  extra={"base": base, "cash_excluded": bool(re.search(r"cash excluded|esclusa liquidità|ohne liquidität", label, re.I))},
                                  evidence=_ev(ln, page)))
                last_code = code
            elif code == "TRANSFER_OUT":
                amt = _amount_cells(ln)
                if amt:
                    ccy = next((c for c in CURRENCIES if c in ln.text), prof.currency)
                    facts.append(Fact(key="rule:TRANSFER_OUT:per_position", kind="fee_rule", field="per_position",
                                      label=label, value=str(amt[-1][1]), currency=ccy, fee_code="TRANSFER_OUT",
                                      measurement="contractual", evidence=_ev(ln, page)))
    if entity is None:
        prof.warnings.append("Issuing legal entity not found: the tariff's jurisdiction must be confirmed manually.")
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
        (re.compile(r"of which.*management fee|davon verwaltungs|di cui.*gestione", re.I), "FUND_MGMT_FEE", "estimated"),
        (re.compile(r"management fees and other administrative|ongoing charges|spese correnti|laufende kosten", re.I), "FUND_ONGOING", "estimated"),
        (re.compile(r"^transaction costs|costi di transazione|transaktionskosten", re.I), "FUND_TRANSACTION", "estimated"),
        (re.compile(r"performance fee|commissioni di performance|erfolgsgebühr", re.I), "FUND_PERFORMANCE", "estimated"),
        (re.compile(r"entry costs|costi di ingresso|einstiegskosten", re.I), "FUND_ENTRY_CHARGE", "maximum"),
        (re.compile(r"exit costs|costi di uscita|ausstiegskosten", re.I), "FUND_EXIT_CHARGE", "maximum"),
    ]
    for page in pages:
        for ln in page.lines:
            label = ln.cells[0].text if ln.cells else ""
            if re.search(r"total costs if you exit after 1 year", label, re.I):
                amt = _amount_cells(ln)
                if amt:
                    facts.append(Fact(key="kid:illustration_1y", kind="product_cost", field="illustration_amount",
                                      label=label, value=str(amt[-1][1]), isin=isin, fee_code="KID_ILLUSTRATION",
                                      measurement="illustrative", extra={"example_investment": "10000"},
                                      evidence=_ev(ln, page)))
                continue
            pm = PERCENT.search(" ".join(c.text for c in ln.cells[1:])) if len(ln.cells) > 1 else None
            if not pm:
                continue
            for pat, code, meas in mapping:
                if pat.search(label):
                    facts.append(Fact(key=f"kid:{code}", kind="product_cost", field="rate_pct", label=label,
                                      value=str(parse_percent(pm.group(0))), isin=isin, fee_code=code,
                                      measurement=meas,
                                      extra={"included_in": "FUND_ONGOING" if code == "FUND_MGMT_FEE" else None,
                                             "document_date": prof.as_of},
                                      evidence=_ev(ln, page)))
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
                    facts.append(Fact(key="sp:distribution", kind="product_cost", field="rate_pct", label=label,
                                      value=str(parse_percent(pm.group(0))), isin=isin, fee_code="SP_ONGOING",
                                      measurement="maximum" if re.search(r"up to|fino a|bis zu", rest, re.I) else "estimated",
                                      extra={"note": "distribution fee embedded in product price"},
                                      evidence=_ev(ln, page)))
            if re.search(r"margin|estimated value|fair value", label, re.I) and len(ln.cells) > 1:
                undisclosed = re.search(r"not disclosed|non comunicat|nicht ausgewiesen", rest, re.I)
                pm = PERCENT.search(rest)
                facts.append(Fact(key="sp:entry_cost", kind="product_cost", field="rate_pct", label=label,
                                  value=None if undisclosed or not pm else str(parse_percent(pm.group(0))),
                                  isin=isin, fee_code="SP_ENTRY_COST",
                                  measurement="unknown" if undisclosed or not pm else "estimated",
                                  evidence=_ev(ln, page)))
    return facts


# ---------------------------------------------------------------- spreadsheet
def parse_positions_xlsx(data: bytes) -> ExtractionResult:
    import io

    wb = load_workbook(io.BytesIO(data), data_only=True, read_only=False)
    facts: list[Fact] = []
    prof = DocumentProfile(doc_type=DocType.PORTFOLIO_STATEMENT, type_score=0.0, page_count=len(wb.worksheets),
                           engines=["openpyxl"])
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
                facts.append(Fact(key=f"fx:{vals[0]}", kind="meta", field="fx_rate", label=str(r[0].value),
                                  value=_cell_decimal(r[1].value),
                                  evidence=Evidence(sheet=ws.title, cell=r[1].coordinate, snippet=f"{r[0].value} {r[1].value}",
                                                    engine="openpyxl")))
        if not header_row:
            continue
        prof.doc_type = DocType.PORTFOLIO_STATEMENT
        prof.type_score = 3.0
        mv_col = next((c for k, c in cols.items() if "market value" in k and ("chf" in k or (prof.currency or "").lower() in k)), None)
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
            ev = Evidence(sheet=ws.title, cell=mv_cell.coordinate,
                          snippet=f"{name} | {isin} | {mv_cell.value}", engine="openpyxl",
                          bbox=None, page=None)
            ev_row = f"A{mv_cell.row}:{get_column_letter(ws.max_column)}{mv_cell.row}"
            if str(name).strip().lower().startswith("total"):
                facts.append(Fact(key="total:assets", kind="doc_total", field="total_assets", label=str(name),
                                  value=_cell_decimal(mv_cell.value), currency=prof.currency or "CHF",
                                  extra={"row_range": ev_row}, evidence=ev))
                continue
            asset_class = str(r[cls_col - 1].value).upper() if cls_col else None
            if isin and not is_valid_isin(isin):
                prof.warnings.append(f"Row {mv_cell.row}: '{isin}' fails the ISIN check digit; needs review.")
            facts.append(Fact(key=f"position:{isin or 'cash:' + str(name)}", kind="position", field="market_value",
                              label=str(name), value=_cell_decimal(mv_cell.value), currency=prof.currency or "CHF",
                              isin=isin or None, extra={"asset_class": asset_class, "row_range": ev_row}, evidence=ev))
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
    if prof.doc_type == DocType.UNKNOWN:
        prof.warnings.append("Could not classify this document; choose its type manually.")
    if "tesseract-ocr" in prof.engines:
        prof.warnings.append("Scanned pages were read with OCR: confirm each value against the image.")
    return ExtractionResult(profile=prof, facts=facts, extractor_version=EXTRACTOR_VERSION), pages
