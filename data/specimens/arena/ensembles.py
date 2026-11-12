"""Ensemble workflows for the workflow arena (SC-5.10): combine the readers that already ran.

Two ways to use several independent readers on the same page, both built only from figures a reader
found at a page box (no new numbers):

    consensus  keep the base workflow's figures; a figure no other reader saw at the same spot with the
               same value goes to review ("a second pair of eyes")
    union      add figures only another reader found, always sent to review ("nothing missed silently")
"""

from __future__ import annotations

from decimal import Decimal


def _num(p: dict) -> Decimal | None:
    v = p.get("value")
    return Decimal(v) if v not in (None, "") else None


def same_spot(a: dict, b: dict, tol: float = 3.0) -> bool:
    """Same value (sign ignored, as in the scorer) and either box centre inside the other box."""
    va, vb, ba, bb = _num(a), _num(b), a.get("bbox"), b.get("bbox")
    if va is None or vb is None or abs(va) != abs(vb) or not ba or not bb:
        return False

    def inside(x: list[float], y: list[float]) -> bool:
        cx, cy = (x[0] + x[2]) / 2, (x[1] + x[3]) / 2
        return y[0] - tol <= cx <= y[2] + tol and y[1] - tol <= cy <= y[3] + tol

    return inside(ba, bb) or inside(bb, ba)


def consensus(base: list[dict], others: list[list[dict]]) -> list[dict]:
    out = []
    for p in base:
        q = dict(p)
        if not any(same_spot(p, o) for other in others for o in other):
            q["needs_review"] = True
            q["reasons"] = [*q.get("reasons", []), "no_second_reader"]
        out.append(q)
    return out


def union(base: list[dict], extra: list[dict]) -> list[dict]:
    added = [
        {**e, "needs_review": True, "reasons": [*e.get("reasons", []), "only_second_reader"]}
        for e in extra
        if _num(e) is not None and not any(same_spot(e, p) for p in base)
    ]
    return [*base, *added]
