"""ISIN format and ISO 6166 check-digit validation.

A valid checksum proves only that the string is well formed. It does not prove
the instrument exists, is a fund, or is the share class the client holds.
Country code ``ZZ`` is reserved in this project for synthetic demo instruments.
"""

from __future__ import annotations

import re

ISIN_RE = re.compile(r"\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b")
SYNTHETIC_PREFIX = "ZZ"


def _digits(body: str) -> str:
    return "".join(str(int(c, 36)) for c in body)


def check_digit(first11: str) -> int:
    digits = _digits(first11.upper())
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return (10 - total % 10) % 10


def is_valid_isin(code: str) -> bool:
    code = code.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", code):
        return False
    return check_digit(code[:11]) == int(code[11])


def is_synthetic(code: str) -> bool:
    return code.upper().startswith(SYNTHETIC_PREFIX)


def make_synthetic_isin(serial: str) -> str:
    """Build a checksum-valid synthetic ISIN 'ZZ' + 9 alphanumerics + check digit."""
    body = (SYNTHETIC_PREFIX + serial.upper()).ljust(11, "0")[:11]
    return body + str(check_digit(body))


def find_isins(text: str) -> list[str]:
    return [m for m in ISIN_RE.findall(text.upper()) if is_valid_isin(m)]
