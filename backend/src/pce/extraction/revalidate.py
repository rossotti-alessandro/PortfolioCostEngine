"""Agentic revalidation of extracted fee values (SC-5.14).

After the reader has extracted a page (finder + verify, SC-5.8), each value goes through a small graph.
A supervisor routes it to specialists, and a decision node turns their opinions into a review status:

    triage ──reading doubt──▶ readers ──▶ reconcile ──▶ critic ──▶ decide
       └──────────────reading confirmed─────────┘    (optional)

- **triage** (supervisor, deterministic): a value whose reading is in doubt (the second reader disagreed
  or saw nothing) goes to the readers; the others skip them.
- **readers**: more independent readers of the value's box, cheapest first. The first one that reads the
  same number at the same place confirms the reading, and the escalation stops there.
- **reconcile**: arithmetic the page itself states. Rows that add up to the printed total, and a KID cost
  in % that matches its amount on the stated investment, confirm each other. Decimal only.
- **critic** (optional): a local language model asks "is this really a fee?". It may only flag.
- **decide**: reading doubts are cleared only by a confirmation; every other doubt and every flag stays,
  and the value goes to analyst review, out of the totals.

Guarantees, tested in ``tests/test_revalidate.py``:
- No specialist returns a number. Opinions are confirm / flag / abstain plus a short reason, so every
  value, label and box that leaves the graph is the one the reader found (file, page, position).
- Nothing is dropped. A figure can be confirmed or sent to review, never removed.
- A doubt that no specialist resolves stays a doubt (missing is not zero, unsure is not accepted).

Pages are independent, so callers may revalidate pages in parallel; the critic is the only slow node and
receives a whole page at once so a model can batch it. Text inside a document is data for the
specialists, never an instruction to them.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from .models import Check, Fact, Review
from .verify import TOTAL_WORDS

# Doubts about the number printed: a reader that sees the same number at the same place resolves them.
# Low OCR confidence is not one of them: it covers the whole line, so the label may be misread too
# (on the benchmark, readers "confirmed" such numbers under the wrong label).
READING_DOUBTS = {"engines_disagree", "not_confirmed"}
# A thousands separator ("1.250") is resolved only by arithmetic, not by another reader of the same digits.
ARITHMETIC_DOUBTS = READING_DOUBTS | {"separator_ambiguous"}
INVESTMENT = re.compile(r"(?<![\d.,'’])10[ '’.,]?000(?![\d])")  # PRIIPs cost examples use 10 000


class Verdict(StrEnum):
    CONFIRM = "confirm"
    FLAG = "flag"
    ABSTAIN = "abstain"


@dataclass(frozen=True)
class Opinion:
    specialist: str
    verdict: Verdict
    detail: str = ""


# A reader looks at one value; a page check or critic looks at a whole page and answers per fact index.
Reader = Callable[[Fact], Opinion]
PageSpecialist = Callable[[list[Fact]], dict[int, Opinion]]


@dataclass
class Specialists:
    readers: list[Reader] = field(default_factory=list)  # cheapest first
    checks: list[PageSpecialist] = field(default_factory=list)
    critic: PageSpecialist | None = None


@dataclass
class Case:
    """The graph state for one value: its fact, the opinions gathered and the path it took."""

    fact: Fact
    opinions: list[Opinion] = field(default_factory=list)
    path: list[str] = field(default_factory=list)


# ---------- nodes ----------


def triage(case: Case) -> str:
    reasons = set(case.fact.review.reasons) if case.fact.review else {"not_confirmed"}
    return "readers" if reasons & READING_DOUBTS else "reconcile"


def run_readers(case: Case, readers: list[Reader]) -> None:
    for read in readers:
        op = read(case.fact)
        case.opinions.append(op)
        if op.verdict is Verdict.CONFIRM:
            return  # two readers agree: no need to pay for a slower one


def decide(case: Case) -> Fact:
    """Turn the opinions into the review. Only ``review`` changes; value, label and box never do."""
    f = case.fact
    review = (
        f.review.model_copy(deep=True)
        if f.review
        else Review(status="needs_review", reasons=["not_confirmed"])
    )
    confirmed_by = {o.specialist for o in case.opinions if o.verdict is Verdict.CONFIRM}
    arithmetic = any(
        o.verdict is Verdict.CONFIRM and o.specialist.startswith("reconcile") for o in case.opinions
    )
    cleared = ARITHMETIC_DOUBTS if arithmetic else READING_DOUBTS if confirmed_by else set()
    reasons = [r for r in review.reasons if r not in cleared]
    reasons += [f"flagged_by_{o.specialist}" for o in case.opinions if o.verdict is Verdict.FLAG]
    review.reasons = list(dict.fromkeys(reasons))
    review.status = "needs_review" if review.reasons else "accepted"
    review.engines = [*review.engines, *sorted(confirmed_by - set(review.engines))]
    review.checks = [
        *review.checks,
        *(
            Check(name=f"revalidate:{o.specialist}", passed=o.verdict is Verdict.CONFIRM, detail=o.detail)
            for o in case.opinions
            if o.verdict is not Verdict.ABSTAIN
        ),
    ]
    f.extra = {**f.extra, "revalidation_path": [*case.path, "decide"]}
    f.review = review
    return f


# ---------- the graph ----------


def revalidate_page(facts: list[Fact], sp: Specialists) -> list[Fact]:
    """Run one page's facts through the graph. Returns the same facts, same order, review updated."""
    cases = [Case(f) for f in facts]
    for c in cases:
        c.path.append("triage")
        if triage(c) == "readers":
            c.path.append("readers")
            run_readers(c, sp.readers)
    for name, node in [("reconcile", sp.checks), ("critic", [sp.critic] if sp.critic else [])]:
        for check in node:
            for i, op in check(facts).items():
                if name == "critic" and op.verdict is not Verdict.FLAG:
                    continue  # the critic judges meaning, not reading: it may flag, never confirm
                cases[i].opinions.append(op)
        if node:
            for c in cases:
                c.path.append(name)
    return [decide(c) for c in cases]


def revalidate(facts: list[Fact], sp: Specialists) -> list[Fact]:
    """Every page of a document, one after another (pages are independent: callers may parallelise)."""
    by_page: dict[int | None, list[int]] = {}
    for i, f in enumerate(facts):
        by_page.setdefault(f.evidence.page, []).append(i)
    out: list[Fact | None] = [None] * len(facts)
    for idx in by_page.values():
        for i, f in zip(idx, revalidate_page([facts[i] for i in idx], sp), strict=True):
            out[i] = f
    return [f for f in out if f is not None]


# ---------- deterministic page checks (backend, no model) ----------


def _num(f: Fact) -> Decimal | None:
    return Decimal(f.value) if f.value not in (None, "") else None


def _overlap_x(a: list[float], b: list[float]) -> bool:
    return min(a[2], b[2]) - max(a[0], b[0]) > 0


def _same_row(a: list[float], b: list[float]) -> bool:
    return abs((a[1] + a[3]) / 2 - (b[1] + b[3]) / 2) <= max(a[3] - a[1], b[3] - b[1]) * 0.6


def reconcile_totals(facts: list[Fact]) -> dict[int, Opinion]:
    """A printed total equal to the sum of the same-unit rows above it in its column (at least two) confirms
    the total and every row in the sum: a misread digit anywhere would break the equality."""
    out: dict[int, Opinion] = {}
    boxed = [(i, f) for i, f in enumerate(facts) if f.evidence.bbox and _num(f) is not None]
    for ti, t in boxed:
        if not TOTAL_WORDS.search(t.label.split("|")[0].split("›")[-1]):
            continue
        tb = t.evidence.bbox
        col = [
            (i, f)
            for i, f in boxed
            if i != ti
            and f.field == t.field
            and f.evidence.bbox[3] <= tb[1]
            and _overlap_x(f.evidence.bbox, tb)
            and not TOTAL_WORDS.search(f.label.split("|")[0].split("›")[-1])
        ]
        # the rows nearest the total first: a column may hold several blocks, each with its own total
        col.sort(key=lambda x: -x[1].evidence.bbox[1])
        run = Decimal(0)
        for n, (_, f) in enumerate(col, start=1):
            run += Decimal(f.value or 0)
            if n >= 2 and run == _num(t):
                op = Opinion("reconcile_totals", Verdict.CONFIRM, f"{n} rows add up to {t.value}")
                for i, _f in [(ti, t), *col[:n]]:
                    out[i] = op
                break
    return out


def reconcile_kid_pct(facts: list[Fact]) -> dict[int, Opinion]:
    """PRIIPs KIDs show each cost as an amount on a 10 000 investment and as a %: on the same row,
    amount / 10 000 x 100 rounded to the printed decimals equals the printed % when both were read right."""
    snippets = " ".join(f.evidence.snippet for f in facts) + " " + " ".join(f.label for f in facts)
    if not INVESTMENT.search(snippets):
        return {}
    out: dict[int, Opinion] = {}
    amounts = [(i, f) for i, f in enumerate(facts) if f.field == "amount" and f.evidence.bbox and _num(f)]
    rates = [(i, f) for i, f in enumerate(facts) if f.field == "rate_pct" and f.evidence.bbox and _num(f)]
    for ai, a in amounts:
        for ri, r in rates:
            if not _same_row(a.evidence.bbox, r.evidence.bbox):
                continue
            amount, pct = abs(Decimal(a.value or 0)), abs(Decimal(r.value or 0))
            step = Decimal(1).scaleb(pct.as_tuple().exponent)  # the printed decimals of the %
            if (amount / 10000 * 100).quantize(step, ROUND_HALF_UP) == pct:
                op = Opinion("reconcile_kid_pct", Verdict.CONFIRM, f"{a.value} on 10 000 = {r.value} %")
                out[ai] = out[ri] = op
    return out


BACKEND_CHECKS: list[PageSpecialist] = [reconcile_totals, reconcile_kid_pct]
