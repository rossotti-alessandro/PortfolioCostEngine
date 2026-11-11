"""Fact-level matching and scores. The one matching rule every strategy is scored with.

A predicted fact matches a gold item when, on the same document (and page when both give one):
- the gold item names a fact key and the fact has that key, or
- both carry a fee code and the codes are equal, or
- at least half of the gold label's words (lowercase, accents stripped, >= 3 letters) appear in the
  fact's label + evidence snippet.
A match with an equal value (Decimal after normalisation, no tolerance) is ``correct``; a match with a
different value is ``wrong_value``, the dangerous error: a confident, wrong number. A gold value of
``None`` means "must stay unknown": a predicted number there, zero included, is ``wrong_value`` and also
counts as ``missing_as_zero`` when it is 0. Matching is one-to-one and greedy, value-equal first.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel

# A number as printed: 1.78 % / 1,78% / 1'250.00 / 1.250,50 / 1\u202f250,00 / 900’000. A plain space is
# not a thousands separator here: table cells are space-separated ("4'500 200.00").
_NUM = re.compile(r"-?\d{1,3}(?:[.,'’\u00a0\u202f]\d{3}(?!\d))+(?:[.,]\d+)?|-?\d+(?:[.,]\d+)?")
_WORD = re.compile(r"[a-z]{3,}")


def numbers(text: str | None) -> list[Decimal]:
    """Every number printed in ``text`` as Decimal (no floats anywhere)."""
    out = []
    for raw in _NUM.findall(text or ""):
        s = re.sub(r"['’\u00a0\u202f]", "", raw)
        if "," in s and "." in s:  # the last separator is the decimal one
            dec = "," if s.rfind(",") > s.rfind(".") else "."
            s = s.replace("." if dec == "," else ",", "").replace(",", ".")
        elif s.count(",") == 1 and len(s.split(",")[1]) != 3:
            s = s.replace(",", ".")
        elif s.count(".") > 1 or s.count(",") >= 1:  # 1.250.000 / 1,250 / 1,250,000
            s = s.replace(",", "").replace(".", "")
        try:
            out.append(Decimal(s))
        except InvalidOperation:
            continue
    return out


def to_decimal(value: str | None) -> Decimal | None:
    """The first number of a value string ('1,08 %' -> 1.08, 'Up to €300' -> 300), or None."""
    ns = numbers(value)
    return ns[0] if ns else None


def same_value(a: Decimal | None, b: Decimal | None) -> bool:
    return (a is None and b is None) or (a is not None and b is not None and a == b)


def words(text: str | None) -> set[str]:
    t = unicodedata.normalize("NFKD", (text or "").lower())
    return set(_WORD.findall("".join(c for c in t if not unicodedata.combining(c))))


class GoldItem(BaseModel):
    """One labelled value. ``value=None`` means the truth is "not determined" and must stay unknown."""

    file: str
    value: str | None
    key: str | None = None
    label: str = ""
    fee_code: str | None = None
    page: int | None = None
    bbox: list[float] | None = None  # the value's box, PDF points, top-left origin


def label_match(gold: GoldItem, fact: dict) -> bool:
    if gold.key:
        return fact.get("key") == gold.key
    if gold.fee_code and fact.get("fee_code"):
        return gold.fee_code == fact["fee_code"]
    want = words(gold.label)
    have = words(f"{fact.get('label', '')} {(fact.get('evidence') or {}).get('snippet', '')}")
    return bool(want) and len(want & have) * 2 >= len(want)


def _page_ok(gold: GoldItem, fact: dict) -> bool:
    page = (fact.get("evidence") or {}).get("page")
    return gold.page is None or page is None or gold.page == page


def bbox_hit(gold: GoldItem, fact: dict) -> bool | None:
    """Does the fact's box contain the centre of the gold value box? None when either has no box."""
    fb = (fact.get("evidence") or {}).get("bbox")
    if not gold.bbox or not fb:
        return None
    cx, cy = (gold.bbox[0] + gold.bbox[2]) / 2, (gold.bbox[1] + gold.bbox[3]) / 2
    return fb[0] - 1 <= cx <= fb[2] + 1 and fb[1] - 1 <= cy <= fb[3] + 1


@dataclass
class Outcome:
    gold: GoldItem
    fact: dict | None
    status: str  # correct | wrong_value | missed
    missing_as_zero: bool = False


@dataclass
class Scores:
    gold: int = 0
    predicted: int = 0  # facts in scope for precision (None when the gold list is not exhaustive)
    correct: int = 0
    wrong_value: int = 0
    missing_as_zero: int = 0
    missed: int = 0
    gold_valued: int = 0  # gold items with a number (not "must stay unknown")
    value_found: int = 0  # of those, values present somewhere among the predicted facts, label ignored
    bbox_checked: int = 0
    bbox_hits: int = 0
    exhaustive: bool = True
    outcomes: list[Outcome] = field(default_factory=list)

    def add(self, other: Scores) -> None:
        for k in (
            "gold",
            "gold_valued",
            "predicted",
            "correct",
            "wrong_value",
            "missing_as_zero",
            "missed",
            "value_found",
            "bbox_checked",
            "bbox_hits",
        ):
            setattr(self, k, getattr(self, k) + getattr(other, k))
        self.exhaustive = self.exhaustive and other.exhaustive
        self.outcomes += other.outcomes

    @property
    def recall(self) -> float | None:
        return self.correct / self.gold if self.gold else None

    @property
    def precision(self) -> float | None:
        return self.correct / self.predicted if self.exhaustive and self.predicted else None

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p and r else None

    @property
    def wrong_value_rate(self) -> float | None:
        """Share of matched predictions that carry a wrong number: the error the product cannot afford."""
        n = self.correct + self.wrong_value
        return self.wrong_value / n if n else None

    @property
    def value_recall(self) -> float | None:
        return self.value_found / self.gold_valued if self.gold_valued else None

    @property
    def bbox_hit_rate(self) -> float | None:
        return self.bbox_hits / self.bbox_checked if self.bbox_checked else None

    def summary(self) -> dict:
        r = lambda x: None if x is None else round(x, 4)  # noqa: E731
        return {
            "gold": self.gold,
            "predicted": self.predicted if self.exhaustive else None,
            "correct": self.correct,
            "wrong_value": self.wrong_value,
            "missing_as_zero": self.missing_as_zero,
            "missed": self.missed,
            "precision": r(self.precision),
            "recall": r(self.recall),
            "f1": r(self.f1),
            "wrong_value_rate": r(self.wrong_value_rate),
            "value_recall": r(self.value_recall),
            "bbox_hit_rate": r(self.bbox_hit_rate),
        }


def score(gold: list[GoldItem], facts: list[dict], exhaustive: bool = True) -> Scores:
    """Score one document's predicted ``facts`` (fact dicts as the pipeline emits them) against ``gold``.

    ``exhaustive``: the gold list holds every value of the kinds in scope, so unmatched predictions are
    false positives and precision is defined. Partial lists (a few values a human read) give recall only.
    """
    s = Scores(gold=len(gold), predicted=len(facts), exhaustive=exhaustive)
    free = list(range(len(facts)))
    values = [to_decimal(f.get("value")) for f in facts]
    for g in gold:
        want = to_decimal(g.value) if g.value is not None else None
        s.gold_valued += want is not None
        if want is not None and any(v == want and _page_ok(g, f) for v, f in zip(values, facts, strict=True)):
            s.value_found += 1
        cands = [i for i in free if _page_ok(g, facts[i]) and label_match(g, facts[i])]
        if not cands:
            s.missed += 1
            s.outcomes.append(Outcome(g, None, "missed"))
            continue
        # value-equal candidate first; otherwise the first in reading order (the one an analyst would see)
        best = next((i for i in cands if same_value(values[i], want)), cands[0])
        free.remove(best)
        fact, got = facts[best], values[best]
        if same_value(got, want):
            s.correct += 1
            s.outcomes.append(Outcome(g, fact, "correct"))
            hit = bbox_hit(g, fact)
            if hit is not None:
                s.bbox_checked += 1
                s.bbox_hits += hit
        else:
            zero = got == 0 and (want is None or want != 0)
            s.wrong_value += 1
            s.missing_as_zero += zero
            s.outcomes.append(Outcome(g, fact, "wrong_value", zero))
    return s
