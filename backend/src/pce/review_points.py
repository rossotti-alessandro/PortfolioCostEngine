"""Points an analyst should review first, ranked.

Pure function over the analysis payload (after `api.compute` attached inline provenance to each atom).
It never changes an amount: it only says where to look and why. The frontend owns the wording (EN/IT);
each point carries a `kind` and the variables its sentence needs.

Rate thresholds below are attention triggers chosen for review, not market data and not a fee claim.
"""

from __future__ import annotations

from decimal import Decimal

from .finance.money import D

HIGH, MEDIUM, LOW = "high", "medium", "low"
_RANK = {HIGH: 0, MEDIUM: 1, LOW: 2}

LOW_CONFIDENCE = Decimal("0.9")  # extraction confidence under this: read the source by eye
UNREVIEWED_SHARE = Decimal("0.05")  # an unchecked line worth >= 5% of the known total
LARGE_DRIVER_SHARE = Decimal("0.25")  # one line >= 25% of the known total

# Review thresholds in bps of the relevant base (holding value for product rates, bank assets otherwise).
REVIEW_BPS: dict[str, Decimal] = {
    "FUND_ONGOING": Decimal("200"),
    "FUND_TRANSACTION": Decimal("75"),
    "SP_ONGOING": Decimal("200"),
    "ADVISORY_FEE": Decimal("150"),
    "MGMT_DISCRETIONARY": Decimal("150"),
    "ALL_IN_FEE": Decimal("200"),
    "EAM_FEE": Decimal("150"),
    "CUSTODY_FEE": Decimal("50"),
    "BROKERAGE": Decimal("75"),
    "FX_COMMISSION": Decimal("50"),
}


def _point(
    kind: str,
    severity: str,
    *,
    atom: dict | None = None,
    fact_ids: list[int] | None = None,
    amount: str | None = None,
    **vars_: object,
) -> dict:
    return {
        "key": f"{kind}:{atom['id'] if atom else ','.join(map(str, fact_ids or []))}",
        "kind": kind,
        "severity": severity,
        "atom_id": atom["id"] if atom else None,
        "fact_ids": fact_ids if fact_ids is not None else (atom["evidence_fact_ids"] if atom else []),
        "amount": amount if amount is not None else (atom["amount"] if atom else None),
        "vars": {k: str(v) for k, v in vars_.items()},
    }


def _flag_point(atom: dict, flagged: list[dict], severity: str) -> dict:
    reasons = sorted({r for e in flagged for r in e["review"].get("reasons", [])})
    return _point(
        "extraction_flag",
        severity,
        atom=atom,
        fact_ids=[e["fact_id"] for e in flagged],
        label=atom["label"],
        reasons=",".join(reasons),
    )


def _rate_bps(atom: dict, bank_assets: dict[str, str]) -> Decimal | None:
    if atom.get("rate_bps") is not None:
        return D(atom["rate_bps"])
    base = bank_assets.get(atom.get("institution") or "")
    if atom.get("amount") is None or not base or D(base) == 0:
        return None
    return (D(atom["amount"]) / D(base) * 10000).quantize(Decimal("0.1"))


def review_points(result: dict) -> list[dict]:
    """Ranked list: severity first, then the amount at stake (unknown amounts rank by severity only)."""
    ledger = result["current"]
    total = D(ledger["total_known"])
    bank_assets = result.get("aum", {}).get("by_institution", {})
    points: list[dict] = []
    seen_facts: set[int] = set()

    for a in ledger["atoms"]:
        role = a.get("role")
        if role == "unknown":
            points.append(
                _point(
                    "not_determined",
                    HIGH if a["materiality"] == "material" else LOW,
                    atom=a,
                    label=a["label"],
                    fee=a["fee_label"],
                )
            )
            continue
        if role != "counted":
            # a flagged reading on a line that is not added still deserves a look, at low priority
            flagged = [
                e for e in a.get("evidence") or [] if (e.get("review") or {}).get("status") == "needs_review"
            ]
            if flagged:
                points.append(_flag_point(a, flagged, LOW))
            continue
        amount = D(a["amount"])
        share = amount / total if total else Decimal(0)
        ev = a.get("evidence") or []

        low = [e for e in ev if e.get("confidence") is not None and D(str(e["confidence"])) < LOW_CONFIDENCE]
        if low:
            points.append(
                _point(
                    "low_confidence",
                    HIGH,
                    atom=a,
                    fact_ids=[e["fact_id"] for e in low],
                    label=a["label"],
                    confidence=min(D(str(e["confidence"])) for e in low),
                )
            )
        flagged = [e for e in ev if (e.get("review") or {}).get("status") == "needs_review"]
        if flagged:
            points.append(_flag_point(a, flagged, HIGH))
        for e in ev:
            if e.get("status") == "corrected" and e["fact_id"] not in seen_facts:
                seen_facts.add(e["fact_id"])
                points.append(
                    _point(
                        "corrected",
                        LOW,
                        atom=a,
                        fact_ids=[e["fact_id"]],
                        label=a["label"],
                        old=e.get("value_extracted"),
                        new=e.get("value"),
                    )
                )
        if ev and share >= UNREVIEWED_SHARE and all(e.get("status") == "extracted" for e in ev):
            points.append(
                _point(
                    "unreviewed",
                    MEDIUM,
                    atom=a,
                    label=a["label"],
                    share=(share * 100).quantize(Decimal("0.1")),
                )
            )
        if a["measurement"] == "public_tariff":
            points.append(_point("list_price", MEDIUM, atom=a, label=a["label"]))
        rate = _rate_bps(a, bank_assets)
        limit = REVIEW_BPS.get(a["fee_code"])
        if rate is not None and limit is not None and rate > limit:
            points.append(_point("rate_high", MEDIUM, atom=a, label=a["label"], bps=rate, limit=limit))
        if share >= LARGE_DRIVER_SHARE:
            points.append(
                _point(
                    "large_driver",
                    LOW,
                    atom=a,
                    label=a["label"],
                    share=(share * 100).quantize(Decimal("0.1")),
                )
            )

    for c in result.get("checks", []):
        if c["status"] in ("fail", "warn"):
            points.append(
                {
                    "key": f"check:{c['key']}",
                    "kind": "check",
                    "severity": HIGH if c["status"] == "fail" else MEDIUM,
                    "atom_id": None,
                    "fact_ids": c.get("fact_ids", []),
                    "amount": None,
                    "vars": {"title": c["title"], "detail": c["detail"]},
                }
            )

    # fee amounts the layout finder saw that no parser used: candidates for a missing cost, never in a total
    by_doc: dict[str, list[dict]] = {}
    for m in result.get("unused_mentions", []):
        by_doc.setdefault(m["filename"], []).append(m)
    for filename, ms in by_doc.items():
        points.append(
            {
                "key": f"unused:{filename}",
                "kind": "unused_mentions",
                "severity": MEDIUM,
                "atom_id": None,
                "fact_ids": [m["fact_id"] for m in ms],
                "amount": None,
                "vars": {"n": str(len(ms)), "file": filename},
            }
        )

    points.sort(key=lambda p: (_RANK[p["severity"]], -(D(p["amount"]) if p["amount"] else Decimal(0))))
    return points
