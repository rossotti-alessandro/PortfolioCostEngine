"""From reviewed facts to cost ledger, checks, missing-document requests and scenarios.

Pure function of its inputs (no DB, no network) so it is fully testable and reproducible.
Every atom cites the fact ids it came from; the UI resolves those to page + rectangle.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field, replace
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from .extraction.vocab import FEE_LABEL_NAMES
from .finance.checklist import hidden_costs
from .finance.isin import is_synthetic, is_valid_isin
from .finance.ledger import AtomRole, FeeAtom, Incidence, Layer, LedgerSummary, Measurement, aggregate
from .finance.money import ZERO, D, bps_of, money
from .finance.scenarios import (
    LAYER_BY_CODE,
    Comparison,
    HoldingInput,
    ProductRate,
    compare,
    internal_economics,
    product_atoms,
)
from .finance.tariff import FeeRule, Tariff, TierMethod

ENGINE_VERSION = "pce-engine-0.2"
BASE_CCY = "CHF"
FX_REVIEW_GAP = Decimal("0.01")  # printed vs reference rate further apart than 1%: a review point
TAX_CODES = {"VAT_ON_FEES", "STAMP_DUTY_CH"}
EXCLUDED_FROM_COMPARISON = {
    "STAMP_DUTY_CH": "Swiss stamp duty is a tax that applies at any Swiss bank; "
    "excluded from the like-for-like comparison."
}
SERVICE_CORE = [
    ("SERVICE", "Management or advisory fee (if any)", Layer.SERVICE),
    ("CUSTODY_FEE", "Custody fee", Layer.CUSTODY),
    ("BROKERAGE", "Brokerage", Layer.TRADING),
]
SERVICE_CODES = {"ADVISORY_FEE", "MGMT_DISCRETIONARY", "ALL_IN_FEE", "EAM_FEE", "PLATFORM_FIXED"}
LEGAL_SUFFIX = re.compile(r"(?<!\w)(SA|AG|S\.A\.|Ltd|plc|LLC|Europe|GmbH|S\.p\.A\.)(?!\w)\.?", re.I)


def listed_assets(holdings: list, total: object) -> object | None:
    """CHF assets for a list or header.

    A holding with no CHF value (no printed rate, or a market value that was never priced) does not
    count. When none are valued the stored total is 0, and publishing that 0 renders ``CHF 0`` for a
    book that was not valued. Missing stays missing.
    """
    if not any(h.get("value") not in (None, "") for h in holdings):
        return None
    return total


def inst_key(name: str | None) -> str:
    if not name:
        return "Unknown institution"
    return re.sub(r"\s+", " ", LEGAL_SUFFIX.sub("", name)).strip(" ,")


# ETF before the structured-product words. "Xtrackers" contains "tracker", and a UCITS ETF is not
# a certificate: those names are funds, so a missing KID is an ongoing charge, not an issuer margin.
# An exchange-traded commodity (ETC) carries a running fee like an ETF, so it is classed with them.
_ETF_NAME = re.compile(r"\bet[fc]\b|xtrackers|\bspdr\b")
# Words that only a structured product uses. The weak ones (note, tracker, convertible) lose to fund and
# bond words: "US Treasury Note" is a bond and "Global Convertible Bond Fund" is a fund.
_STRUCTURED_NAME = re.compile(
    r"certificate|certificato|zertifikat|barrier|mini-?future|reverse convertible|\bwarrants?\b"
)
_WEAK_STRUCTURED_NAME = re.compile(r"convertible|\bnotes?\b|\btracker\b")
_FUND_NAME = re.compile(r"fund|fonds|fondo|sicav|\bfds?\b")
_BOND_NAME = re.compile(r"\bbond\b|obbligazion|anleihe|government|treasury|\bbtp\b")
# Listed options and futures: their costs are trading costs, there is no ongoing product charge.
_DERIVATIVE_NAME = re.compile(r"\boptions?\b|\bopzion[ei]\b|\bcall\b|\bput\b|\bfutures?\b")
# Physical precious metal (bars, coins, metal accounts): custody, not an embedded product cost.
_METAL_NAME = re.compile(r"gold|silver|platin|palladi|\boro\b|argento|edelmetall")
_PHYSICAL_NAME = re.compile(r"\bbars?\b|barren|lingott|\bkg\b|\boz\b|unze|\bcoins?\b|münze|account|konto")
# A bank's own category column, in the languages of the corpus. Order matters: first match wins.
_CATEGORY = [
    ("STRUCTURED", re.compile(r"struct|certif|zertif|strutt")),
    ("ETF", re.compile(r"\bet[fpc]s?\b")),
    ("FUND", re.compile(r"fund|fond|sicav|ucits|hedge|private equity")),
    ("DERIVATIVE", re.compile(r"deriv|option|future|opzion")),
    ("COMMODITY", re.compile(r"commodit|precious|metal|metall|materie prime|rohstoff")),
    ("BOND", re.compile(r"bond|fixed income|obblig|anleih|oblig|reddito fisso|renten")),
    ("EQUITY", re.compile(r"equit|stock|share|azion|aktie|action")),
    ("CASH", re.compile(r"cash|liquid|account|conto|konto|compte|deposit")),
]
_PACKAGED = ("ETF", "FUND", "STRUCTURED")


def _class_from_name(name: str) -> str:
    n = name.lower()
    if _ETF_NAME.search(n):
        return "ETF"
    if _STRUCTURED_NAME.search(n):
        return "STRUCTURED"
    # "FD" / "FDS" is how US statements abbreviate a fund, including a bond fund. Checked before the
    # bond words so "Total Return Bond FD" is a fund, not a plain bond.
    if _FUND_NAME.search(n):
        return "FUND"
    if _BOND_NAME.search(n):
        return "BOND"
    if _DERIVATIVE_NAME.search(n):
        return "DERIVATIVE"
    if _WEAK_STRUCTURED_NAME.search(n):
        return "STRUCTURED"
    if re.search(r"\bucits\b", n):
        return "ETF"
    if _METAL_NAME.search(n) and _PHYSICAL_NAME.search(n):
        return "COMMODITY"
    if re.search(r"account|cash|liquid|conto|konto|compte", n):
        return "CASH"
    return "EQUITY"


def _class_from_category(given: str) -> str | None:
    g = given.lower()
    return next((cls for cls, rx in _CATEGORY if rx.search(g)), None)


def infer_asset_class(name: str, given: str | None, authoritative: bool = False) -> tuple[str, bool]:
    """A holding's class, and whether it was inferred rather than stated.

    ``authoritative`` is a public-register class (FIRDS CFI, OpenFIGI): kept as is. Otherwise ``given``
    is the bank's own category column, which is often the exposure, not the instrument: an ETF listed
    under "Equities" is still an ETF with an ongoing charge, so a fund, ETF or certificate name wins over
    an equity, bond or commodity category. An unrecognised category falls back to the name.
    """
    if given and authoritative:
        g = given.upper()
        return ("STRUCTURED" if g.startswith("STRUCT") else g), False
    by_name = _class_from_name(name)
    cat = _class_from_category(given) if given else None
    if cat is None:
        return by_name, True
    if cat in ("EQUITY", "BOND", "COMMODITY") and by_name in _PACKAGED:
        return by_name, True
    return cat, False


# Fewer days than this and a report says too little about the year to extrapolate (SC-7.21): a one-day
# report × 365 turned CHF 1'900 of fees into CHF 693'500. Its amounts count as printed, as a lower bound.
MIN_ANNUALISE_DAYS = 28


def _report_period(ps: str | None, pe: str | None) -> tuple[int | None, str]:
    """Days a report covers and how to treat them: full, partial (annualise), short, reversed or unknown."""
    if not (ps and pe):
        return None, "unknown"
    days = (date.fromisoformat(pe) - date.fromisoformat(ps)).days + 1
    if days <= 0:
        return None, "reversed"  # an extraction slip; annualising by a negative count flips every sign
    if 360 <= days <= 366:
        return days, "full"
    return days, "short" if days < MIN_ANNUALISE_DAYS else "partial"


def _product_gap(holding: dict) -> bool:
    """True when a missing KID must be an unknown product-cost atom, never a silent zero.

    Equity, cash, plain bonds, listed options and futures and physical metal have no ongoing charge, so
    they get no made-up TER (a bond fund is classed FUND by its name, and a KID for the bond's ISIN
    makes it a FUND before this check; SC-9.10). A fund, ETF or structured product does, with or without an
    ISIN (a certificate read without its ISIN was a silent zero before SC-7.21). Any
    other holding does only when its ISIN is checksum-valid, so a joined KID can be asked for by
    share class.
    """
    kind = holding["asset_class"]
    if kind in ("CASH", "EQUITY", "BOND", "DERIVATIVE", "COMMODITY"):
        return False
    if kind in ("FUND", "ETF", "STRUCTURED"):
        return True
    isin = holding.get("isin") or ""
    return bool(isin and is_valid_isin(isin))


def _gap_fee(holding: dict) -> tuple[str, Layer, str]:
    """Fee code, layer and note for a product whose KID was not joined."""
    if holding["asset_class"] in ("FUND", "ETF"):
        return (
            "FUND_ONGOING",
            Layer.PRODUCT,
            "No KID for this exact share class. The ongoing charge is unknown, not zero.",
        )
    if holding["asset_class"] == "STRUCTURED":
        return (
            "SP_ENTRY_COST",
            Layer.STRUCTURED,
            "No KID / termsheet for this exact share class.",
        )
    return (
        "FUND_ONGOING",
        Layer.PRODUCT,
        "No KID joined for this ISIN. Product cost is unknown, not zero.",
    )


def _statement_signature(ik: str, as_of: str | None, facts: list[dict]) -> tuple | None:
    """What makes two statements the same: bank, date and the multiset of (instrument, value, currency)."""
    rows = sorted(
        (f.get("isin") or f["label"], str(D(f["value"]).normalize()), f.get("currency") or "")
        for f in facts
        if f["kind"] == "position" and f["value"] is not None
    )
    return (ik, as_of, tuple(rows)) if rows else None


def _merge_lots(holdings: list[dict]) -> list[dict]:
    """One row per institution and instrument for the product-cost join; ``lots`` keeps the source rows.

    Two lots of one ISIN would otherwise give two atoms with one id. A lot without a CHF value leaves the
    merged value unknown, never a partial sum.
    """
    merged: dict[tuple[str, str], dict] = {}
    for h in holdings:
        k = (h["institution"], h["isin"] or h["name"])
        if k not in merged:
            merged[k] = {**h, "lots": [h]}
            continue
        m = merged[k]
        m["lots"].append(h)
        m["value"] = None if m["value"] is None or h["value"] is None else m["value"] + h["value"]
    return list(merged.values())


def _pick_product_docs(
    documents: list[dict], by_doc: dict[int, list[dict]], checks: list[Check]
) -> tuple[dict[str, list[dict]], dict[str, dict]]:
    """One KID or termsheet per ISIN: the newest ``as_of``, the lowest document id on a tie.

    Two versions of one KID (a re-download, another language, last year's) must not add their charges
    twice. The others are named in a check, and a warning when their figures differ.
    """
    per_isin: dict[str, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
    doc_by_id = {d["id"]: d for d in documents}
    for d in documents:
        if d["doc_type"] in ("kid", "termsheet"):
            for f in by_doc[d["id"]]:
                if f.get("isin"):
                    per_isin[f["isin"]][d["id"]].append(f)
    facts_out: dict[str, list[dict]] = {}
    meta_out: dict[str, dict] = {}
    for isin, per_doc in per_isin.items():
        order = sorted(per_doc, key=lambda i: ((doc_by_id[i].get("profile") or {}).get("as_of") or "", -i))
        keep, others = order[-1], order[:-1]
        facts_out[isin], meta_out[isin] = per_doc[keep], doc_by_id[keep]
        if not others:
            continue
        figures = {(f["fee_code"], f.get("measurement"), f["value"]) for f in per_doc[keep]}
        differ = any((f["fee_code"], f.get("measurement"), f["value"]) not in figures
                     for i in others for f in per_doc[i])  # fmt: skip
        names = ", ".join(doc_by_id[i]["filename"] for i in others)
        checks.append(
            Check(
                f"duplicate:product:{isin}",
                f"{isin}: more than one product document",
                "warn" if differ else "info",
                f"Costs taken from {doc_by_id[keep]['filename']} (the most recent). Not used: {names}."
                + (" Their figures differ: check which version applies." if differ else ""),
                [f["id"] for f in per_doc[keep]],
            )
        )
    return facts_out, meta_out


@dataclass
class Check:
    key: str
    title: str
    status: str  # pass | warn | fail | info
    detail: str
    fact_ids: list[int] = field(default_factory=list)


@dataclass
class MissingRequest:
    key: str
    priority: int  # 1 = highest
    institution: str | None
    title: str
    ask_for: str
    reason: str
    blocks: list[str]
    assets_affected: Decimal | None
    document_type: str


def _d(v: Any) -> Decimal | None:
    return None if v in (None, "") else D(v)


def _ser(o: Any) -> Any:
    if isinstance(o, Decimal):
        return str(o)
    if isinstance(o, dict):
        return {k: _ser(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_ser(v) for v in o]
    if hasattr(o, "value") and isinstance(o.value, str):
        return o.value
    return o


def atom_dict(a: FeeAtom, role: AtomRole | None, aum: Decimal | None) -> dict:
    return {
        "id": a.atom_id,
        "fee_code": a.fee_code,
        "fee_label": FEE_LABEL_NAMES.get(a.fee_code, a.fee_code),
        "layer": a.layer.value,
        "label": a.label,
        "institution": a.institution,
        "instrument_id": a.instrument_id,
        "amount": None if a.amount is None else str(a.amount.quantize(Decimal("0.01"))),
        "bps": None if a.amount is None or not aum else str(bps_of(a.amount, aum)),
        "measurement": a.measurement.value,
        "incidence": a.incidence.value,
        "recurring": a.recurring,
        "included_in": a.included_in,
        "corroborates": a.corroborates,
        "role": role.value if role else None,
        "rate_bps": None if a.rate_bps is None else str(a.rate_bps),
        "basis_amount": None if a.basis_amount is None else str(a.basis_amount),
        "evidence_fact_ids": [int(x) for x in a.evidence_ids if str(x).isdigit()],
        "formula": a.formula,
        "note": a.note,
        "materiality": a.materiality,
    }


def summary_dict(s: LedgerSummary, atoms: list[FeeAtom]) -> dict:
    return {
        "total_known": str(s.total_known.quantize(Decimal("0.01"))),
        "billed_known": str(s.billed_known.quantize(Decimal("0.01"))),
        "embedded_known": str(s.embedded_known.quantize(Decimal("0.01"))),
        "one_off_known": str(s.one_off_known.quantize(Decimal("0.01"))),
        "total_bps": None if s.total_bps is None else str(s.total_bps),
        "scope_aum": None if s.scope_aum is None else str(s.scope_aum),
        "is_complete": s.is_complete,
        "verified_share": None
        if s.verified_share is None
        else str(s.verified_share.quantize(Decimal("0.001"))),
        "by_measurement": {k: str(v.quantize(Decimal("0.01"))) for k, v in s.by_measurement.items()},
        "by_layer": {k: str(v.quantize(Decimal("0.01"))) for k, v in s.by_layer.items()},
        "by_institution": {k: str(v.quantize(Decimal("0.01"))) for k, v in s.by_institution.items()},
        "by_instrument": {k: str(v.quantize(Decimal("0.01"))) for k, v in s.by_instrument.items()},
        "unknown": [a.atom_id for a in s.unknown],
        "warnings": s.warnings,
        "atoms": [atom_dict(a, s.roles.get(a.atom_id), s.scope_aum) for a in atoms],
    }


_NO_CHF_TOTAL = (
    "No CHF total: no exchange rate into CHF is printed on the documents. "
    "Assets are not shown as zero, and no saving is claimed."
)
_NO_KNOWN_COST = "No saving is claimed: no current cost is known. Unknown costs are not treated as zero."


def _claim_saving(cmp: Comparison, *, valued: bool, known: Decimal) -> None:
    """A saving needs a CHF asset base and at least one known current cost. Otherwise say so."""
    reasons: list[str] = []
    if not valued:
        reasons.append(_NO_CHF_TOTAL)
    if known <= 0:
        reasons.append(_NO_KNOWN_COST)
    if not reasons:
        return
    cmp.saving_claimed = False
    # Drop caveats that describe a difference we are refusing to show.
    cmp.caveats = reasons


def analyse(prospect: dict, documents: list[dict], facts: list[dict], proposal: dict) -> dict:
    """documents: {id, filename, doc_type, profile}; facts: {id, document_id, key, kind, field, label, value,
    currency, isin, fee_code, measurement, extra, status}; proposal: see demo.spec.PROPOSAL_DEFAULTS."""
    # Fixed order (by id), so a shuffled input gives byte-identical output and the same snapshot hash.
    documents = sorted(documents, key=lambda d: d["id"])
    live = sorted((f for f in facts if f.get("status") != "rejected"), key=lambda f: f["id"])
    by_doc: dict[int, list[dict]] = defaultdict(list)
    for f in live:
        by_doc[f["document_id"]].append(f)
    checks: list[Check] = []
    requests: list[MissingRequest] = []

    # ------------------------------------------------------------ exchange rates (only those printed
    # on the client's own documents, so every converted amount traces back to a page)
    fx: dict[str, dict[str, tuple[Decimal, int]]] = defaultdict(dict)
    for d in documents:
        ik = inst_key((d.get("profile") or {}).get("institution"))
        for f in by_doc[d["id"]]:
            m = re.search(r"([A-Z]{3})\s*/\s*([A-Z]{3})", (f.get("label") or "").upper())
            if f["field"] == "fx_rate" and f["value"] and m and m.group(2) == BASE_CCY:
                fx[ik][m.group(1)] = (D(f["value"]), f["id"])
    missing_fx: dict[tuple[str, str], Decimal] = defaultdict(lambda: ZERO)
    used_fx: set[tuple[str, str]] = set()
    # SC-7.11: where no rate is printed, the ECB reference rate on the valuation date (looked up by the caller
    # with currency codes and dates only): {date: {ccy: {rate, rate_date, source, url}}}.
    reference_fx: dict[str, dict[str, dict]] = prospect.get("reference_fx") or {}
    used_ref: dict[tuple[str, str], dict] = {}
    val_dates = sorted(
        (d.get("profile") or {}).get("as_of") or ""
        for d in documents
        if d["doc_type"] == "portfolio_statement"
    )

    def valuation_date(ik: str) -> str | None:
        """The bank's statement date, else the latest statement date of the prospect."""
        own = [
            (d.get("profile") or {}).get("as_of")
            for d in documents
            if d["doc_type"] == "portfolio_statement"
            and inst_key((d.get("profile") or {}).get("institution")) == ik
        ]
        return max((x for x in own if x), default=None) or (
            val_dates[-1] if val_dates and val_dates[-1] else None
        )

    def to_base(amount: Decimal, ccy: str | None, ik: str) -> tuple[Decimal | None, str, tuple[str, ...]]:
        """Amount in CHF, the conversion note and the rate's fact id; None if no rate is known.

        A rate printed on the client's documents wins. Without one, the ECB reference rate on the valuation
        date (SC-7.11). Without either, the amount stays unconverted and is never counted as zero.
        """
        if not ccy or ccy == BASE_CCY:
            return amount, "", ()
        hit = fx.get(ik, {}).get(ccy)
        if hit is not None:
            rate, fid = hit
            used_fx.add((ik, ccy))
            return money(amount * rate), f"{ccy} {amount:,.2f} × {rate} {ccy}/{BASE_CCY}", (str(fid),)
        day = valuation_date(ik)
        ref = reference_fx.get(day or "", {}).get(ccy)
        if ref is None:
            missing_fx[(ik, ccy)] += amount
            return None, "", ()
        used_ref[(ik, ccy)] = ref
        rate = D(ref["rate"])
        note = f"{ccy} {amount:,.2f} × {rate} {ccy}/{BASE_CCY} ({ref['source']}, {ref['rate_date']})"
        return money(amount * rate), note, ()

    # ------------------------------------------------------------ institutions & positions
    holdings: list[dict] = []
    institutions: dict[str, dict] = {}
    statements_seen: dict[tuple, dict] = {}
    for d in documents:
        if d["doc_type"] != "portfolio_statement":
            continue
        prof = d.get("profile") or {}
        ik = inst_key(prof.get("institution"))
        # A re-downloaded or re-exported statement has other bytes, so the upload's sha256 check misses it.
        # Same bank, same date and the same positions is the same statement: count it once.
        sig = _statement_signature(ik, prof.get("as_of"), by_doc[d["id"]])
        if sig and sig in statements_seen:
            first = statements_seen[sig]
            checks.append(
                Check(
                    f"duplicate:statement:{d['id']}",
                    f"{d['filename']} repeats {first['filename']}",
                    "warn",
                    f"Same institution, valuation date and positions as {first['filename']}. "
                    "Counted once; this copy is ignored.",
                )
            )
            continue
        if sig:
            statements_seen[sig] = d
        inst = institutions.setdefault(
            ik,
            {
                "name": ik,
                "legal_name": prof.get("institution"),
                "jurisdiction": prof.get("jurisdiction"),
                "as_of": prof.get("as_of"),
                "documents": [],
                "assets": ZERO,
                "valued": False,
            },
        )
        inst["documents"].append(d["id"])
        pos_sum, total_fact, larger_total = ZERO, None, None
        for f in by_doc[d["id"]]:
            if f["key"] == "meta:second_person":
                checks.append(
                    Check(
                        f"second_person:{d['id']}",
                        f"{ik}: the file holds statements of more than one person",
                        "fail",
                        f"{f['label']}. Their holdings are added together here. Upload only the prospect's"
                        " pages, or split the file.",
                        [f["id"]],
                    )
                )
            elif f["kind"] == "doc_total" and f["key"] == "total:largest_printed":
                larger_total = f
            elif f["kind"] == "doc_total":
                total_fact = f
            if f["kind"] != "position" or f["value"] is None:
                continue
            orig = D(f["value"])
            pos_sum += orig  # reconciled in the statement's own currency
            if orig == 0:
                continue  # a printed 0 is not a CHF market value; showing it as CHF 0 pretends it was valued
            val, fx_note, _ = to_base(orig, f.get("currency"), ik)
            ex = f.get("extra") or {}
            ac, inferred = infer_asset_class(
                f["label"], ex.get("asset_class"), authoritative=bool(ex.get("asset_class_source"))
            )
            # No printed rate: keep the position so the pipeline can show it, but do not invent CHF.
            holdings.append(
                {
                    "fact_id": f["id"],
                    "document_id": d["id"],
                    "institution": ik,
                    "isin": f.get("isin"),
                    "name": f["label"],
                    "asset_class": ac,
                    "asset_class_inferred": inferred,
                    "value": val,
                    "currency": f.get("currency") or BASE_CCY,
                    "value_ccy": orig,
                    "fx_note": fx_note,
                    "status": f.get("status") or "extracted",
                    "synthetic_isin": bool(f.get("isin") and is_synthetic(f["isin"])),
                }
            )
            if val is not None:
                inst["assets"] += val
                inst["valued"] = True
        if total_fact:
            tot = D(total_fact["value"])
            ok = abs(tot - pos_sum) <= Decimal("1.00")
            checks.append(
                Check(
                    f"reconcile:{d['id']}",
                    f"{ik}: positions add up to the statement total",
                    "pass" if ok else "fail",
                    f"Sum of positions {pos_sum:,.2f} vs printed total {tot:,.2f}"
                    + (f" {total_fact.get('currency')}" if total_fact.get("currency") else "")
                    + (
                        ""
                        if ok
                        else f" (difference {tot - pos_sum:,.2f}). Check for missing rows or accrued interest"
                    ),
                    [total_fact["id"]],
                )
            )
        if larger_total:
            checks.append(
                Check(
                    f"printed_total:{d['id']}",
                    f"{ik}: the statement prints a larger total than the holdings read",
                    "fail",
                    f"Printed total {D(larger_total['value']):,.2f} vs holdings read {pos_sum:,.2f}. Look for"
                    " cash, policies or accounts that were not read, or a second client in the same file.",
                    [larger_total["id"]],
                )
            )
        if not total_fact:
            checks.append(
                Check(
                    f"reconcile:{d['id']}",
                    f"{ik}: statement total",
                    "warn",
                    "No printed total found; completeness of the position list cannot be confirmed.",
                )
            )
    as_ofs = {i["as_of"] for i in institutions.values() if i["as_of"]}
    if len(as_ofs) > 1:
        checks.append(
            Check(
                "valuation_dates",
                "Valuation dates are aligned",
                "warn",
                f"Statements have different valuation dates: {', '.join(sorted(as_ofs))}.",
            )
        )
    elif as_ofs:
        checks.append(
            Check(
                "valuation_dates",
                "Valuation dates are aligned",
                "pass",
                f"All holdings valued at {next(iter(as_ofs))}.",
            )
        )
    isin_seen: dict[str, list[str]] = defaultdict(list)
    for h in holdings:
        if h["isin"]:
            isin_seen[h["isin"]].append(h["institution"])
    for isin, insts in isin_seen.items():
        if len(insts) > 1:
            checks.append(
                Check(
                    f"dup:{isin}",
                    f"{isin} appears {len(insts)} times",
                    "warn",
                    "Same instrument in several statements: confirm these are separate holdings, "
                    "not a consolidated report repeating another bank's positions.",
                )
            )
    total_aum = sum((h["value"] for h in holdings if h["value"] is not None), ZERO)
    cash = sum(
        (h["value"] for h in holdings if h["asset_class"] == "CASH" and h["value"] is not None),
        ZERO,
    )
    chf_valued = any(h["value"] is not None for h in holdings)
    if not holdings:
        requests.append(
            MissingRequest(
                "holdings",
                1,
                None,
                "Statement of assets for every bank",
                "Statement of assets / portfolio valuation at the same date for each account",
                "Without holdings no cost can be put in proportion to assets.",
                ["all outputs"],
                ZERO,
                "portfolio_statement",
            )
        )

    # ------------------------------------------------------------ bank service costs
    atoms: list[FeeAtom] = []
    # Latest report first (SC-7.16): with two reports from one bank only the latest 12 months count, and a
    # second copy of the same period corroborates the first instead of adding to it.
    counted_period: dict[str, tuple[str | None, str | None]] = {}
    latest_first = sorted(
        documents, key=lambda d: (d.get("profile") or {}).get("period_end") or "", reverse=True
    )
    for d in latest_first:
        prof = d.get("profile") or {}
        ik = inst_key(prof.get("institution"))
        if d["doc_type"] == "cost_report" or any(f["kind"] == "fee_observed" for f in by_doc[d["id"]]):
            inst = institutions.setdefault(
                ik,
                {
                    "name": ik,
                    "legal_name": prof.get("institution"),
                    "jurisdiction": prof.get("jurisdiction"),
                    "as_of": None,
                    "documents": [],
                    "assets": ZERO,
                    "valued": False,
                },
            )
            if d["id"] not in inst["documents"]:
                inst["documents"].append(d["id"])
            ps, pe = prof.get("period_start"), prof.get("period_end")
            days, period_kind = _report_period(ps, pe)
            annualise = period_kind == "partial"
            if period_kind == "reversed":
                checks.append(
                    Check(
                        f"period:{d['id']}",
                        f"{ik}: cost report period is impossible",
                        "fail",
                        f"The report ends ({pe}) before it starts ({ps}). Amounts are counted as printed, "
                        "not annualised. Correct the dates.",
                    )
                )
            elif period_kind == "short":
                checks.append(
                    Check(
                        f"period:{d['id']}",
                        f"{ik}: cost report covers 12 months",
                        "warn",
                        f"Report covers only {days} days, too few to annualise. Amounts are counted as "
                        "printed: a lower bound, not the annual cost.",
                    )
                )
            elif annualise:
                checks.append(
                    Check(
                        f"period:{d['id']}",
                        f"{ik}: cost report covers 12 months",
                        "warn",
                        f"Report covers {days} days; amounts are annualised (× 365/{days}).",
                    )
                )
            # Lines of one report with the same code are separate charges (custody fee and custody
            # surcharge): summed into one atom (SC-7.16). A line in a currency with no printed rate cannot
            # be summed, but the cost exists: it becomes an unknown, never a silent zero (SC-7.21).
            lines: dict[str, list[tuple[dict, Decimal, str, tuple[str, ...]]]] = defaultdict(list)
            unconverted: dict[str, list[dict]] = defaultdict(list)
            for f in by_doc[d["id"]]:
                if f["kind"] != "fee_observed" or f["value"] is None:
                    continue
                amt, fx_note, fx_ids = to_base(D(f["value"]), f.get("currency"), ik)
                if amt is None:
                    unconverted[f["fee_code"]].append(f)
                else:
                    lines[f["fee_code"]].append((f, amt, fx_note, fx_ids))
            for code in dict.fromkeys([*lines, *unconverted]):
                items = lines.get(code, [])
                facts_of_code = [f for f, _a, _n, _i in items] + unconverted.get(code, [])
                label = facts_of_code[0]["label"]
                target = f"cur:{ik}:{code}"
                if target in counted_period and counted_period[target] != (ps, pe):
                    seen_ps, seen_pe = counted_period[target]
                    checks.append(
                        Check(
                            f"older_report:{d['id']}:{code}",
                            f"{ik}: older {label} not counted",
                            "info",
                            f"This report covers {ps} – {pe}; the one for {seen_ps} – {seen_pe} is newer. "
                            "Only the latest 12 months count.",
                            [f["id"] for f in facts_of_code],
                        )
                    )
                    continue
                # Same period again (a second copy of the report): its unknowns are already listed, and its
                # amount corroborates the counted atom instead of adding to it.
                seen = target in counted_period
                duplicate = seen and any(a.atom_id == target for a in atoms)
                counted_period.setdefault(target, (ps, pe))
                if unconverted.get(code) and not seen:
                    ccys = ", ".join(sorted({f.get("currency") or "?" for f in unconverted[code]}))
                    atoms.append(
                        FeeAtom(
                            f"{target}:unconverted",
                            code,
                            LAYER_BY_CODE.get(code, Layer.OTHER),
                            f"{ik} · {label} ({ccys})",
                            ik,
                            None,
                            Measurement.UNKNOWN,
                            Incidence.TAX if code in TAX_CODES else Incidence.BILLED,
                            evidence_ids=tuple(str(f["id"]) for f in unconverted[code]),
                            note=f"Charged in {ccys} with no {ccys}/{BASE_CCY} rate on the documents: not "
                            "converted and not counted as zero.",
                        )
                    )
                if not items:
                    continue
                amt = sum((a for _f, a, _n, _i in items), ZERO)
                ids = tuple(x for f, _a, _n, fx_ids in items for x in (str(f["id"]), *fx_ids))
                if amt < 0:
                    # A refund, a reversal or a misread minus. A negative annual fee is never a cost, and
                    # counting it would lower the total (SC-7.21).
                    checks.append(
                        Check(
                            f"negative_fee:{d['id']}:{code}",
                            f"{ik}: {label} adds up to a negative amount",
                            "fail",
                            f"The {label} lines sum to {amt:,.2f}. A refund or a misread sign? Not counted; "
                            "confirm the amount on the page.",
                            [f["id"] for f, _a, _n, _i in items],
                        )
                    )
                    if not seen:
                        atoms.append(
                            FeeAtom(
                                f"{target}:negative",
                                code,
                                LAYER_BY_CODE.get(code, Layer.OTHER),
                                f"{ik} · {label}",
                                ik,
                                None,
                                Measurement.UNKNOWN,
                                Incidence.TAX if code in TAX_CODES else Incidence.BILLED,
                                evidence_ids=ids,
                                note=f"Printed lines sum to {amt:,.2f}: under review, not counted.",
                            )
                        )
                    continue
                fx_notes = "; ".join(n for _f, _a, n, _i in items if n)
                formula = f"reported for {ps} – {pe}"
                if len(items) > 1:
                    formula += f", {len(items)} lines: " + " + ".join(f"{a:,.2f}" for _f, a, _n, _i in items)
                formula += f"; {fx_notes}" if fx_notes else ""
                if annualise:
                    assert days is not None
                    # rounded to the cent here, as debits are, so the rows shown add up to the total
                    amt = (amt * Decimal(365) / Decimal(days)).quantize(Decimal("0.01"))
                    formula += f", annualised × 365/{days}"
                elif period_kind == "short":
                    formula += f", {days} days only: not annualised, a lower bound"
                atoms.append(
                    FeeAtom(
                        f"rep:{d['id']}:{code}" if duplicate else target,
                        code,
                        LAYER_BY_CODE.get(code, Layer.OTHER),
                        f"{ik} · " + " + ".join(dict.fromkeys(f["label"] for f, _a, _n, _i in items)),
                        ik,
                        amt,
                        Measurement.OBSERVED,
                        Incidence.TAX if code in TAX_CODES else Incidence.BILLED,
                        corroborates=target if duplicate else None,
                        evidence_ids=ids,
                        formula=formula,
                    )
                )
    # cash debits corroborate (or, absent a report, establish) the annual figure. Debits of one fee at one
    # bank are pooled across its statements (SC-7.20) and summed (SC-7.7), then annualised: by the stated
    # frequency, else by the days the statements cover, else kept as a flagged lower bound. A statement
    # repeating a period already pooled counts once.
    pools: dict[tuple[str, str], dict] = {}
    for d in documents:
        if d["doc_type"] != "cash_statement":
            continue
        prof = d.get("profile") or {}
        ik = inst_key(prof.get("institution"))
        period = (prof.get("period_start"), prof.get("period_end"))
        groups: dict[str, list[tuple[dict, Decimal]]] = defaultdict(list)
        for f in by_doc[d["id"]]:
            if f["kind"] != "cash_debit" or f["value"] is None:
                continue
            debit, _note, _ids = to_base(D(f["value"]), f.get("currency"), ik)
            if debit is None:
                # no printed rate: the debit exists but has no CHF amount; never dropped as zero (SC-7.21)
                pools.setdefault((ik, f["fee_code"]), {"doc": d["id"], "periods": [], "items": []})
                pools[(ik, f["fee_code"])].setdefault("unconverted", []).append(f)
            else:
                groups[f["fee_code"]].append((f, debit))
        for code, items in groups.items():
            pool = pools.setdefault((ik, code), {"doc": d["id"], "periods": [], "items": []})
            if all(period) and period in pool["periods"]:
                checks.append(
                    Check(
                        f"debit_repeat:{d['id']}:{code}",
                        f"{ik}: {items[0][0]['label']} debits for {period[0]} – {period[1]} counted once",
                        "info",
                        "Another statement already covers this period, so its debits are not added again.",
                        [f["id"] for f, _v in items],
                    )
                )
                continue
            pool["periods"].append(period)
            pool["items"] += items
    for (ik, code), pool in pools.items():
        items, doc_id = pool["items"], pool["doc"]
        periods = pool["periods"]
        target = f"cur:{ik}:{code}"
        reported = any(a.atom_id == target for a in atoms)
        if pool.get("unconverted") and not reported:
            ccys = ", ".join(sorted({f.get("currency") or "?" for f in pool["unconverted"]}))
            atoms.append(
                FeeAtom(
                    f"{target}:unconverted",
                    code,
                    LAYER_BY_CODE.get(code, Layer.OTHER),
                    f"{ik} · {pool['unconverted'][0]['label']} ({ccys})",
                    ik,
                    None,
                    Measurement.UNKNOWN,
                    Incidence.BILLED,
                    evidence_ids=tuple(str(f["id"]) for f in pool["unconverted"]),
                    note=f"Debited in {ccys} with no {ccys}/{BASE_CCY} rate on the documents: not converted "
                    "and not counted as zero.",
                )
            )
        if not items:
            continue
        if sum((v for _f, v in items), ZERO) < 0:
            checks.append(
                Check(
                    f"negative_fee:{doc_id}:{code}",
                    f"{ik}: {items[0][0]['label']} debits add up to a negative amount",
                    "fail",
                    "More was credited back than debited. A refund or a misread sign? Not counted; confirm "
                    "the amounts on the statements.",
                    [f["id"] for f, _v in items],
                )
            )
            if not reported:
                atoms.append(
                    FeeAtom(
                        f"{target}:negative",
                        code,
                        LAYER_BY_CODE.get(code, Layer.OTHER),
                        f"{ik} · {items[0][0]['label']}",
                        ik,
                        None,
                        Measurement.UNKNOWN,
                        Incidence.BILLED,
                        evidence_ids=tuple(str(f["id"]) for f, _v in items),
                        note="Debits net to a negative amount: under review, not counted.",
                    )
                )
            continue
        days = None
        if all(a and b for a, b in periods):
            covered: set[date] = set()  # union of the periods, so overlapping statements are not double-timed
            for a, b in periods:
                first, last = date.fromisoformat(a), date.fromisoformat(b)
                covered |= {first + timedelta(i) for i in range((last - first).days + 1)}
            days = len(covered)
        total = sum((v for _f, v in items), ZERO)
        k = len(items)
        n = next((f["extra"]["periods_per_year"] for f, _v in items
                  if (f.get("extra") or {}).get("periods_per_year")), None)  # fmt: skip
        note = None
        what = f"{total:,.2f} debited" + (f" in {k} debits" if k > 1 else "")
        what += f" on {len(periods)} statements" if len(periods) > 1 else ""
        if n:
            annual = total / k * n
            measurement = Measurement.ESTIMATED
            formula = what + (f" ÷ {k}" if k > 1 else "") + f" × {n} periods per year"
        elif days and 360 <= days <= 366:
            annual, measurement, formula = total, Measurement.OBSERVED, what + f" over {days} days"
        elif days and days >= MIN_ANNUALISE_DAYS:
            annual = total * Decimal(365) / Decimal(days)
            measurement = Measurement.ESTIMATED
            formula = what + f" over {days} days, annualised × 365/{days}"
        elif days:
            annual, measurement = total, Measurement.ESTIMATED
            formula = what + f" over {days} days only: not annualised"
            note = f"Statements cover {days} days, too few to annualise: a lower bound, not the annual fee."
            checks.append(
                Check(
                    f"debit_period:{doc_id}:{code}",
                    f"{ik}: period of {items[0][0]['label']} debits",
                    "warn",
                    f"The statements cover only {days} days, so these debits are counted as a lower bound.",
                    [f["id"] for f, _v in items],
                )
            )
        else:
            annual, measurement = total, Measurement.ESTIMATED
            formula = what + " (period unknown, not annualised)"
            note = "Statement period unknown: a lower bound, not the annual fee."
            checks.append(
                Check(
                    f"debit_period:{doc_id}:{code}",
                    f"{ik}: period of {items[0][0]['label']} debits",
                    "warn",
                    "The statement period is unknown, so these debits are counted as a lower bound.",
                    [f["id"] for f, _v in items],
                )
            )
        annual = annual.quantize(Decimal("0.01"))
        corroborates = reported
        atoms.append(
            FeeAtom(
                f"debit:{doc_id}:{code}" if corroborates else target,
                code,
                LAYER_BY_CODE.get(code, Layer.OTHER),
                f"{ik} · {items[0][0]['label']}",
                ik,
                annual,
                measurement,
                Incidence.BILLED,
                corroborates=target if corroborates else None,
                evidence_ids=tuple(str(f["id"]) for f, _v in items),
                formula=formula,
                note=""
                if corroborates
                else (note or "Annualised from cash debits; confirm with the annual cost report."),
            )
        )

    # tariffs: applicability + contract-vs-observed checks (or contractual atoms if nothing observed)
    for d in documents:
        if d["doc_type"] != "tariff":
            continue
        prof = d.get("profile") or {}
        fs = by_doc[d["id"]]
        meta = next((f for f in fs if f["field"] == "issuing_entity"), None)
        tj = ((meta or {}).get("extra") or {}).get("jurisdiction") or prof.get("jurisdiction")
        ik = inst_key((meta or {}).get("extra", {}).get("entity") or prof.get("institution"))
        target_inst = next((k for k in institutions if k.split(" (")[0] in ik or ik in k), ik)
        booking = institutions.get(target_inst, {}).get("jurisdiction")
        tariff = Tariff(
            f"doc{d['id']}",
            ik,
            tj or "??",
            date.fromisoformat(prof.get("as_of") or "1900-01-01"),
            None,
            "CHF",
        )
        val_date = date.fromisoformat(
            institutions.get(target_inst, {}).get("as_of") or prof.get("as_of") or "1900-01-01"
        )
        if not booking:
            checks.append(
                Check(
                    f"tariff:{d['id']}",
                    f"{d['filename']}: tariff applicability",
                    "warn",
                    "No holdings found for this institution, so the booking jurisdiction is unknown.",
                    [meta["id"]] if meta else [],
                )
            )
            continue
        ok, reason = tariff.applicability(booking, val_date)
        if not ok:
            checks.append(
                Check(
                    f"tariff:{d['id']}",
                    f"{target_inst}: price schedule rejected",
                    "fail",
                    f"{reason} The document was kept for reference but is not used in any calculation.",
                    [meta["id"]] if meta else [],
                )
            )
            requests.append(
                MissingRequest(
                    f"tariff:{target_inst}",
                    2,
                    target_inst,
                    f"{target_inst}: price schedule of the Swiss booking entity",
                    f"Individual fee agreement or current price schedule issued by the {booking} "
                    f"entity that books the account",
                    "The uploaded schedule belongs to another legal entity/jurisdiction.",
                    ["contractual cross-check"],
                    institutions[target_inst]["assets"],
                    "custody_tariff",
                )
            )
            continue
        checks.append(
            Check(
                f"tariff:{d['id']}",
                f"{target_inst}: price schedule applies",
                "pass",
                f"Issued by a {tj} entity, account booked in {booking}, in force on {val_date}.",
                [meta["id"]] if meta else [],
            )
        )
        inst_hold = [h for h in holdings if h["institution"] == target_inst]
        bases = {
            "aum": sum((h["value"] for h in inst_hold), ZERO),
            "custody_eligible": sum((h["value"] for h in inst_hold if h["asset_class"] != "CASH"), ZERO),
        }
        mins = {
            f["fee_code"]: D(f["value"])
            for f in fs
            if f["field"] == "minimum" and (f.get("extra") or {}).get("per") == "year"
        }
        for f in fs:
            if f["field"] != "rate_pct" or f["fee_code"] not in (
                "ADVISORY_FEE",
                "MGMT_DISCRETIONARY",
                "CUSTODY_FEE",
            ):
                continue
            base_key = "custody_eligible" if (f.get("extra") or {}).get("cash_excluded") else "aum"
            rule = FeeRule(
                f["fee_code"],
                f["label"],
                base_key,
                rate_bps=D(f["value"]) * 100,
                minimum=mins.get(f["fee_code"], 0),
            )
            expected = rule.annual_amount(bases[base_key])
            observed = next((a for a in atoms if a.atom_id == f"cur:{target_inst}:{f['fee_code']}"), None)
            if observed:
                diff = observed.amount - expected
                st = "pass" if abs(diff) <= max(Decimal("1"), expected * Decimal("0.02")) else "warn"
                checks.append(
                    Check(
                        f"contract:{target_inst}:{f['fee_code']}",
                        f"{target_inst}: {FEE_LABEL_NAMES.get(f['fee_code'], f['fee_code'])} "
                        "matches the price schedule",
                        st,
                        f"Schedule implies {expected:,.2f} ({rule.formula(bases[base_key])}); "
                        f"observed {observed.amount:,.2f}"
                        + (
                            ""
                            if st == "pass"
                            else f"; difference {diff:,.2f} — individual conditions or a different fee base?"
                        ),
                        [f["id"]] + [int(x) for x in observed.evidence_ids],
                    )
                )
            else:
                atoms.append(
                    FeeAtom(
                        f"cur:{target_inst}:{f['fee_code']}",
                        f["fee_code"],
                        LAYER_BY_CODE.get(f["fee_code"], Layer.OTHER),
                        f"{target_inst} · {f['label']}",
                        target_inst,
                        expected,
                        Measurement.CONTRACTUAL,
                        Incidence.BILLED,
                        evidence_ids=(str(f["id"]),),
                        formula=rule.formula(bases[base_key]),
                        basis_amount=bases[base_key],
                        rate_bps=rule.rate_bps,
                    )
                )

    # unknown core service costs for every institution without evidence
    for ik, inst in institutions.items():
        have = {a.fee_code for a in atoms if a.institution == ik}
        for code, label, layer in SERVICE_CORE:
            present = bool(have & SERVICE_CODES) if code == "SERVICE" else code in have
            if not present:
                atoms.append(
                    FeeAtom(
                        f"cur:{ik}:{code}:unknown",
                        "ADVISORY_FEE" if code == "SERVICE" else code,
                        layer,
                        f"{ik} · {label}",
                        ik,
                        None,
                        Measurement.UNKNOWN,
                        Incidence.BILLED,
                        note="No fee report, debit or applicable contract found.",
                    )
                )
        if not any(a.institution == ik and a.measurement == Measurement.OBSERVED for a in atoms):
            if inst.get("valued") and total_aum:
                share = (inst["assets"] / total_aum * 100).quantize(Decimal("0.1"))
                reason = (
                    f"No charged fee is documented for {ik} ({share}% of assets). "
                    "Service, custody and trading costs are shown as UNKNOWN, not zero."
                )
                affected: Decimal | None = inst["assets"]
            else:
                # Unvalued assets are not 0% and not CHF 0 affected.
                reason = (
                    f"No charged fee is documented for {ik}. Its assets are not valued in CHF, "
                    "so no share is calculated. Service, custody and trading costs are shown as "
                    "UNKNOWN, not zero."
                )
                affected = None
            requests.append(
                MissingRequest(
                    f"cost_report:{ik}",
                    1,
                    ik,
                    f"{ik}: annual cost and charges report",
                    "Annual report on costs and charges (ex-post) for the last 12 months, "
                    "or all fee debit advices "
                    "for the same period, plus the mandate/advisory agreement",
                    reason,
                    ["verified current total", "point estimate of the saving", "acquisition decision"],
                    affected,
                    "annual_cost_report",
                )
            )

    # ------------------------------------------------------------ product costs
    product_docs, product_doc_meta = _pick_product_docs(documents, by_doc, checks)
    rates: list[ProductRate] = []
    extra_product_atoms: list[FeeAtom] = []
    merged_holdings = _merge_lots(holdings)
    for h in merged_holdings:
        if h["asset_class"] != "CASH" and product_docs.get(h["isin"] or ""):
            # A KID for this exact ISIN proves a packaged product, even when its name reads like a share
            # ("Comgest Monde C"); ignoring it would report the cost complete without the fund's charges.
            if h["asset_class"] in ("EQUITY", "BOND"):
                is_sp = product_doc_meta[h["isin"]]["doc_type"] == "termsheet"
                h["asset_class"] = "STRUCTURED" if is_sp else "FUND"
                for lot in h["lots"]:
                    lot["asset_class"] = h["asset_class"]
        elif not _product_gap(h):
            continue  # equity and cash: no invented TER
        isin = h["isin"]
        fs = product_docs.get(isin or "", [])
        code, layer, gap_note = _gap_fee(h)
        if h["value"] is None or not fs:
            # No CHF basis, or no KID for this ISIN: an explicit unknown. Never amount 0.
            ccy = h["currency"]
            if h["value"] is None and fs:
                note = (
                    "A KID matches this ISIN, but the position is not valued in CHF, so the "
                    "ongoing charge is not calculated and is not zero."
                )
            elif h["value"] is None:
                note = (
                    f"{gap_note} The position is in {ccy} and no {ccy}/{BASE_CCY} rate is printed, "
                    "so no CHF amount is calculated."
                )
            else:
                note = gap_note
            extra_product_atoms.append(
                FeeAtom(
                    f"cur:{h['institution']}:{isin or h['name']}:PRODUCT_UNKNOWN",
                    code,
                    layer,
                    f"{h['name']} · product costs",
                    h["institution"],
                    None,
                    Measurement.UNKNOWN,
                    Incidence.EMBEDDED,
                    instrument_id=isin,
                    note=note,
                )
            )
            if not fs:
                if h["value"] is None:
                    reason = (
                        f"Embedded costs are unknown. The position is denominated in {ccy} and no "
                        f"{ccy}/{BASE_CCY} rate is printed, so it is not converted and not counted as zero."
                    )
                    affected = None
                else:
                    reason = f"Embedded costs of a CHF {h['value']:,.0f} position are unknown."
                    affected = h["value"]
                requests.append(
                    MissingRequest(
                        f"kid:{isin or h['name']}",
                        2,
                        h["institution"],
                        f"KID for {h['name']}",
                        f"Key Information Document (PRIIPs KID or FinSA BIB) for ISIN {isin}, "
                        "exact share class, current version"
                        if isin
                        else f"Product documentation for {h['name']}",
                        reason,
                        ["product cost of this position"],
                        affected,
                        "kid_priips",
                    )
                )
            continue
        doc = product_doc_meta[isin]
        ddate = (doc.get("profile") or {}).get("as_of")
        if (
            ddate
            and (
                date.fromisoformat(institutions[h["institution"]]["as_of"] or ddate)
                - date.fromisoformat(ddate)
            ).days
            > 548
        ):
            checks.append(
                Check(
                    f"stale:{isin}",
                    f"{isin}: product document is older than 18 months",
                    "warn",
                    f"Document dated {ddate}; costs may have changed. Request the current version.",
                )
            )
        for f in fs:
            code, meas = f["fee_code"], f.get("measurement")
            if code in (
                "FUND_ONGOING",
                "FUND_TRANSACTION",
                "FUND_PERFORMANCE",
                "FUND_MGMT_FEE",
                "SP_ONGOING",
                "SP_ENTRY_COST",
            ) and meas in ("estimated", "unknown"):
                if code == "FUND_PERFORMANCE" and f["value"] is not None and D(f["value"]) == 0:
                    continue
                rates.append(
                    ProductRate(
                        isin,
                        code,
                        _d(f["value"]),
                        included_in_code=(f.get("extra") or {}).get("included_in"),
                        evidence_ids=(str(f["id"]),),
                        source_label=f"{doc['filename']}, dated {ddate or 'n/a'}",
                    )
                )
            elif meas == "maximum" and f["value"] is not None and D(f["value"]) > 0:
                amt = h["value"] * D(f["value"]) / 100
                extra_product_atoms.append(
                    FeeAtom(
                        f"cur:{h['institution']}:{isin}:{code}:max",
                        code,
                        LAYER_BY_CODE.get(code, Layer.PRODUCT),
                        f"{h['name']} · {f['label']} (maximum)",
                        h["institution"],
                        amt,
                        Measurement.MAXIMUM,
                        Incidence.EMBEDDED,
                        instrument_id=isin,
                        recurring=code.endswith("ONGOING"),
                        evidence_ids=(str(f["id"]),),
                        formula=f"{h['value']:,.2f} × up to {f['value']}%",
                        note="Disclosed maximum, not the amount actually charged; not counted.",
                    )
                )
            elif meas == "illustrative" and f["value"] is not None:
                extra_product_atoms.append(
                    FeeAtom(
                        f"cur:{h['institution']}:{isin}:KID_ILLUSTRATION",
                        "KID_ILLUSTRATION",
                        Layer.PRODUCT,
                        f"{h['name']} · KID cost illustration",
                        h["institution"],
                        D(f["value"]),
                        Measurement.ILLUSTRATIVE,
                        Incidence.EMBEDDED,
                        instrument_id=isin,
                        evidence_ids=(str(f["id"]),),
                        # the KID's own currency, not CHF: "USD 7 on USD 10'000" (SC-5.19)
                        formula=f"manufacturer example: {f.get('currency') or ''} {f['value']} on a "
                        f"{f.get('currency') or ''} 10'000 investment".replace("  ", " "),
                        note="Hypothetical example from the KID; never a cost actually paid.",
                    )
                )
        if h["asset_class"] in ("FUND", "ETF") and not any(f["fee_code"] == "FUND_TRANSACTION" for f in fs):
            # A UCITS KIID or FinSA BIB states ongoing charges without portfolio transaction costs; those
            # are real and outside the OCF, so the gap is an unknown, never a silent zero (SC-7.8).
            rates.append(
                ProductRate(
                    isin,
                    "FUND_TRANSACTION",
                    None,
                    source_label=f"{doc['filename']} does not state portfolio transaction costs.",
                )
            )
    # Only CHF-valued positions enter the rate × value product. An unvalued line stays an unknown atom.
    hold_inputs = [
        HoldingInput(
            h["isin"] or h["name"],
            h["name"],
            h["asset_class"],
            h["value"],
            h["institution"],
            h["institution"],
        )
        for h in holdings
        if h["value"] is not None
    ]
    cur_product = product_atoms(hold_inputs, rates, "cur")
    for a in cur_product:
        if a.fee_code == "SP_ENTRY_COST" and a.measurement == Measurement.UNKNOWN:
            a.note = "Issuer margin not disclosed in the termsheet."
            h = next(x for x in merged_holdings if x["isin"] == a.instrument_id)
            requests.append(
                MissingRequest(
                    f"sp:{a.instrument_id}",
                    3,
                    a.institution,
                    f"Issuer cost data for {h['name']}",
                    f"Issuer KID or SSPA cost data showing the issue price vs fair value "
                    f"for ISIN {a.instrument_id}",
                    "The termsheet does not disclose the issuer margin; this embedded cost stays UNKNOWN.",
                    ["structured product cost"],
                    h["value"],
                    "sp_termsheet",
                )
            )
    current_atoms = atoms + cur_product + extra_product_atoms
    # SC-7.9: where funds at a bank have no KID, the bank's own ex-post product-cost figure (tier T4) covers
    # the gap. KID figures (tier T3) stay counted; only the part of the bank figure they do not explain is
    # added, as one residual atom, so nothing is counted twice. If the KIDs already explain the whole bank
    # figure, nothing is added and the gaps stay unknown. The comparison keeps per-holding product costs.
    view_atoms = list(current_atoms)
    for d in documents:
        if d["doc_type"] != "cost_report":
            continue
        prof = d.get("profile") or {}
        ik = inst_key(prof.get("institution"))
        rep = next((f for f in by_doc[d["id"]] if f["field"] == "reported_product_costs"), None)
        mine = [a for a in view_atoms if a.institution == ik and a.incidence == Incidence.EMBEDDED]
        if not rep or not any(a.measurement == Measurement.UNKNOWN for a in mine):
            continue
        amt, fx_note, fx_ids = to_base(D(rep["value"]), rep.get("currency"), ik)
        if amt is None:
            continue
        ps, pe = prof.get("period_start"), prof.get("period_end")
        days, period_kind = _report_period(ps, pe)
        basis = f"bank figure {amt:,.2f}" + (f" for {ps} – {pe}" if days else "")
        if period_kind == "partial":
            assert days is not None
            amt = (amt * Decimal(365) / Decimal(days)).quantize(Decimal("0.01"))
            basis += f", annualised × 365/{days}"
        explained = sum(
            (
                a.amount
                for a in mine
                if a.amount is not None
                and not a.included_in
                and not a.corroborates
                and a.measurement in (Measurement.ESTIMATED, Measurement.OBSERVED, Measurement.CONTRACTUAL)
            ),
            ZERO,
        )
        if amt <= explained:
            continue
        gaps = {a.atom_id for a in mine if a.measurement == Measurement.UNKNOWN}
        view_atoms = [
            replace(
                a, materiality="minor", note=f"{a.note} Covered by the bank's reported product costs.".strip()
            )
            if a.atom_id in gaps
            else a
            for a in view_atoms
        ]
        view_atoms.append(
            FeeAtom(
                f"cur:{ik}:PRODUCT_REPORTED",
                "FUND_ONGOING",
                Layer.PRODUCT,
                f"{ik} · product costs reported by the bank, not covered by a KID",
                ik,
                amt - explained,
                Measurement.ESTIMATED,
                Incidence.EMBEDDED,
                evidence_ids=(str(rep["id"]), *fx_ids),
                formula=f"{basis} − {explained:,.2f} from KIDs and termsheets"
                + (f"; {fx_note}" if fx_note else ""),
                note="The bank's own estimate in its cost report, for the products without a KID.",
            )
        )
    current = aggregate(view_atoms, scope_aum=total_aum or None)
    hidden = hidden_costs(
        holdings,
        BASE_CCY,
        {(a.institution or "", a.fee_code) for a in current_atoms if a.measurement != Measurement.UNKNOWN},
    )
    if hidden:
        checks.append(
            Check(
                "hidden_costs",
                "Hidden costs not yet estimated",
                "info",
                f"{len(hidden)} hidden cost(s) apply to these holdings but are not estimated: "
                + ", ".join(sorted({h.label for h in hidden}))
                + ". Shown apart, never in the total.",
            )
        )

    # bank's own reported product-cost estimate vs ours (reconciliation, never added)
    for d in documents:
        if d["doc_type"] != "cost_report":
            continue
        ik = inst_key((d.get("profile") or {}).get("institution"))
        rep = next((f for f in by_doc[d["id"]] if f["field"] == "reported_product_costs"), None)
        if rep:
            ours = sum(
                (
                    a.amount
                    for a in cur_product
                    if a.institution == ik and current.roles[a.atom_id] == AtomRole.COUNTED
                ),
                ZERO,
            )
            theirs, _note, _ids = to_base(D(rep["value"]), rep.get("currency"), ik)
            if theirs is None:
                continue
            diff = ours - theirs
            pct = (diff / theirs * 100).quantize(Decimal("0.1")) if theirs else None
            st = "pass" if pct is not None and abs(pct) <= 5 else "warn"
            checks.append(
                Check(
                    f"product_recon:{ik}",
                    f"{ik}: product costs vs the bank's own estimate",
                    st,
                    f"KID-based estimate {ours:,.2f} vs bank-reported {theirs:,.2f} ({pct:+}%). "
                    "The bank figure is used as a cross-check only, never added.",
                    [rep["id"]],
                )
            )
        retro = next((f for f in by_doc[d["id"]] if f["field"] == "retrocessions_received"), None)
        retro_chf = to_base(D(retro["value"]), retro.get("currency"), ik)[0] if retro else None
        if retro and retro_chf is not None:
            checks.append(
                Check(
                    f"retro:{ik}",
                    f"{ik}: retrocessions received",
                    "info",
                    f"{ik} reports CHF {retro_chf:,.2f} of retrocessions paid out of product costs. "
                    "Not an extra client cost; under Swiss law they generally belong to the client unless "
                    "validly waived (to verify with counsel).",
                    [retro["id"]],
                )
            )
    for w in current.warnings:
        checks.append(Check(f"ledger:{len(checks)}", "Duplicate or inclusion check", "warn", w))
    if any(a.corroborates for a in current_atoms) and not current.warnings:
        checks.append(
            Check(
                "corroboration",
                "Cash debits match the annual cost report",
                "pass",
                "Quarterly debits × 4 equal the annual amounts; counted once.",
            )
        )

    # currency conversion: say which printed rate was used, and never convert with a guessed rate
    for ik, inst_rates in fx.items():
        for ccy, (rate, fid) in inst_rates.items():
            if (ik, ccy) not in used_fx:
                continue
            checks.append(
                Check(
                    f"fx:{ik}:{ccy}",
                    f"{ik}: {ccy} amounts converted at the printed rate",
                    "info",
                    f"{ccy}/{BASE_CCY} {rate} as printed on the document. Fees for the year are converted "
                    "at this valuation-date rate (an approximation for a whole period).",
                    [fid],
                )
            )
            ref = reference_fx.get(valuation_date(ik) or "", {}).get(ccy)
            if ref and abs(rate - D(ref["rate"])) > D(ref["rate"]) * FX_REVIEW_GAP:
                checks.append(
                    Check(
                        f"fx_gap:{ik}:{ccy}",
                        f"{ik}: printed {ccy}/{BASE_CCY} rate differs from the reference rate",
                        "warn",
                        f"Printed {rate} vs {ref['source']} {ref['rate']} on {ref['rate_date']}: more than "
                        f"{FX_REVIEW_GAP * 100}% apart. The printed rate is used; check it was read right.",
                        [fid],
                    )
                )
    for (ik, ccy), ref in sorted(used_ref.items()):
        checks.append(
            Check(
                f"fx_ref:{ik}:{ccy}",
                f"{ik}: {ccy} amounts converted at the reference rate",
                "info",
                f"No {ccy}/{BASE_CCY} rate is printed on the documents, so {ccy} amounts are converted at "
                f"{ref['rate']} ({ref['source']}, {ref['rate_date']}, {ref['url']}). Upload a page with the "
                "bank's own rate to replace it.",
            )
        )
    for (ik, ccy), amt in missing_fx.items():
        checks.append(
            Check(
                f"fx_missing:{ik}:{ccy}",
                f"{ik}: no {ccy}/{BASE_CCY} rate on the documents",
                "fail",
                f"{ccy} {amt:,.2f} could not be converted and is left out of every total. "
                "No rate is printed and no reference rate is available.",
            )
        )
        requests.append(
            MissingRequest(
                f"fx:{ik}:{ccy}",
                1,
                ik,
                f"{ik}: {ccy}/{BASE_CCY} exchange rate at the valuation date",
                f"Statement page showing the {ccy}/{BASE_CCY} rate used for the valuation",
                "Amounts in a foreign currency are not converted with a guessed rate.",
                ["assets", "costs"],
                None,
                "portfolio_statement",
            )
        )

    # coverage matrix: institution × layer
    coverage = []
    for ik, inst in institutions.items():
        row = {
            "institution": ik,
            "assets": str(inst["assets"]),
            "valued": bool(inst.get("valued")),
            "jurisdiction": inst["jurisdiction"],
            "cells": {},
        }
        for layer in (
            Layer.SERVICE,
            Layer.CUSTODY,
            Layer.TRADING,
            Layer.PRODUCT,
            Layer.STRUCTURED,
            Layer.TAX,
        ):
            rel = [
                a
                for a in view_atoms
                if a.institution == ik
                and a.layer == layer
                and current.roles[a.atom_id] in (AtomRole.COUNTED, AtomRole.UNKNOWN)
            ]
            if not rel:
                row["cells"][layer.value] = "not_applicable"
            elif any(current.roles[a.atom_id] == AtomRole.UNKNOWN for a in rel):
                row["cells"][layer.value] = (
                    "partial" if any(current.roles[a.atom_id] == AtomRole.COUNTED for a in rel) else "unknown"
                )
            else:
                order = ["observed", "contractual", "public_tariff", "estimated"]
                row["cells"][layer.value] = max((a.measurement.value for a in rel), key=order.index)
        coverage.append(row)

    # ------------------------------------------------------------ scenarios
    p = proposal
    vat = D(p.get("vat_pct", "0")) if prospect.get("domicile", "CH") == "CH" else ZERO
    custody_base = total_aum - cash
    bases = {
        "aum": total_aum,
        "custody_eligible": custody_base,
        "trade_notional": D(p.get("annual_turnover_chf", "0")),
        "fx_notional": D(p.get("fx_notional_chf", "0")),
    }
    tiers = [(None if u in (None, "") else D(u), D(r)) for u, r in p["eam_tiers"]]
    firm, custodian = p.get("firm_name", "Proposal"), p.get("custodian", "Proposed custodian")
    rules = [
        FeeRule(
            "EAM_FEE",
            f"{firm} · management fee (EAM)",
            "aum",
            tiers=tiers,
            tier_method=TierMethod(p.get("eam_tier_method", "marginal")),
        ),
        FeeRule(
            "CUSTODY_FEE",
            f"{custodian} · custody fee",
            "custody_eligible",
            rate_bps=D(p["custody_bps"]),
            minimum=D(p.get("custody_min", "0")),
        ),
        FeeRule(
            "BROKERAGE",
            f"{custodian} · brokerage (assumed turnover)",
            "trade_notional",
            rate_bps=D(p["brokerage_bps"]),
        ),
        FeeRule(
            "FX_COMMISSION",
            f"{custodian} · FX commission (assumed volume)",
            "fx_notional",
            rate_bps=D(p["fx_bps"]),
        ),
    ]
    svc: list[FeeAtom] = []
    for r in rules:
        amount = r.annual_amount(bases[r.base])
        inst_name = firm if r.fee_code == "EAM_FEE" else custodian
        svc.append(
            FeeAtom(
                f"prop:{r.fee_code}",
                r.fee_code,
                LAYER_BY_CODE.get(r.fee_code, Layer.OTHER),
                r.label,
                inst_name,
                amount,
                Measurement.CONTRACTUAL,
                Incidence.BILLED,
                formula=r.formula(bases[r.base]),
                basis_amount=bases[r.base],
                note="Proposal input (editable)",
            )
        )
    if vat:
        vat_base = sum((a.amount for a in svc if a.fee_code in ("EAM_FEE", "CUSTODY_FEE")), ZERO)
        svc.append(
            FeeAtom(
                "prop:VAT_ON_FEES",
                "VAT_ON_FEES",
                Layer.TAX,
                f"Swiss VAT {vat}% on management and custody fees",
                firm,
                vat_base * vat / 100,
                Measurement.CONTRACTUAL,
                Incidence.TAX,
                formula=f"{vat_base:,.2f} × {vat}% (client domiciled in CH)",
            )
        )

    def cmp_view(atoms_: list[FeeAtom]) -> list[FeeAtom]:
        return [a for a in atoms_ if a.fee_code not in EXCLUDED_FROM_COMPARISON]

    same_product = product_atoms(hold_inputs, rates, "cur")  # identical holdings -> identical product costs
    same_unknown_product = [a for a in extra_product_atoms if a.measurement == Measurement.UNKNOWN]
    same_atoms = svc + same_product + same_unknown_product
    cur_cmp = aggregate(cmp_view(current_atoms), scope_aum=total_aum or None)
    same_sum = aggregate(same_atoms, scope_aum=total_aum or None)
    shared = {(a.instrument_id, a.fee_code) for a in same_sum.unknown} & {
        (a.instrument_id, a.fee_code) for a in cur_cmp.unknown
    }
    cur_ok = not any(
        a.materiality == "material" and (a.instrument_id, a.fee_code) not in shared for a in cur_cmp.unknown
    )
    same_ok = not any(
        a.materiality == "material" and (a.instrument_id, a.fee_code) not in shared for a in same_sum.unknown
    )
    mig = p.get("migration", {})
    transfer_cost = sum((D(v) for v in mig.values()), ZERO)
    same_cmp = compare(cur_cmp, same_sum, transfer_cost, True, cur_ok, same_ok)
    _claim_saving(same_cmp, valued=chf_valued, known=cur_cmp.total_known)

    # optimised: explicit instrument swaps
    swaps = p.get("optimized_swaps", [])
    swap_from = {s["from"]: s for s in swaps}
    opt_holdings, opt_rates = [], [r for r in rates if r.instrument_id not in swap_from]
    swap_rows = []
    rebuild = ZERO
    for h in hold_inputs:
        s = swap_from.get(h.instrument_id)
        if s:
            opt_holdings.append(HoldingInput(s["to"], s["to_name"], "FUND", h.value, custodian, "proposal"))
            opt_rates.append(
                ProductRate(s["to"], "FUND_ONGOING", D(s["to_ongoing"]), source_label="proposal input")
            )
            opt_rates.append(
                ProductRate(
                    s["to"], "FUND_TRANSACTION", D(s["to_transaction"]), source_label="proposal input"
                )
            )
            old_rate = sum(
                (
                    r.rate_pct
                    for r in rates
                    if r.instrument_id == h.instrument_id
                    and r.rate_pct is not None
                    and r.fee_code in ("FUND_ONGOING", "FUND_TRANSACTION")
                ),
                ZERO,
            )
            known_old = any(r.instrument_id == h.instrument_id for r in rates)
            swap_rows.append(
                {
                    "from": h.instrument_id,
                    "from_name": h.name,
                    "to": s["to"],
                    "to_name": s["to_name"],
                    "value": str(h.value),
                    "from_rate_pct": str(old_rate) if known_old else None,
                    "to_rate_pct": str(D(s["to_ongoing"]) + D(s["to_transaction"])),
                }
            )
            rebuild += h.value * 2 * D(p["brokerage_bps"]) / Decimal(10000)
        else:
            opt_holdings.append(h)
    opt_product = product_atoms(opt_holdings, opt_rates, "cur")
    opt_unknown = [a for a in same_unknown_product if a.instrument_id not in swap_from]
    opt_sum = aggregate(svc + opt_product + opt_unknown, scope_aum=total_aum or None)
    opt_ok = not any(
        a.materiality == "material" and (a.instrument_id, a.fee_code) not in shared for a in opt_sum.unknown
    )
    cur_ok_opt = not any(
        a.materiality == "material"
        and ((a.instrument_id, a.fee_code) not in shared or a.instrument_id in swap_from)
        for a in cur_cmp.unknown
    )
    opt_cmp = compare(cur_cmp, opt_sum, transfer_cost + rebuild, False, cur_ok_opt, opt_ok)
    _claim_saving(opt_cmp, valued=chf_valued, known=cur_cmp.total_known)

    internal = internal_economics(
        [a for a in svc if a.fee_code == "EAM_FEE"],
        D(p["internal"]["servicing_cost"]),
        D(p["internal"]["onboarding_cost"]),
        same_cmp,
        evidence_complete=cur_ok,
        min_margin_pct=D(p["internal"]["min_margin_pct"]),
    )

    requests.sort(key=lambda r: (r.priority, -(r.assets_affected or ZERO)))
    excluded = [
        {
            "fee_code": a.fee_code,
            "label": a.label,
            "amount": str(a.amount),
            "reason": EXCLUDED_FROM_COMPARISON[a.fee_code],
        }
        for a in current_atoms
        if a.fee_code in EXCLUDED_FROM_COMPARISON and a.amount is not None
    ]
    return _ser(
        {
            "engine_version": ENGINE_VERSION,
            "synthetic": bool(holdings)
            and any(h["isin"] for h in holdings)
            and all(h["synthetic_isin"] for h in holdings if h["isin"]),
            "aum": {
                "total": total_aum,
                "valued": chf_valued,
                "cash": cash,
                "custody_eligible": custody_base,
                "by_institution": {k: v["assets"] for k, v in institutions.items()},
            },
            "institutions": [{**v, "assets": str(v["assets"])} for v in institutions.values()],
            "holdings": [
                {
                    **h,
                    "value": None if h["value"] is None else str(h["value"]),
                    "weight_pct": str((h["value"] / total_aum * 100).quantize(Decimal("0.1")))
                    if h["value"] is not None and total_aum
                    else None,
                }
                for h in holdings
            ],
            "current": summary_dict(current, view_atoms),
            "coverage": coverage,
            "hidden_costs": [asdict(h) for h in hidden],
            "checks": [asdict(c) for c in checks],
            "requests": [asdict(r) for r in requests],
            "comparison_exclusions": excluded,
            "scenarios": {
                "current_comparable": summary_dict(cur_cmp, cmp_view(current_atoms)),
                "same_holdings": {
                    "ledger": summary_dict(same_sum, same_atoms),
                    "comparison": asdict(same_cmp),
                    "migration_items": mig,
                },
                "optimized": {
                    "ledger": summary_dict(opt_sum, svc + opt_product + opt_unknown),
                    "comparison": asdict(opt_cmp),
                    "swaps": swap_rows,
                    "rebuild_trading_cost": rebuild,
                },
            },
            "internal": asdict(internal),
            "proposal_inputs": p,
            "client_domicile": prospect.get("domicile", "CH"),
        }
    )
