"""Decimal helpers. Money is never a float anywhere in the engine.

Rounding policy: keep full precision through calculations; round only for
presentation (``money``) or where a contract states a rounding point.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

CENT = Decimal("0.01")
BPS = Decimal("10000")
ZERO = Decimal("0")


def D(value: object) -> Decimal:
    """Convert to Decimal without passing through binary float."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        raise TypeError("floats are not accepted for money; pass str or Decimal")
    if isinstance(value, bool):
        raise TypeError("bool is not a number")
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:  # pragma: no cover - message clarity
        raise ValueError(f"not a decimal number: {value!r}") from exc


def money(value: object) -> Decimal:
    return D(value).quantize(CENT, rounding=ROUND_HALF_EVEN)


def bps_of(amount: object, base: object) -> Decimal | None:
    """Amount expressed in basis points of base; None when base is zero."""
    base_d = D(base)
    if base_d == 0:
        return None
    return (D(amount) / base_d * BPS).quantize(Decimal("0.1"), rounding=ROUND_HALF_EVEN)


def parse_amount(raw: str) -> Decimal:
    """Parse a printed amount in Swiss/EU/US conventions.

    Handles ``1'234'567.89`` (Swiss), ``1’234.50``, ``1.234.567,89`` (EU),
    ``1,234,567.89`` (US), ``-1 234,50`` and trailing minus ``1'200.00-``.
    Ambiguous single-separator inputs like ``1.200`` or ``1,200`` are rejected
    so a human can confirm the locale instead of the engine guessing.
    """
    s = raw.strip().replace(" ", " ").replace("CHF", "").replace("EUR", "").replace("USD", "")
    s = s.strip()
    neg = False
    if s.endswith("-"):
        neg, s = True, s[:-1].strip()
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1].strip()
    if s.startswith("-") or s.startswith("−"):
        neg, s = True, s[1:].strip()
    s = s.replace("'", "").replace("’", "").replace(" ", "")
    if not s:
        raise ValueError("empty amount")
    has_dot, has_comma = "." in s, "," in s
    if has_dot and has_comma:
        if s.rfind(",") > s.rfind("."):  # EU: 1.234,56
            s = s.replace(".", "").replace(",", ".")
        else:  # US: 1,234.56
            s = s.replace(",", "")
    elif has_comma:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
            raise ValueError(f"ambiguous amount {raw!r}: thousands or decimal separator?")
        if len(parts) == 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_dot:
        parts = s.split(".")
        if len(parts) > 2:
            s = s.replace(".", "")
        elif len(parts[1]) == 3 and len(parts[0]) <= 3 and parts[0] not in ("0", ""):
            raise ValueError(f"ambiguous amount {raw!r}: thousands or decimal separator?")
    value = D(s)
    return -value if neg else value


def parse_percent(raw: str) -> Decimal:
    """'1.08%' -> Decimal('1.08') (percent units, not a fraction)."""
    s = raw.strip().rstrip("%").strip().replace(",", ".")
    return D(s)
