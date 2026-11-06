"""Per-document processing trace: what each pipeline stage did with one uploaded file.

Built from what is already stored (document row, its facts, the prospect analysis), so the analyst can
check every step from upload to the cost figure. Stage titles and summaries are English template keys;
the UI translates them. No document text is returned beyond the extracted labels the analyst reviews.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any

from .db import Document, FactRow

KIND_LABELS = {
    "position": "Holdings",
    "doc_total": "Printed totals",
    "fee_observed": "Fees charged",
    "cash_debit": "Fee debits",
    "fee_rule": "Tariff rules",
    "product_cost": "Product costs",
    "reported": "Reported cost figures",
    "meta": "Document details",
}
REVIEWED = ("accepted", "corrected", "manual")
# What the reader looks for in each document type; "not found" is shown, never assumed to be zero.
EXPECTED: dict[str, list[tuple[str, str]]] = {
    "portfolio_statement": [("position", "Holdings"), ("total", "Printed total")],
    "cost_report": [
        ("fee_observed", "Service costs charged"),
        ("total", "Total costs"),
        ("RETRO_RECEIVED", "Retrocessions"),
    ],
    "cash_statement": [("cash_debit", "Fee debits")],
    "tariff": [
        ("CUSTODY_FEE", "Custody fee"),
        ("BROKERAGE", "Brokerage"),
        ("ADVISORY_FEE", "Advisory or mandate fee"),
    ],
    "kid": [
        ("FUND_ONGOING", "Ongoing costs"),
        ("FUND_TRANSACTION", "Transaction costs"),
        ("FUND_ENTRY_CHARGE", "Entry charge"),
        ("FUND_EXIT_CHARGE", "Exit charge"),
        ("FUND_PERFORMANCE", "Performance fee"),
    ],
    "termsheet": [("SP_ENTRY_COST", "Entry costs"), ("SP_ONGOING", "Ongoing costs")],
}


def _stage(key: str, status: str, summary: str, ms: int | None = None, **kw: Any) -> dict:
    return {"key": key, "status": status, "summary": summary, "ms": ms, "vars": {}, "details": [], **kw}


def _worst(statuses: list[str]) -> str:
    for s in ("fail", "warn", "ok"):
        if s in statuses:
            return s
    return "skipped"


def document_pipeline(d: Document, facts: list[FactRow], analysis: dict, base_ccy: str) -> dict:
    prof = d.profile or {}
    ms = prof.get("timings_ms") or {}
    warnings: list[str] = prof.get("warnings") or []
    engines: list[str] = prof.get("engines") or []
    ids = {f.id for f in facts}
    stages: list[dict] = []

    stages.append(
        _stage(
            "upload",
            "ok",
            "File stored on this server and fingerprinted",
            ms.get("upload"),
            details=[
                {"label": "File", "value": d.filename},
                {"label": "Size", "value": f"{d.size:,} bytes"},
                {"label": "SHA-256", "value": d.sha256},
                {"label": "Uploaded by", "value": d.uploaded_by},
                {"label": "Uploaded at", "value": str(d.uploaded_at)[:19]},
            ],
        )
    )

    ocr = "tesseract-ocr" in engines
    sheet = "openpyxl" in engines or d.filename.lower().endswith(".xlsx")
    pages = d.pages or []
    stages.append(
        _stage(
            "read",
            "warn" if ocr else ("ok" if pages or sheet else "fail"),
            "Spreadsheet read cell by cell"
            if sheet
            else ("Pages read: {n}, some with OCR" if ocr else "Pages read as digital text: {n}"),
            ms.get("read"),
            vars={"n": len(pages)},
            details=[
                {
                    "label": f"Page {pg['number']}",
                    "value": "OCR" if pg["engine"] == "tesseract-ocr" else "text",
                }
                for pg in pages
            ],
            warnings=[w for w in warnings if "OCR" in w],
        )
    )

    detected, used = d.doc_type, d.doc_type_override or d.doc_type
    type_warn = [w for w in warnings if "OCR" not in w]
    stages.append(
        _stage(
            "classify",
            "warn" if used == "unknown" or type_warn else "ok",
            "Set manually as {type}" if detected != used else "Recognised as {type}",
            ms.get("classify"),
            vars={"type": used},
            details=[
                {"label": "Score", "value": str(prof.get("type_score", ""))},
                {"label": "Issuer", "value": prof.get("institution") or "–"},
                {"label": "Jurisdiction", "value": prof.get("jurisdiction") or "–"},
                {"label": "Language", "value": prof.get("language") or "–"},
                {"label": "Currency", "value": prof.get("currency") or "–"},
                {
                    "label": "Date / period",
                    "value": f"{prof['period_start']} → {prof['period_end']}"
                    if prof.get("period_start")
                    else (prof.get("as_of") or "–"),
                },
            ],
            warnings=type_warn,
        )
    )

    kinds = Counter(f.kind for f in facts)
    located = sum(1 for f in facts if (f.evidence or {}).get("bbox") or (f.evidence or {}).get("cell"))
    misses: list[dict] = prof.get("possible_misses") or []
    found = {f.fee_code for f in facts} | {f.kind for f in facts} | {f.key.split(":")[0] for f in facts}
    looked_for = [{"label": label, "found": code in found} for code, label in EXPECTED.get(used, [])]
    stages.append(
        _stage(
            "extract",
            ("warn" if misses else "ok") if facts else ("warn" if used != "unknown" else "skipped"),
            "{n} values found, {located} with their exact place in the file",
            ms.get("extract"),
            vars={"n": len(facts), "located": located},
            details=[{"label": KIND_LABELS.get(k, k), "value": str(n)} for k, n in kinds.most_common()],
            warnings=["{n} cost lines on the page were not read: check them"] if misses else [],
            warning_vars={"n": len(misses)},
            looked_for=looked_for,
            misses=misses,
            values=[
                {
                    "id": f.id,
                    "label": f.label,
                    "value": f.value_current,
                    "currency": f.currency,
                    "where": f"p.{f.evidence['page']}"
                    if (f.evidence or {}).get("page")
                    else f"{(f.evidence or {}).get('sheet')}!{(f.evidence or {}).get('cell')}",
                    "engine": (f.evidence or {}).get("engine") or "",
                    "confidence": (f.evidence or {}).get("confidence"),
                    "status": f.status,
                }
                for f in facts
                if f.kind != "meta"
            ],
        )
    )

    states = Counter(f.status for f in facts)
    pending = states.get("extracted", 0)
    stages.append(
        _stage(
            "review",
            "skipped" if not facts else ("warn" if pending else "ok"),
            "{done} of {n} values checked by a person",
            vars={"done": sum(states.get(s, 0) for s in REVIEWED), "n": len(facts)},
            details=[
                {"label": "Accepted", "value": str(states.get("accepted", 0))},
                {"label": "Corrected", "value": str(states.get("corrected", 0))},
                {"label": "Rejected", "value": str(states.get("rejected", 0))},
                {"label": "Waiting for review", "value": str(pending)},
            ],
        )
    )

    checks = [
        {k: c[k] for k in ("title", "status", "detail")}
        for c in analysis.get("checks", [])
        if ids & set(c.get("fact_ids") or []) or c.get("key", "").endswith(f":{d.id}")
    ]
    status_map = {"pass": "ok", "warn": "warn", "fail": "fail"}
    stages.append(
        _stage(
            "validate",
            _worst([status_map.get(c["status"], "warn") for c in checks]),
            "{pass} of {n} checks passed" if checks else "No cross-checks apply to this document",
            vars={"pass": sum(1 for c in checks if c["status"] == "pass"), "n": len(checks)},
            checks=checks,
        )
    )

    atoms = [a for a in analysis.get("current", {}).get("atoms", []) if ids & set(a["evidence_fact_ids"])]
    holdings = [h for h in analysis.get("holdings", []) if h.get("document_id") == d.id]
    stages.append(
        _stage(
            "categorize",
            "ok" if atoms else "skipped",
            "{n} costs placed in their cost layer" if atoms else "This document adds no cost line",
            vars={"n": len(atoms)},
            atoms=[
                {
                    "label": a["label"],
                    "fee_label": a["fee_label"],
                    "layer": a["layer"],
                    "measurement": a["measurement"],
                    "role": a["role"],
                    "amount": a["amount"],
                    "formula": a["formula"],
                }
                for a in atoms
            ],
        )
    )

    counted = [a for a in atoms if a["role"] == "counted" and a["amount"] is not None]
    contrib = sum((Decimal(a["amount"]) for a in counted), Decimal(0))
    held = sum((Decimal(h["value_ccy"]) for h in holdings if h.get("value_ccy")), Decimal(0))
    cur = analysis.get("current", {})
    stages.append(
        _stage(
            "result",
            "ok" if atoms or holdings else "skipped",
            "Adds {cost} {ccy} a year to the known cost of {total} {ccy}"
            if counted
            else "Adds no cost to the total; used for holdings, checks or as corroboration",
            vars={
                "cost": f"{contrib:,.2f}",
                "total": f"{Decimal(cur.get('total_known') or 0):,.2f}",
                "ccy": base_ccy,
            },
            details=[
                {
                    "label": "Holdings from this document",
                    "value": f"{len(holdings)} · {held:,.2f} {base_ccy}",
                },
                {"label": "Costs counted in the total", "value": str(len(counted))},
                {
                    "label": "Costs shown but not added",
                    "value": str(sum(1 for a in atoms if a["role"] != "counted")),
                },
                {"label": "Cost picture complete", "value": "yes" if cur.get("is_complete") else "no"},
            ],
        )
    )
    return {
        "document": {"id": d.id, "filename": d.filename, "doc_type": used, "prospect_id": d.prospect_id},
        "extractor_version": d.extractor_version,
        "total_ms": sum(v for v in ms.values() if isinstance(v, int)) or None,
        "stages": stages,
    }
