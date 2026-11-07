"""Number normalisation and the shared fee-line extractor for the benchmark (SC-5.6).

The same extractor runs on every engine's text, so differences in the score come from
what the engine read, not from per-engine parsing. It is deliberately simple: a line
(or table row) with a fee word and a number. FeeLens' real parsers are richer; this
measures the input they would get.
"""

from __future__ import annotations

import re

FEE_WORDS = re.compile(
    r"(fee|cost|charge|commission|expense|\bter\b|\bocf\b|spread|custody|brokerage|safekeeping|"
    r"geb[üu]hr|kosten|kommission|courtage|depot|spesen|entgelt|aufschlag|ausgabe|r[üu]cknahme|"
    r"frais|droit|garde|tenue|"
    r"cost[io]|commission[ei]|spes[ae]|oner[ei]|custodia|diritt[oi]|tenuta)",
    re.I,
)

# A number as printed: 1.78 % / 1,78% / 1'250.00 / 1 250,00 / 0.05 / 25 bp / CHF 30
NUM = re.compile(
    r"(?<![\w.,])(\d{1,3}(?:\.\d{3})+,\d+|\d{1,3}(?:[ '’  ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)\s*(%|‰|bps?|bp\b)?",
    re.I,
)


def canon(num: str, unit: str | None = None) -> str | None:
    """Canonical form of one printed number: '1,78 %' -> '1.78%', "1'250.00" -> '1250'."""
    s = re.sub(r"[ '’  ]", "", num)
    if "," in s and "." in s:  # 1.250,50 or 1,250.50: the last separator is the decimal one
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        s = s.replace("." if dec == "," else ",", "").replace(",", ".")
    elif "," in s:
        head, _, tail = s.rpartition(",")
        s = s.replace(",", "") if len(tail) == 3 and head.isdigit() and len(head) <= 3 and unit != "%" else s.replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return None
    txt = f"{v:.6f}".rstrip("0").rstrip(".")
    u = (unit or "").lower()
    if u.startswith("bp"):
        u = "bp"
    return txt + ("%" if u == "%" else "‰" if u == "‰" else "bp" if u == "bp" else "")


def numbers(text: str) -> list[str]:
    """All canonical numbers in a text, with units where printed."""
    out = []
    for m in NUM.finditer(text or ""):
        c = canon(m.group(1), m.group(2))
        if c is not None:
            out.append(c)
    return out


def value_key(value: str) -> str | None:
    """The canonical number of a ground-truth value string (first number in it)."""
    ns = numbers(value)
    return ns[0] if ns else None


def bare(c: str) -> str:
    return re.sub(r"(%|‰|bp)$", "", c)


def same_number(gt: str, found: str) -> bool:
    """A found number matches when the digits agree; a missing unit on one side is tolerated."""
    return bare(gt) == bare(found) and (gt == found or not re.search(r"\D$", found) or not re.search(r"\D$", gt))


def label_tokens(label: str) -> set[str]:
    return {t for t in re.findall(r"[a-zà-ÿ]{4,}", label.lower())}


def extract_fee_lines(text: str) -> list[dict]:
    """Shared extractor: every number on a line or table row that also has a fee word."""
    items = []
    for line in (text or "").splitlines():
        if not FEE_WORDS.search(line):
            continue
        for c in numbers(line):
            if re.fullmatch(r"(19|20)\d\d", c):  # a year, not a fee
                continue
            items.append({"value": c, "line": line.strip()[:200]})
    return items


def extract_fee_tables(tables: list[dict], context: str = "") -> list[dict]:
    """Table-aware extractor: in a table about fees, every rate or amount cell is a fee candidate.

    A table is "about fees" when any of its cells, or the text just above it (context), has a
    fee word. This is what a table model buys: the fee word sits in a header or a section title,
    not on the row with the number.
    """
    items = []
    for t in tables:
        cells = [c or "" for row in t["rows"] for c in row]
        if not (FEE_WORDS.search(" ".join(cells)) or FEE_WORDS.search(context)):
            continue
        for row in t["rows"]:
            line = " | ".join(c or "" for c in row)
            for c in numbers(line):
                if re.fullmatch(r"(19|20)\d\d", c) or (c.isdigit() and int(c) < 10):
                    continue  # years and bare small integers (footnote marks, counts)
                items.append({"value": c, "line": line[:200]})
    return items
