"""From reviewed facts to cost ledger, checks, missing-document requests and scenarios.

Pure function of its inputs (no DB, no network) so it is fully testable and reproducible.
Every atom cites the fact ids it came from; the UI resolves those to page + rectangle.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from .engine.isin import is_synthetic
from .engine.ledger import AtomRole, FeeAtom, Incidence, Layer, LedgerSummary, Measurement, aggregate
from .engine.money import ZERO, D, bps_of
from .engine.scenarios import (
    LAYER_BY_CODE,
    HoldingInput,
    ProductRate,
    compare,
    internal_economics,
    product_atoms,
)
from .engine.tariff import FeeRule, Tariff, TierMethod
from .extraction.vocab import FEE_LABEL_NAMES

ENGINE_VERSION = "pce-engine-0.1"
TAX_CODES = {"VAT_ON_FEES", "STAMP_DUTY_CH"}
EXCLUDED_FROM_COMPARISON = {"STAMP_DUTY_CH": "Swiss stamp duty is a tax that applies at any Swiss bank; "
                                             "excluded from the like-for-like comparison."}
SERVICE_CORE = [("SERVICE", "Management or advisory fee (if any)", Layer.SERVICE),
                ("CUSTODY_FEE", "Custody fee", Layer.CUSTODY),
                ("BROKERAGE", "Brokerage", Layer.TRADING)]
SERVICE_CODES = {"ADVISORY_FEE", "MGMT_DISCRETIONARY", "ALL_IN_FEE", "EAM_FEE", "PLATFORM_FIXED"}
LEGAL_SUFFIX = re.compile(r"\b(SA|AG|S\.A\.|Ltd|plc|LLC|Europe|GmbH|S\.p\.A\.)\b\.?", re.I)


def inst_key(name: str | None) -> str:
    if not name:
        return "Unknown institution"
    return re.sub(r"\s+", " ", LEGAL_SUFFIX.sub("", name)).strip(" ,")


def infer_asset_class(name: str, given: str | None) -> tuple[str, bool]:
    if given:
        g = given.upper()
        return ("STRUCTURED" if g.startswith("STRUCT") else g), False
    n = name.lower()
    if re.search(r"\betf\b", n):
        return "ETF", True
    if re.search(r"convertible|certificate|note|tracker|barrier|zertifikat|certificato", n):
        return "STRUCTURED", True
    if re.search(r"fund|fonds|fondo|sicav", n):
        return "FUND", True
    if re.search(r"account|cash|liquid|conto|konto|compte", n):
        return "CASH", True
    return "EQUITY", True


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
    assets_affected: Decimal
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
    if hasattr(o, "value") and isinstance(getattr(o, "value"), str):
        return o.value
    return o


def atom_dict(a: FeeAtom, role: AtomRole | None, aum: Decimal | None) -> dict:
    return {
        "id": a.atom_id, "fee_code": a.fee_code, "fee_label": FEE_LABEL_NAMES.get(a.fee_code, a.fee_code),
        "layer": a.layer.value, "label": a.label, "institution": a.institution, "instrument_id": a.instrument_id,
        "amount": None if a.amount is None else str(a.amount.quantize(Decimal("0.01"))),
        "bps": None if a.amount is None or not aum else str(bps_of(a.amount, aum)),
        "measurement": a.measurement.value, "incidence": a.incidence.value, "recurring": a.recurring,
        "included_in": a.included_in, "corroborates": a.corroborates, "role": role.value if role else None,
        "rate_bps": None if a.rate_bps is None else str(a.rate_bps), "basis_amount": None if a.basis_amount is None else str(a.basis_amount),
        "evidence_fact_ids": [int(x) for x in a.evidence_ids if str(x).isdigit()],
        "formula": a.formula, "note": a.note, "materiality": a.materiality,
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
        "verified_share": None if s.verified_share is None else str(s.verified_share.quantize(Decimal("0.001"))),
        "by_measurement": {k: str(v.quantize(Decimal("0.01"))) for k, v in s.by_measurement.items()},
        "by_layer": {k: str(v.quantize(Decimal("0.01"))) for k, v in s.by_layer.items()},
        "by_institution": {k: str(v.quantize(Decimal("0.01"))) for k, v in s.by_institution.items()},
        "by_instrument": {k: str(v.quantize(Decimal("0.01"))) for k, v in s.by_instrument.items()},
        "unknown": [a.atom_id for a in s.unknown],
        "warnings": s.warnings,
        "atoms": [atom_dict(a, s.roles.get(a.atom_id), s.scope_aum) for a in atoms],
    }


def analyse(prospect: dict, documents: list[dict], facts: list[dict], proposal: dict) -> dict:
    """documents: {id, filename, doc_type, profile}; facts: {id, document_id, key, kind, field, label, value,
    currency, isin, fee_code, measurement, extra, status}; proposal: see demo.spec.PROPOSAL_DEFAULTS."""
    live = [f for f in facts if f.get("status") != "rejected"]
    docs = {d["id"]: d for d in documents}
    by_doc: dict[int, list[dict]] = defaultdict(list)
    for f in live:
        by_doc[f["document_id"]].append(f)
    checks: list[Check] = []
    requests: list[MissingRequest] = []

    # ------------------------------------------------------------ institutions & positions
    holdings: list[dict] = []
    institutions: dict[str, dict] = {}
    for d in documents:
        if d["doc_type"] != "portfolio_statement":
            continue
        prof = d.get("profile") or {}
        ik = inst_key(prof.get("institution"))
        inst = institutions.setdefault(ik, {"name": ik, "legal_name": prof.get("institution"),
                                            "jurisdiction": prof.get("jurisdiction"), "as_of": prof.get("as_of"),
                                            "documents": [], "assets": ZERO})
        inst["documents"].append(d["id"])
        pos_sum, total_fact = ZERO, None
        for f in by_doc[d["id"]]:
            if f["kind"] == "doc_total":
                total_fact = f
            if f["kind"] != "position" or f["value"] is None:
                continue
            val = D(f["value"])
            ac, inferred = infer_asset_class(f["label"], (f.get("extra") or {}).get("asset_class"))
            holdings.append({"fact_id": f["id"], "document_id": d["id"], "institution": ik, "isin": f.get("isin"),
                             "name": f["label"], "asset_class": ac, "asset_class_inferred": inferred,
                             "value": val, "currency": f.get("currency") or "CHF",
                             "synthetic_isin": bool(f.get("isin") and is_synthetic(f["isin"]))})
            pos_sum += val
            inst["assets"] += val
        if total_fact:
            tot = D(total_fact["value"])
            ok = abs(tot - pos_sum) <= Decimal("1.00")
            checks.append(Check(f"reconcile:{d['id']}", f"{ik}: positions add up to the statement total",
                                "pass" if ok else "fail",
                                f"Sum of positions {pos_sum:,.2f} vs printed total {tot:,.2f}"
                                + ("" if ok else f" (difference {tot - pos_sum:,.2f}). Check for missing rows or accrued interest."),
                                [total_fact["id"]]))
        else:
            checks.append(Check(f"reconcile:{d['id']}", f"{ik}: statement total", "warn",
                                "No printed total found; completeness of the position list cannot be confirmed."))
    as_ofs = {i["as_of"] for i in institutions.values() if i["as_of"]}
    if len(as_ofs) > 1:
        checks.append(Check("valuation_dates", "Valuation dates are aligned", "warn",
                            f"Statements have different valuation dates: {', '.join(sorted(as_ofs))}."))
    elif as_ofs:
        checks.append(Check("valuation_dates", "Valuation dates are aligned", "pass",
                            f"All holdings valued at {next(iter(as_ofs))}."))
    isin_seen: dict[str, list[str]] = defaultdict(list)
    for h in holdings:
        if h["isin"]:
            isin_seen[h["isin"]].append(h["institution"])
    for isin, insts in isin_seen.items():
        if len(insts) > 1:
            checks.append(Check(f"dup:{isin}", f"{isin} appears {len(insts)} times", "warn",
                                "Same instrument in several statements: confirm these are separate holdings, "
                                "not a consolidated report repeating another bank's positions."))
    total_aum = sum((h["value"] for h in holdings), ZERO)
    cash = sum((h["value"] for h in holdings if h["asset_class"] == "CASH"), ZERO)
    if not holdings:
        requests.append(MissingRequest("holdings", 1, None, "Statement of assets for every bank",
                                       "Statement of assets / portfolio valuation at the same date for each account",
                                       "Without holdings no cost can be put in proportion to assets.",
                                       ["all outputs"], ZERO, "portfolio_statement"))

    # ------------------------------------------------------------ bank service costs
    atoms: list[FeeAtom] = []
    for d in documents:
        prof = d.get("profile") or {}
        ik = inst_key(prof.get("institution"))
        if d["doc_type"] == "cost_report":
            inst = institutions.setdefault(ik, {"name": ik, "legal_name": prof.get("institution"),
                                                "jurisdiction": prof.get("jurisdiction"), "as_of": None,
                                                "documents": [], "assets": ZERO})
            inst["documents"].append(d["id"])
            ps, pe = prof.get("period_start"), prof.get("period_end")
            days = (date.fromisoformat(pe) - date.fromisoformat(ps)).days + 1 if ps and pe else None
            if days and not 360 <= days <= 366:
                checks.append(Check(f"period:{d['id']}", f"{ik}: cost report covers 12 months", "warn",
                                    f"Report covers {days} days; amounts are annualised (× 365/{days})."))
            for f in by_doc[d["id"]]:
                if f["kind"] != "fee_observed" or f["value"] is None:
                    continue
                amt = D(f["value"])
                formula = f"reported for {ps} – {pe}"
                if days and not 360 <= days <= 366:
                    amt = amt * Decimal(365) / Decimal(days)
                    formula += f", annualised × 365/{days}"
                code = f["fee_code"]
                layer = LAYER_BY_CODE.get(code, Layer.OTHER)
                atoms.append(FeeAtom(f"cur:{ik}:{code}", code, layer, f"{ik} · {f['label']}", ik, amt,
                                     Measurement.OBSERVED, Incidence.TAX if code in TAX_CODES else Incidence.BILLED,
                                     evidence_ids=(str(f["id"]),), formula=formula))
    # cash debits corroborate (or, absent a report, establish) the annual figure
    for d in documents:
        if d["doc_type"] != "cash_statement":
            continue
        ik = inst_key((d.get("profile") or {}).get("institution"))
        for f in by_doc[d["id"]]:
            if f["kind"] != "cash_debit" or f["value"] is None:
                continue
            code = f["fee_code"]
            n = (f.get("extra") or {}).get("periods_per_year")
            annual = D(f["value"]) * (n or 1)
            target = f"cur:{ik}:{code}"
            aid = f"debit:{f['id']}"
            formula = f"{D(f['value']):,.2f} debited" + (f" × {n} periods per year" if n else " (period unknown, not annualised)")
            if any(a.atom_id == target for a in atoms):
                atoms.append(FeeAtom(aid, code, LAYER_BY_CODE.get(code, Layer.OTHER), f"{ik} · {f['label']}", ik,
                                     annual, Measurement.ESTIMATED if n else Measurement.OBSERVED, Incidence.BILLED,
                                     corroborates=target, evidence_ids=(str(f["id"]),), formula=formula))
            else:
                atoms.append(FeeAtom(target, code, LAYER_BY_CODE.get(code, Layer.OTHER), f"{ik} · {f['label']}", ik,
                                     annual, Measurement.ESTIMATED if n else Measurement.OBSERVED, Incidence.BILLED,
                                     evidence_ids=(str(f["id"]),), formula=formula,
                                     note="Annualised from a single debit; confirm with the annual cost report."))

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
        tariff = Tariff(f"doc{d['id']}", ik, tj or "??", date.fromisoformat(prof.get("as_of") or "1900-01-01"), None, "CHF")
        val_date = date.fromisoformat(institutions.get(target_inst, {}).get("as_of") or date.today().isoformat())
        if not booking:
            checks.append(Check(f"tariff:{d['id']}", f"{d['filename']}: tariff applicability", "warn",
                                "No holdings found for this institution, so the booking jurisdiction is unknown.",
                                [meta["id"]] if meta else []))
            continue
        ok, reason = tariff.applicability(booking, val_date)
        if not ok:
            checks.append(Check(f"tariff:{d['id']}", f"{target_inst}: price schedule rejected", "fail",
                                f"{reason} The document was kept for reference but is not used in any calculation.",
                                [meta["id"]] if meta else []))
            requests.append(MissingRequest(f"tariff:{target_inst}", 2, target_inst,
                                           f"{target_inst}: price schedule of the Swiss booking entity",
                                           f"Individual fee agreement or current price schedule issued by the {booking} "
                                           f"entity that books the account",
                                           "The uploaded schedule belongs to another legal entity/jurisdiction.",
                                           ["contractual cross-check"], institutions[target_inst]["assets"], "custody_tariff"))
            continue
        checks.append(Check(f"tariff:{d['id']}", f"{target_inst}: price schedule applies", "pass",
                            f"Issued by a {tj} entity, account booked in {booking}, in force on {val_date}.",
                            [meta["id"]] if meta else []))
        inst_hold = [h for h in holdings if h["institution"] == target_inst]
        bases = {"aum": sum((h["value"] for h in inst_hold), ZERO),
                 "custody_eligible": sum((h["value"] for h in inst_hold if h["asset_class"] != "CASH"), ZERO)}
        mins = {f["fee_code"]: D(f["value"]) for f in fs if f["field"] == "minimum" and (f.get("extra") or {}).get("per") == "year"}
        for f in fs:
            if f["field"] != "rate_pct" or f["fee_code"] not in ("ADVISORY_FEE", "MGMT_DISCRETIONARY", "CUSTODY_FEE"):
                continue
            base_key = "custody_eligible" if (f.get("extra") or {}).get("cash_excluded") else "aum"
            rule = FeeRule(f["fee_code"], f["label"], base_key, rate_bps=D(f["value"]) * 100, minimum=mins.get(f["fee_code"], 0))
            expected = rule.annual_amount(bases[base_key])
            observed = next((a for a in atoms if a.atom_id == f"cur:{target_inst}:{f['fee_code']}"), None)
            if observed:
                diff = observed.amount - expected
                st = "pass" if abs(diff) <= max(Decimal("1"), expected * Decimal("0.02")) else "warn"
                checks.append(Check(f"contract:{target_inst}:{f['fee_code']}",
                                    f"{target_inst}: {FEE_LABEL_NAMES.get(f['fee_code'], f['fee_code'])} matches the price schedule",
                                    st, f"Schedule implies {expected:,.2f} ({rule.formula(bases[base_key])}); "
                                        f"observed {observed.amount:,.2f}"
                                        + ("" if st == "pass" else f"; difference {diff:,.2f} — individual conditions or a different fee base?"),
                                    [f["id"]] + [int(x) for x in observed.evidence_ids]))
            else:
                atoms.append(FeeAtom(f"cur:{target_inst}:{f['fee_code']}", f["fee_code"],
                                     LAYER_BY_CODE.get(f["fee_code"], Layer.OTHER), f"{target_inst} · {f['label']}",
                                     target_inst, expected, Measurement.CONTRACTUAL, Incidence.BILLED,
                                     evidence_ids=(str(f["id"]),), formula=rule.formula(bases[base_key]),
                                     basis_amount=bases[base_key], rate_bps=rule.rate_bps))

    # unknown core service costs for every institution without evidence
    for ik, inst in institutions.items():
        have = {a.fee_code for a in atoms if a.institution == ik}
        for code, label, layer in SERVICE_CORE:
            present = bool(have & SERVICE_CODES) if code == "SERVICE" else code in have
            if not present:
                atoms.append(FeeAtom(f"cur:{ik}:{code}:unknown", "ADVISORY_FEE" if code == "SERVICE" else code, layer,
                                     f"{ik} · {label}", ik, None, Measurement.UNKNOWN, Incidence.BILLED,
                                     note="No fee report, debit or applicable contract found."))
        if not any(a.institution == ik and a.measurement == Measurement.OBSERVED for a in atoms):
            share = (inst["assets"] / total_aum * 100).quantize(Decimal("0.1")) if total_aum else ZERO
            requests.append(MissingRequest(
                f"cost_report:{ik}", 1, ik, f"{ik}: annual cost and charges report",
                "Annual report on costs and charges (ex-post) for the last 12 months, or all fee debit advices "
                "for the same period, plus the mandate/advisory agreement",
                f"No charged fee is documented for {ik} ({share}% of assets). Service, custody and trading "
                "costs are shown as UNKNOWN, not zero.",
                ["verified current total", "point estimate of the saving", "acquisition decision"],
                inst["assets"], "annual_cost_report"))

    # ------------------------------------------------------------ product costs
    product_docs: dict[str, list[dict]] = defaultdict(list)
    product_doc_meta: dict[str, dict] = {}
    for d in documents:
        if d["doc_type"] in ("kid", "termsheet"):
            for f in by_doc[d["id"]]:
                if f.get("isin"):
                    product_docs[f["isin"]].append(f)
                    product_doc_meta[f["isin"]] = d
    rates: list[ProductRate] = []
    extra_product_atoms: list[FeeAtom] = []
    for h in holdings:
        if h["asset_class"] in ("CASH", "EQUITY", "BOND"):
            continue
        isin = h["isin"]
        fs = product_docs.get(isin or "", [])
        if not fs:
            atoms_key = f"cur:{h['institution']}:{isin or h['name']}:PRODUCT_UNKNOWN"
            extra_product_atoms.append(FeeAtom(atoms_key, "FUND_ONGOING" if h["asset_class"] in ("FUND", "ETF") else "SP_ENTRY_COST",
                                               Layer.PRODUCT if h["asset_class"] in ("FUND", "ETF") else Layer.STRUCTURED,
                                               f"{h['name']} · product costs", h["institution"], None,
                                               Measurement.UNKNOWN, Incidence.EMBEDDED, instrument_id=isin,
                                               note="No KID / termsheet for this exact share class."))
            requests.append(MissingRequest(
                f"kid:{isin or h['name']}", 2, h["institution"], f"KID for {h['name']}",
                f"Key Information Document (PRIIPs KID or FinSA BIB) for ISIN {isin}, exact share class, current version"
                if isin else f"Product documentation for {h['name']}",
                f"Embedded costs of a CHF {h['value']:,.0f} position are unknown.",
                ["product cost of this position"], h["value"], "kid_priips"))
            continue
        doc = product_doc_meta[isin]
        ddate = (doc.get("profile") or {}).get("as_of")
        if ddate and (date.fromisoformat(institutions[h["institution"]]["as_of"] or ddate) - date.fromisoformat(ddate)).days > 548:
            checks.append(Check(f"stale:{isin}", f"{isin}: product document is older than 18 months", "warn",
                                f"Document dated {ddate}; costs may have changed. Request the current version."))
        for f in fs:
            code, meas = f["fee_code"], f.get("measurement")
            if code in ("FUND_ONGOING", "FUND_TRANSACTION", "FUND_PERFORMANCE", "FUND_MGMT_FEE", "SP_ONGOING", "SP_ENTRY_COST") and meas in ("estimated", "unknown"):
                if code == "FUND_PERFORMANCE" and f["value"] is not None and D(f["value"]) == 0:
                    continue
                rates.append(ProductRate(isin, code, _d(f["value"]),
                                         included_in_code=(f.get("extra") or {}).get("included_in"),
                                         evidence_ids=(str(f["id"]),), source_label=f"{doc['filename']}, dated {ddate or 'n/a'}"))
            elif meas == "maximum" and f["value"] is not None and D(f["value"]) > 0:
                amt = h["value"] * D(f["value"]) / 100
                extra_product_atoms.append(FeeAtom(
                    f"cur:{h['institution']}:{isin}:{code}:max", code, LAYER_BY_CODE.get(code, Layer.PRODUCT),
                    f"{h['name']} · {f['label']} (maximum)", h["institution"], amt, Measurement.MAXIMUM,
                    Incidence.EMBEDDED, instrument_id=isin, recurring=code.endswith("ONGOING"),
                    evidence_ids=(str(f["id"]),), formula=f"{h['value']:,.2f} × up to {f['value']}%",
                    note="Disclosed maximum, not the amount actually charged; not counted."))
            elif meas == "illustrative" and f["value"] is not None:
                extra_product_atoms.append(FeeAtom(
                    f"cur:{h['institution']}:{isin}:KID_ILLUSTRATION", "KID_ILLUSTRATION", Layer.PRODUCT,
                    f"{h['name']} · KID cost illustration", h["institution"], D(f["value"]), Measurement.ILLUSTRATIVE,
                    Incidence.EMBEDDED, instrument_id=isin, evidence_ids=(str(f["id"]),),
                    formula="manufacturer example on a 10'000 investment",
                    note="Hypothetical example from the KID; never a cost actually paid."))
    hold_inputs = [HoldingInput(h["isin"] or h["name"], h["name"], h["asset_class"], h["value"], h["institution"],
                                h["institution"]) for h in holdings]
    cur_product = product_atoms(hold_inputs, rates, "cur")
    for a in cur_product:
        if a.fee_code == "SP_ENTRY_COST" and a.measurement == Measurement.UNKNOWN:
            a.note = "Issuer margin not disclosed in the termsheet."
            h = next(x for x in holdings if x["isin"] == a.instrument_id)
            requests.append(MissingRequest(
                f"sp:{a.instrument_id}", 3, a.institution, f"Issuer cost data for {h['name']}",
                f"Issuer KID or SSPA cost data showing the issue price vs fair value for ISIN {a.instrument_id}",
                "The termsheet does not disclose the issuer margin; this embedded cost stays UNKNOWN.",
                ["structured product cost"], h["value"], "sp_termsheet"))
    current_atoms = atoms + cur_product + extra_product_atoms
    current = aggregate(current_atoms, scope_aum=total_aum or None)

    # bank's own reported product-cost estimate vs ours (reconciliation, never added)
    for d in documents:
        if d["doc_type"] != "cost_report":
            continue
        ik = inst_key((d.get("profile") or {}).get("institution"))
        rep = next((f for f in by_doc[d["id"]] if f["field"] == "reported_product_costs"), None)
        if rep:
            ours = sum((a.amount for a in cur_product if a.institution == ik and current.roles[a.atom_id] == AtomRole.COUNTED), ZERO)
            theirs = D(rep["value"])
            diff = ours - theirs
            pct = (diff / theirs * 100).quantize(Decimal("0.1")) if theirs else None
            st = "pass" if pct is not None and abs(pct) <= 5 else "warn"
            checks.append(Check(f"product_recon:{ik}", f"{ik}: product costs vs the bank's own estimate", st,
                                f"KID-based estimate {ours:,.2f} vs bank-reported {theirs:,.2f} ({pct:+}%). "
                                "The bank figure is used as a cross-check only, never added.", [rep["id"]]))
        retro = next((f for f in by_doc[d["id"]] if f["field"] == "retrocessions_received"), None)
        if retro:
            checks.append(Check(f"retro:{ik}", f"{ik}: retrocessions received", "info",
                                f"{ik} reports CHF {D(retro['value']):,.2f} of retrocessions paid out of product costs. "
                                "Not an extra client cost; under Swiss law they generally belong to the client unless "
                                "validly waived (to verify with counsel).", [retro["id"]]))
    for w in current.warnings:
        checks.append(Check(f"ledger:{len(checks)}", "Duplicate or inclusion check", "warn", w))
    if any(a.corroborates for a in current_atoms) and not current.warnings:
        checks.append(Check("corroboration", "Cash debits match the annual cost report", "pass",
                            "Quarterly debits × 4 equal the annual amounts; counted once."))

    # coverage matrix: institution × layer
    coverage = []
    for ik, inst in institutions.items():
        row = {"institution": ik, "assets": str(inst["assets"]), "jurisdiction": inst["jurisdiction"], "cells": {}}
        for layer in (Layer.SERVICE, Layer.CUSTODY, Layer.TRADING, Layer.PRODUCT, Layer.STRUCTURED, Layer.TAX):
            rel = [a for a in current_atoms if a.institution == ik and a.layer == layer
                   and current.roles[a.atom_id] in (AtomRole.COUNTED, AtomRole.UNKNOWN)]
            if not rel:
                row["cells"][layer.value] = "not_applicable"
            elif any(current.roles[a.atom_id] == AtomRole.UNKNOWN for a in rel):
                row["cells"][layer.value] = "partial" if any(current.roles[a.atom_id] == AtomRole.COUNTED for a in rel) else "unknown"
            else:
                order = ["observed", "contractual", "public_tariff", "estimated"]
                row["cells"][layer.value] = max((a.measurement.value for a in rel), key=order.index)
        coverage.append(row)

    # ------------------------------------------------------------ scenarios
    p = proposal
    vat = D(p.get("vat_pct", "0")) if prospect.get("domicile", "CH") == "CH" else ZERO
    custody_base = total_aum - cash
    bases = {"aum": total_aum, "custody_eligible": custody_base,
             "trade_notional": D(p.get("annual_turnover_chf", "0")), "fx_notional": D(p.get("fx_notional_chf", "0"))}
    tiers = [(None if u in (None, "") else D(u), D(r)) for u, r in p["eam_tiers"]]
    firm, custodian = p.get("firm_name", "Proposal"), p.get("custodian", "Proposed custodian")
    rules = [
        FeeRule("EAM_FEE", f"{firm} · management fee (EAM)", "aum", tiers=tiers,
                tier_method=TierMethod(p.get("eam_tier_method", "marginal"))),
        FeeRule("CUSTODY_FEE", f"{custodian} · custody fee", "custody_eligible", rate_bps=D(p["custody_bps"]),
                minimum=D(p.get("custody_min", "0"))),
        FeeRule("BROKERAGE", f"{custodian} · brokerage (assumed turnover)", "trade_notional", rate_bps=D(p["brokerage_bps"])),
        FeeRule("FX_COMMISSION", f"{custodian} · FX commission (assumed volume)", "fx_notional", rate_bps=D(p["fx_bps"])),
    ]
    svc: list[FeeAtom] = []
    for r in rules:
        amount = r.annual_amount(bases[r.base])
        inst_name = firm if r.fee_code == "EAM_FEE" else custodian
        svc.append(FeeAtom(f"prop:{r.fee_code}", r.fee_code, LAYER_BY_CODE.get(r.fee_code, Layer.OTHER), r.label,
                           inst_name, amount, Measurement.CONTRACTUAL, Incidence.BILLED, formula=r.formula(bases[r.base]),
                           basis_amount=bases[r.base], note="Proposal input (editable)"))
    if vat:
        vat_base = sum((a.amount for a in svc if a.fee_code in ("EAM_FEE", "CUSTODY_FEE")), ZERO)
        svc.append(FeeAtom("prop:VAT_ON_FEES", "VAT_ON_FEES", Layer.TAX, f"Swiss VAT {vat}% on management and custody fees",
                           firm, vat_base * vat / 100, Measurement.CONTRACTUAL, Incidence.TAX,
                           formula=f"{vat_base:,.2f} × {vat}% (client domiciled in CH)"))

    def cmp_view(atoms_: list[FeeAtom]) -> list[FeeAtom]:
        return [a for a in atoms_ if a.fee_code not in EXCLUDED_FROM_COMPARISON]

    same_product = product_atoms(hold_inputs, rates, "cur")  # identical holdings -> identical product costs
    same_unknown_product = [a for a in extra_product_atoms if a.measurement == Measurement.UNKNOWN]
    same_atoms = svc + same_product + same_unknown_product
    cur_cmp = aggregate(cmp_view(current_atoms), scope_aum=total_aum or None)
    same_sum = aggregate(same_atoms, scope_aum=total_aum or None)
    shared = {(a.instrument_id, a.fee_code) for a in same_sum.unknown} & {(a.instrument_id, a.fee_code) for a in cur_cmp.unknown}
    cur_ok = not any(a.materiality == "material" and (a.instrument_id, a.fee_code) not in shared for a in cur_cmp.unknown)
    same_ok = not any(a.materiality == "material" and (a.instrument_id, a.fee_code) not in shared for a in same_sum.unknown)
    mig = p.get("migration", {})
    transfer_cost = sum((D(v) for v in mig.values()), ZERO)
    same_cmp = compare(cur_cmp, same_sum, transfer_cost, True, cur_ok, same_ok)

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
            opt_rates.append(ProductRate(s["to"], "FUND_ONGOING", D(s["to_ongoing"]), source_label="proposal input"))
            opt_rates.append(ProductRate(s["to"], "FUND_TRANSACTION", D(s["to_transaction"]), source_label="proposal input"))
            old_rate = sum((r.rate_pct for r in rates if r.instrument_id == h.instrument_id and r.rate_pct is not None
                            and r.fee_code in ("FUND_ONGOING", "FUND_TRANSACTION")), ZERO)
            known_old = any(r.instrument_id == h.instrument_id for r in rates)
            swap_rows.append({"from": h.instrument_id, "from_name": h.name, "to": s["to"], "to_name": s["to_name"],
                              "value": str(h.value), "from_rate_pct": str(old_rate) if known_old else None,
                              "to_rate_pct": str(D(s["to_ongoing"]) + D(s["to_transaction"]))})
            rebuild += h.value * 2 * D(p["brokerage_bps"]) / Decimal(10000)
        else:
            opt_holdings.append(h)
    opt_product = product_atoms(opt_holdings, opt_rates, "cur")
    opt_unknown = [a for a in same_unknown_product if a.instrument_id not in swap_from]
    opt_sum = aggregate(svc + opt_product + opt_unknown, scope_aum=total_aum or None)
    opt_ok = not any(a.materiality == "material" and (a.instrument_id, a.fee_code) not in shared for a in opt_sum.unknown)
    cur_ok_opt = not any(a.materiality == "material" and ((a.instrument_id, a.fee_code) not in shared or a.instrument_id in swap_from)
                         for a in cur_cmp.unknown)
    opt_cmp = compare(cur_cmp, opt_sum, transfer_cost + rebuild, False, cur_ok_opt, opt_ok)

    internal = internal_economics([a for a in svc if a.fee_code == "EAM_FEE"],
                                  D(p["internal"]["servicing_cost"]), D(p["internal"]["onboarding_cost"]),
                                  same_cmp, evidence_complete=cur_ok, min_margin_pct=D(p["internal"]["min_margin_pct"]))

    requests.sort(key=lambda r: (r.priority, -r.assets_affected))
    excluded = [{"fee_code": a.fee_code, "label": a.label, "amount": str(a.amount), "reason": EXCLUDED_FROM_COMPARISON[a.fee_code]}
                for a in current_atoms if a.fee_code in EXCLUDED_FROM_COMPARISON and a.amount is not None]
    return _ser({
        "engine_version": ENGINE_VERSION,
        "synthetic": all(h["synthetic_isin"] for h in holdings if h["isin"]) and bool(holdings),
        "aum": {"total": total_aum, "cash": cash, "custody_eligible": custody_base,
                "by_institution": {k: v["assets"] for k, v in institutions.items()}},
        "institutions": [{**v, "assets": str(v["assets"])} for v in institutions.values()],
        "holdings": [{**h, "value": str(h["value"]),
                      "weight_pct": str((h["value"] / total_aum * 100).quantize(Decimal("0.1"))) if total_aum else None}
                     for h in holdings],
        "current": summary_dict(current, current_atoms),
        "coverage": coverage,
        "checks": [asdict(c) for c in checks],
        "requests": [asdict(r) for r in requests],
        "comparison_exclusions": excluded,
        "scenarios": {
            "current_comparable": summary_dict(cur_cmp, cmp_view(current_atoms)),
            "same_holdings": {"ledger": summary_dict(same_sum, same_atoms), "comparison": asdict(same_cmp),
                              "migration_items": mig},
            "optimized": {"ledger": summary_dict(opt_sum, svc + opt_product + opt_unknown), "comparison": asdict(opt_cmp),
                          "swaps": swap_rows, "rebuild_trading_cost": rebuild},
        },
        "internal": asdict(internal),
        "proposal_inputs": p,
        "client_domicile": prospect.get("domicile", "CH"),
    })
