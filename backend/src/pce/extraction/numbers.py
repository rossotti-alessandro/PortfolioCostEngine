"""Printed numbers to ``Decimal``: one parser for every reader (text layer, OCR, VLM) (SC-5.8).

Swiss, German, Italian, French and English documents print the same amount as
``1'250.50``, ``1.250,50``, ``1 250,50`` or ``1,250.50``; rates as ``0,85 %``, ``25 bp``;
negatives as ``(3.28)``, ``-3.28`` or ``3.28-``. Getting this wrong silently changes a fee by
a factor of 1000, so the rules are explicit and unit-tested, and the parser refuses (returns
``None``) rather than guesses when a token is ambiguous.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

CURRENCY_WORDS = {
    "CHF": "CHF", "EUR": "EUR", "USD": "USD", "GBP": "GBP", "JPY": "JPY", "SGD": "SGD",
    "EURO": "EUR", "EUROS": "EUR", "€": "EUR", "$": "USD", "£": "GBP", "FR.": "CHF", "SFR.": "CHF",
}  # fmt: skip
_CCY = r"(?:Euros?|CHF|EUR|USD|GBP|JPY|SGD|€|\$|£|S?Fr\.)"
_DIGITS = (
    r"\d{1,3}(?:\.\d{3})+,\d+"  # 1.250,50
    r"|\d{1,3}(?:,\d{3})+\.\d+"  # 1,250.50
    r"|\d{1,3}(?:['’‘ʼ   ]\d{3})+(?:[.,]\d+)?"  # 1'250.50  1 250,50
    r"|\d{1,3}(?:[.,]\d{3})+(?![.,]?\d)"  # 1.250 or 1,250 (thousands, ambiguous: see _to_decimal)
    r"|\d+(?:[.,]\d+)?"  # 0.85  0,85  220
)
TOKEN = re.compile(
    rf"(?P<pre>{_CCY}\s?)?(?P<neg>[-−–]\s?|\()?(?P<num>{_DIGITS})(?P<close>\))?"
    rf"(?P<post>\s?(?:%|‰|bps?\b|bp\b|pb\b|Bp\b|{_CCY})|\.[-–]|,[-–]|-(?!\s*\d))?",
    re.I,
)


@dataclass(frozen=True)
class PrintedNumber:
    text: str  # as printed, including currency and unit
    value: Decimal  # signed; a rate keeps its printed scale (0.85 for "0.85 %")
    unit: str  # "%" | "‰" | "bp" | "" (plain number or amount)
    currency: str | None
    start: int  # span inside the source string
    end: int

    @property
    def is_rate(self) -> bool:
        return self.unit in ("%", "‰", "bp")

    @property
    def formatted(self) -> bool:
        """Printed with a decimal or thousands separator, or with a currency: looks like money."""
        return bool(re.search(r"[.,'’‘ʼ   ]\d", self.text)) or self.currency is not None


def _to_decimal(num: str, is_rate: bool) -> Decimal | None:
    s = re.sub(r"['’‘ʼ   ]", "", num)
    if "," in s and "." in s:  # the last separator is the decimal one
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        s = s.replace("." if dec == "," else ",", "").replace(",", ".")
    elif "," in s or "." in s:
        sep = "," if "," in s else "."
        parts = s.split(sep)
        if len(parts) > 2:  # 1.250.000 / 1,250,000: thousands only
            if any(len(p) != 3 for p in parts[1:]):
                return None
            s = "".join(parts)
        elif len(parts[1]) == 3 and not is_rate and parts[0] != "0":
            # "1,250" / "1.250": thousands in most documents here; a 3-decimal amount is rare.
            # Rates keep the decimal reading (0.125 %, 1,250 %).
            s = "".join(parts)
        else:
            s = s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def find_numbers(text: str) -> list[PrintedNumber]:
    """Every number printed in ``text`` with its unit and currency. Dates, ISIN digits and
    numbers glued to letters (``2a``, ``A1``) are not returned."""
    out: list[PrintedNumber] = []
    iso = [x.span() for x in re.finditer(r"\b\d{4}-\d\d-\d\d\b", text or "")]
    for m in TOKEN.finditer(text or ""):
        start, end = m.start(), m.end()
        before = text[max(0, start - 1) : start]
        after = text[end : end + 1]
        if any(a <= m.start("num") < b for a, b in iso):
            continue  # part of an ISO date 2026-09-30
        if before and (before.isalnum() or before in "./") and not m.group("pre"):
            continue  # inside a word, an ISIN, a date or a fraction
        if after and after.isalpha() and not m.group("post"):
            continue  # 3a, 10x, 2nd
        if re.match(r"[./]\d", text[end : end + 2]):
            continue  # first part of a date: 31.12.2025, 31/12, 2026-09-30
        post = (m.group("post") or "").strip()
        unit = (
            "%"
            if post == "%"
            else "‰"
            if post == "‰"
            else "bp"
            if post.lower() in ("bp", "bps", "pb")
            else ""
        )
        ccy_raw = (m.group("pre") or "").strip() or (
            post if unit == "" and not re.fullmatch(r"[.,]?[-–]", post) else ""
        )
        currency = CURRENCY_WORDS.get(ccy_raw.upper()) if ccy_raw else None
        if ccy_raw and currency is None and ccy_raw in ("€", "$", "£"):
            currency = CURRENCY_WORDS[ccy_raw]
        value = _to_decimal(m.group("num"), bool(unit))
        if value is None:
            continue
        neg = m.group("neg") or ""
        if neg and neg != "(" and re.search(r"\d\s*$", text[max(0, start - 3) : start]):
            neg = ""  # the dash of a range "0.5 – 1.0", not a minus sign
            start = m.start("num")
        if (neg.strip() in ("-", "−", "–")) or (neg == "(" and m.group("close")) or post == "-":
            value = -value
        elif neg == "(" and not m.group("close"):
            start += 1  # an opening bracket of a phrase, not a negative
        out.append(PrintedNumber(text[start:end].strip(), value, unit, currency, start, end))
    return out
