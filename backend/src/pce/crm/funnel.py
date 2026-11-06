"""Conversion funnel from stage history. Pure functions over plain dicts, so they are unit-testable.

Semantics:
- *reached* a stage = the contact's furthest funnel stage is at or beyond it. A contact moved straight
  from Lead to Won counts as having passed every stage in between (standard "at least" funnel).
- Lost contacts keep the furthest stage they reached before being lost.
- A ratio with a zero denominator is ``None`` (not determined), never 0.
- AUM is summed per currency; contacts without an estimate are counted, not treated as 0.
"""

from __future__ import annotations

import itertools
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from statistics import median
from typing import Any

from .models import FUNNEL_STAGES, LOST_REASONS, OPEN_STAGES, SOURCES, STAGE_LABELS

RATIO_Q = Decimal("0.0001")
DAYS_Q = Decimal("0.1")


def ratio(num: int, den: int) -> str | None:
    return None if den == 0 else str((Decimal(num) / Decimal(den)).quantize(RATIO_Q))


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _days(a: str, b: str) -> Decimal:
    return Decimal((_ts(b) - _ts(a)).total_seconds()) / Decimal(86400)


def _median_days(values: list[Decimal]) -> str | None:
    return str(median(values).quantize(DAYS_Q)) if values else None


def furthest_index(events: list[dict]) -> int:
    """Index in FUNNEL_STAGES of the furthest stage the contact ever entered (lost is not a step)."""
    idx = [FUNNEL_STAGES.index(e["to_stage"]) for e in events if e["to_stage"] in FUNNEL_STAGES]
    return max(idx, default=0)


def compute_funnel(contacts: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    by_contact: dict[int, list[dict]] = defaultdict(list)
    for e in sorted(events, key=lambda e: (e["at"], e.get("id", 0))):
        by_contact[e["contact_id"]].append(e)

    total = len(contacts)
    reached = Counter()
    durations: dict[str, list[Decimal]] = defaultdict(list)
    to_win: list[Decimal] = []
    current = Counter(c["stage"] for c in contacts)
    aum: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    aum_unknown = Counter()
    lost_reasons: dict[str, Counter] = defaultdict(Counter)
    by_source: dict[str, Counter] = defaultdict(Counter)

    for c in contacts:
        evs = by_contact.get(c["id"], [])
        far = furthest_index(evs)
        for i in range(far + 1):
            reached[FUNNEL_STAGES[i]] += 1
        for a, b in itertools.pairwise(evs):
            durations[a["to_stage"]].append(_days(a["at"], b["at"]))
        if c["stage"] == "won":
            won_at = next((e["at"] for e in reversed(evs) if e["to_stage"] == "won"), None)
            if won_at:
                to_win.append(_days(c["created_at"], won_at))
        if c["stage"] in OPEN_STAGES:
            if c.get("estimated_aum") is None:
                aum_unknown[c["stage"]] += 1
            else:
                aum[c["stage"]][c.get("currency") or "CHF"] += Decimal(c["estimated_aum"])
        if c["stage"] == "lost":
            lost_reasons[c.get("lost_reason") or "other"][FUNNEL_STAGES[far]] += 1
        src = by_source[c.get("source") or "other"]
        src["contacts"] += 1
        src[c["stage"] if c["stage"] in ("won", "lost") else "open"] += 1

    stages = []
    prev = None
    for s in FUNNEL_STAGES:
        stages.append(
            {
                "stage": s,
                "label": STAGE_LABELS[s],
                "reached": reached[s],
                "current": current[s],
                "share_of_total": ratio(reached[s], total),
                "conversion_from_previous": None if prev is None else ratio(reached[s], reached[prev]),
                "drop_off": None if prev is None else reached[prev] - reached[s],
                "median_days_in_stage": _median_days(durations[s]) if s != "won" else None,
                "aum": {k: str(v) for k, v in sorted(aum[s].items())},
                "aum_unknown": aum_unknown[s],
            }
        )
        prev = s

    won, lost = current["won"], current["lost"]
    open_aum: dict[str, Decimal] = defaultdict(Decimal)
    for per in aum.values():
        for k, v in per.items():
            open_aum[k] += v
    return {
        "total": total,
        "open": sum(current[s] for s in OPEN_STAGES),
        "won": won,
        "lost": lost,
        "win_rate": ratio(won, won + lost),
        "overall_conversion": ratio(won, total),
        "median_days_to_win": _median_days(to_win),
        "stages": stages,
        "lost_reasons": sorted(
            (
                {
                    "reason": r,
                    "label": LOST_REASONS.get(r, r),
                    "count": sum(cnt.values()),
                    "lost_after": {s: cnt[s] for s in FUNNEL_STAGES if cnt[s]},
                }
                for r, cnt in lost_reasons.items()
            ),
            key=lambda x: (-x["count"], x["reason"]),
        ),
        "by_source": sorted(
            (
                {
                    "source": s,
                    "label": SOURCES.get(s, s),
                    "contacts": cnt["contacts"],
                    "open": cnt["open"],
                    "won": cnt["won"],
                    "lost": cnt["lost"],
                    "win_rate": ratio(cnt["won"], cnt["won"] + cnt["lost"]),
                }
                for s, cnt in by_source.items()
            ),
            key=lambda x: (-x["contacts"], x["source"]),
        ),
        "pipeline_aum": {k: str(v) for k, v in sorted(open_aum.items())},
        "pipeline_aum_unknown": sum(aum_unknown.values()),
    }
