"""Local detector for structured personal identifiers in extracted document text (SC-11.3).

Rules only, no model and no network: IBAN, Swiss AHV/AVS number and payment card (check digits
via python-stdnum), email, phone, and account/client numbers that sit next to a label. Check
digits are enforced so random digit runs are not flagged. Names and addresses need a model
(SC-11.9). ISINs are never flagged: public lookups depend on them (ADR 0004).

A ``Span`` holds offsets, never the matched text, so spans can be logged safely.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict
from stdnum import iban, luhn
from stdnum.ch import ssn

from pce.finance.isin import is_valid_isin

Kind = Literal["iban", "ahv", "card", "account", "phone", "email"]


class Span(BaseModel):
    """One detected identifier: character offsets into the scanned text and the rule that fired."""

    model_config = ConfigDict(frozen=True)

    kind: Kind
    start: int
    end: int


# A space or one line break between groups: narrow PDF columns wrap an IBAN onto the next line.
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:[ \n]?[A-Z0-9]{4}){2,7}(?:[ \n]?[A-Z0-9]{1,3})?\b")
# After the label, a failed check digit is an OCR misread (0/O, 1/l, 5/S), not a random number: hide it.
_IBAN_LABELLED = re.compile(
    r"\bIBAN\s*:?\s*([A-Z]{2}[0-9A-Z]{2}(?:[ \n]?[A-Za-z0-9]{4}){2,7}(?:[ \n]?[A-Za-z0-9]{1,3})?)\b"
)
_AHV = re.compile(r"\b756[.\s]?\d{4}[.\s]?\d{4}[.\s]?\d{2}\b")
_CARD = re.compile(r"\b[2-6]\d{3}(?:[ -]?\d{4}){2,3}(?:[ -]?\d{1,3})?\b")
_YEARS = re.compile(r"(?:(?:19|20)\d\d\s?){3,}(?:\d{1,3})?")  # performance tables: "2017 2018 2019 2020"
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_INTL = re.compile(r"(?<![\w+])(?:\+|00)[1-9]\d{0,2}(?:[\s./-]?\(0\))?(?:[\s./-]?\d{1,4}){2,6}\b")
# Swiss national format without a label ("091 123 45 67"): the 3-3-2-2 grouping is not used for amounts.
_PHONE_CH = re.compile(r"(?<![\d'.,])0[1-9]\d \d{3} \d{2} \d{2}(?![\d'.,])")
_PHONE_LABELLED = re.compile(
    r"\b(?:tel|telefono|telefon|phone|t[ée]l[ée]phone|t[ée]l|fax|mobile|cell|natel|cellulare)\.?\s*:?\s*"
    r"(0\d{1,3}(?:[\s./-]?\d{2,4}){2,4})\b",
    re.IGNORECASE,
)
# Label words that name an identifier, in IT/DE/FR/EN. The number must follow the label
# directly, so "Portfolio value: 1'234" is not an account; dates, periods and amounts are excluded below.
_BASE = (
    r"konto|conto|account|acct|compte|depot|deposito|dossier|rapporto|relazione|relationship|"
    r"portfolio|portafoglio|portefeuille|client|cliente|kunde|kunden|customer|mandat[eo]?|stamm"
)
_NUMWORD = r"(?:-?\s?(?:nr|no|n°|n|num|number|nummer|numero|num[ée]ro)\.?)"
_ACCOUNT = re.compile(
    rf"\b(?:(?:{_BASE})(?:{_NUMWORD})?\s*[:#]?|(?:{_BASE}){_NUMWORD}|(?:{_NUMWORD})\s*(?:de\s+)?(?:{_BASE}))"
    r"\s*([A-Z]{0,4}-?\d[\d./-]{3,30}\d)",
    re.IGNORECASE,
)
# Labelled numbers that are really dates, periods or amounts ("Konto 31.12.2025", "Portfolio 2025-2026").
_NOT_ID = re.compile(r"\d{1,2}\.\d{1,2}\.\d{2,4}|(?:19|20)\d\d[-/](?:19|20)?\d\d|\d+[.,]\d{2}")
_COMPOUND_ACCOUNT = re.compile(
    r"\b(?:kontonummer|kontonr|depotnummer|stammnummer|kundennummer|codice\s+cliente)\s*:?\s*"
    r"([A-Z]{0,4}-?\d[\d./-]{3,30}\d)",
    re.IGNORECASE,
)

# Earlier kinds win when spans overlap.
_PRIORITY: dict[str, int] = {"iban": 0, "ahv": 1, "card": 2, "account": 3, "phone": 4, "email": 5}


def _ibans(text: str) -> list[Span]:
    spans = []
    for m in _IBAN.finditer(text):
        raw = m.group()
        # The pattern can swallow a following word ("... 5295 7 CHF"); drop trailing groups until valid.
        while raw and not iban.is_valid(raw.replace("\n", " ")):
            raw = re.split(r"\s(?=\S*$)", raw)[0] if re.search(r"\s", raw) else ""
        if raw:
            spans.append(Span(kind="iban", start=m.start(), end=m.start() + len(raw)))
    for m in _IBAN_LABELLED.finditer(text):
        if 15 <= len(re.sub(r"\s", "", m.group(1))) <= 34:
            spans.append(Span(kind="iban", start=m.start(1), end=m.end(1)))
    return spans


def _digits(s: str) -> int:
    return sum(c.isdigit() for c in s)


def _repeats(text: str, found: list[Span]) -> list[Span]:
    """Every other place the same value appears: a statement repeats the account number in page headers
    without its label."""
    out = []
    for value, kind in {text[s.start : s.end]: s.kind for s in found if s.end - s.start >= 6}.items():
        for m in re.finditer(rf"(?<![\w.-]){re.escape(value)}(?![\w-]|\.\w)", text):
            out.append(Span(kind=kind, start=m.start(), end=m.end()))
    return out


def detect(text: str) -> list[Span]:
    """Return non-overlapping identifier spans in ``text``, ordered by position."""
    found = _ibans(text)
    found += [
        Span(kind="ahv", start=m.start(), end=m.end()) for m in _AHV.finditer(text) if ssn.is_valid(m.group())
    ]
    found += [
        Span(kind="card", start=m.start(), end=m.end())
        for m in _CARD.finditer(text)
        if 13 <= _digits(m.group()) <= 19
        and luhn.is_valid(re.sub(r"\D", "", m.group()))
        and not _YEARS.fullmatch(m.group())
    ]
    found += [Span(kind="email", start=m.start(), end=m.end()) for m in _EMAIL.finditer(text)]
    found += [
        Span(kind="phone", start=m.start(), end=m.end())
        for m in _PHONE_INTL.finditer(text)
        if 8 <= _digits(m.group()) <= 15
    ]
    found += [Span(kind="phone", start=m.start(1), end=m.end(1)) for m in _PHONE_LABELLED.finditer(text)]
    found += [Span(kind="phone", start=m.start(), end=m.end()) for m in _PHONE_CH.finditer(text)]
    for rx in (_ACCOUNT, _COMPOUND_ACCOUNT):
        found += [
            Span(kind="account", start=m.start(1), end=m.end(1))
            for m in rx.finditer(text)
            if _digits(m.group(1)) >= 5
            and not _NOT_ID.fullmatch(m.group(1))
            and not is_valid_isin(m.group(1).upper())
        ]
    found += _repeats(text, found)
    found.sort(key=lambda s: (s.start, _PRIORITY[s.kind], -(s.end - s.start)))
    kept: list[Span] = []
    for s in found:
        if kept and s.start < kept[-1].end:
            if _PRIORITY[s.kind] < _PRIORITY[kept[-1].kind]:
                kept[-1] = s
            continue
        kept.append(s)
    return kept


def mask(text: str, spans: list[Span]) -> str:
    """Replace each span with a stable token per distinct value: ``[IBAN_1]``, ``[EMAIL_2]``, ..."""
    tokens: dict[tuple[str, str], str] = {}
    counts: dict[str, int] = {}
    out, pos = [], 0
    for s in sorted(spans, key=lambda s: s.start):
        value = re.sub(r"[\s.\-/]", "", text[s.start : s.end]).upper()
        if (s.kind, value) not in tokens:
            counts[s.kind] = counts.get(s.kind, 0) + 1
            tokens[(s.kind, value)] = f"[{s.kind.upper()}_{counts[s.kind]}]"
        out += [text[pos : s.start], tokens[(s.kind, value)]]
        pos = s.end
    out.append(text[pos:])
    return "".join(out)
