"""Local detector for person names, postal addresses and birth dates (SC-11.9).

A small multilingual entity model (GLiNER2-PII, Apache-2.0, about 200M parameters, CPU) proposes spans;
this module keeps only those that look like a private person's data and then runs a narrow checker:

- drops proposals that are product, bank or company names, pronouns, form labels or ISINs: the cost
  analysis needs those visible, and the model flags them often on real documents;
- adds every other place a found name appears (a page header repeats ``BERNASCONI M.`` without a label)
  and the name after a holder label or a salutation the model missed;
- reports proposals between the two thresholds as ``uncertain``: they are hidden anyway (missing a name is
  a leak, hiding a word is not), and the caller can show them to a person.

The checker can only add spans, never remove one the rules found (``pce.pii.redact`` merges both).

Fully offline: the weights are fetched once with ``python -m pce.pii_names --download`` (pinned revision)
and loaded with the Hugging Face hub in offline mode, so no text or request leaves the machine at run time
(ADR 0004). Without the ``pii`` extra or the weights, ``available()`` is False and callers fall back.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal

from pce.finance.isin import is_valid_isin

Kind = Literal["name", "address", "birth_date"]

MODEL_ID = "fastino/gliner2-privacy-filter-PII-multi"
MODEL_REVISION = "1cb4166094dc58fa8d836429f060d6c95f62b495"  # pinned 2026-11-26
# Model label -> our kind. Narrow on purpose: wider label sets (city, country, document dates) over-mask.
LABELS: dict[str, Kind] = {
    "person": "name",
    "street_address": "address",
    "date_of_birth": "birth_date",
}
HIGH = 0.5  # at or above: hidden, not reported
LOW = 0.3  # between LOW and HIGH: hidden and reported as uncertain
_CHUNK = 900  # characters per model call; the encoder sees at most 512 tokens


@dataclass(frozen=True)
class Found:
    kind: Kind
    start: int
    end: int
    uncertain: bool = False


@dataclass
class Result:
    spans: list[Found] = field(default_factory=list)

    @property
    def uncertain(self) -> list[Found]:
        return [s for s in self.spans if s.uncertain]


# Words that make a proposal a product, institution or company, not a private person. Lower case.
_ORG_WORDS = {
    "ag", "sa", "s.a.", "sa.", "spa", "s.p.a.", "gmbh", "ltd", "plc", "inc", "llc", "sicav", "kg", "nv",
    "bank", "banca", "banque", "banco", "kantonalbank", "cantonale", "bancaria", "fund", "funds", "fonds",
    "fondo", "etf", "ucits", "trust", "capital", "asset", "assets", "management", "invest", "investments",
    "holding", "group", "gruppo", "privatbank", "wealth", "securities", "partners", "cie", "&", "co.",
    "index", "msci", "equity", "bond", "bonds", "global", "world", "selection", "portfolio", "sustainable",
}  # fmt: skip
# Pronouns, salutations and form labels the model reads as names. Lower case, whole proposal.
_NOT_NAMES = {
    "sie", "you", "your", "ihr", "ihre", "lei", "vous", "voi", "we", "us", "noi", "nous", "wir", "client",
    "cliente", "kunde", "customer", "investor", "investitore", "anleger", "investisseur", "manufacturer",
    "nome", "cognome", "nome e cognome", "name", "vorname", "nachname", "nom", "prénom", "first name",
    "last name", "surname", "full name", "signature", "firma", "unterschrift", "titolare", "inhaber",
    "titulaire", "account holder", "holder", "herr", "frau", "signor", "signora", "monsieur", "madame",
    "mr", "mrs", "ms", "dear", "gentile", "egregio", "cher", "chère", "sehr geehrter", "sehr geehrte",
}  # fmt: skip
# Labels that put a private person's name after them, up to the end of the line or a comma.
_HOLDER = re.compile(
    r"(?im)^[ \t]*(?:titolare|intestatario|cointestatari|inhaber(?:in)?|kontoinhaber|titulaire|"
    r"account holder|holder|beneficiary|beneficiario|beneficiaire|bénéficiaire)\s*:\s*([^\n,]{3,80})"
)
_SALUTATION = re.compile(
    r"(?i)\b(?:gentile|egregio|egregia|gentilissim[oa])\s+(?:signor[a]?|sig\.(?:ra)?|dott\.(?:ssa)?)\s+"
    r"|\bsehr geehrte[r]?\s+(?:herr|frau)\s+|\bch[eè]re?\s+(?:monsieur|madame)\s+"
    r"|\bdear\s+(?:mr|mrs|ms|dr)\.?\s+"
)
_NAME_AFTER_SALUTATION = re.compile(r"[A-ZÀ-ÖØ-Þ][\w'’-]+(?:\s+[A-ZÀ-ÖØ-Þ][\w'’-]+){0,2}")
_ISIN = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}\d\b")


def _words(s: str) -> list[str]:
    return re.findall(r"[\w.&'’-]+", s.lower())


_PARTICLES = {
    "de",
    "di",
    "da",
    "del",
    "della",
    "dei",
    "von",
    "van",
    "der",
    "den",
    "du",
    "des",
    "le",
    "la",
    "ten",
    "y",
}
_ROLE_WORDS = {
    "person", "manager", "investment", "investor", "investors", "depositary", "depositario", "dépositaire",
    "custodian", "berater", "anleger", "emittent", "emittente", "issuer", "distributor", "advisor", "adviser",
    "shareholder", "conto", "account", "sub-fund", "prospectus", "prospetto", "gestion", "gestione",
}  # fmt: skip
# Right after a name, these make it a firm: "Julius Bär & Co. AG", "Edmond de Rothschild (Suisse) S.A.".
_ORG_AFTER = re.compile(
    r"^[ \t]*(?:&|\(|-|,)?[ \t]*(?:co\b|cie\b|suisse|schweiz|svizzera|switzerland|luxembourg|lux\b|"
    r"ag\b|sa\b|s\.a\.|spa\b|s\.p\.a\.|gmbh|ltd|plc|inc\b|llc|sicav|bank|banca|banque|funds?\b|fonds|"
    r"asset|investments?|capital|group|holding|private|privatbank|wealth|securities|partners|gestion|sgr)",
    re.IGNORECASE,
)


def _is_firm(text: str, value: str) -> bool:
    """True when any occurrence of ``value`` on the page is followed by a company word."""
    for m in re.finditer(re.escape(value), text):
        if _ORG_AFTER.match(text[m.end() : m.end() + 30]):
            return True
    return False


# The model reads every date as a birth date; statements are full of dates the analysis needs. Only a date
# introduced by a birth label on the same line is personal.
_BIRTH = re.compile(
    r"(?i)(?:data di nascita|nato il|nata il|geburtsdatum|geboren(?: am)?|date de naissance|n[ée]e? le|"
    r"date of birth|born(?: on)?|d\.?o\.?b\.?)\s*:?\s*$"
)


def _birth_label_before(text: str, value: str) -> bool:
    for m in re.finditer(re.escape(value), text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        if _BIRTH.search(text[line_start : m.start()]):
            return True
    return False


def _keep(kind: Kind, value: str, text: str = "") -> bool:
    """False for proposals that are not a private person's data."""
    v = value.strip()
    if len(v) < 3:
        return False
    if any(is_valid_isin(m.group()) for m in _ISIN.finditer(v)):
        return False
    words = _words(v)
    if kind == "name":
        tokens = [t for t in re.split(r"\s+", v) if t]
        if v.lower() in _NOT_NAMES or re.search(r"\d", v):
            return False
        if any(w in _ORG_WORDS or w in _NOT_NAMES or w in _ROLE_WORDS for w in words):
            return False
        # A private person's name is at least two capitalised words (particles allowed in between);
        # a lone word ("Person", "Allianz", "Berater") is kept only through a label cue or a repeat.
        caps = [t for t in tokens if t.lower() not in _PARTICLES]
        if len(caps) < 2 or tokens[-1].lower() in _PARTICLES:
            return False
        if not all(re.match(r"[A-ZÀ-ÖØ-Þ]", t) for t in caps) or max(len(t) for t in caps) < 3:
            return False  # "T T MM": table headers, not people
        if text and _is_firm(text, v):
            return False
    if kind == "birth_date" and text and not _birth_label_before(text, value):
        return False
    if kind == "address":
        if not re.search(r"[A-Za-zÀ-ÿ]", v) or any(w in _ORG_WORDS for w in words):
            return False
    return True


def _cue_name(part: str) -> bool:
    """Looser test for a name a label introduced: one capitalised word is enough there."""
    p = part.strip()
    return (
        len(p) >= 2
        and bool(re.match(r"[A-ZÀ-ÖØ-Þ]", p))
        and not re.search(r"\d", p)
        and p.lower() not in _NOT_NAMES
        and not any(w in _ORG_WORDS or w in _ROLE_WORDS for w in _words(p))
    )


def _chunks(text: str) -> list[tuple[int, str]]:
    out, start = [], 0
    while start < len(text):
        end = min(len(text), start + _CHUNK)
        if end < len(text):
            nl = text.rfind("\n", start, end)
            end = nl + 1 if nl > start else end
        out.append((start, text[start:end]))
        start = end
    return out


@lru_cache(maxsize=1)
def _model() -> Any:
    # Offline before the import: the hub must not phone home, and the hosted-API client is never built.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from gliner2 import GLiNER2

    return GLiNER2.from_pretrained(MODEL_ID, revision=MODEL_REVISION, local_files_only=True)


@lru_cache(maxsize=1)
def available() -> bool:
    """True when the ``pii`` extra is installed and the pinned weights are on disk."""
    try:
        _model()
    except Exception:  # missing package, missing weights, broken install: all mean "not available"
        return False
    return True


def _propose(text: str) -> list[tuple[Kind, int, int, float]]:
    model = _model()
    out: list[tuple[Kind, int, int, float]] = []
    for off, chunk in _chunks(text):
        r = model.extract_entities(
            chunk, list(LABELS), threshold=LOW, include_confidence=True, include_spans=True
        )
        for label, values in r.get("entities", {}).items():
            for v in values:
                out.append((LABELS[label], off + v["start"], off + v["end"], float(v["confidence"])))
    return out


def _repeats(text: str, names: list[Found]) -> list[Found]:
    """Every other occurrence of a found name or of its parts (surname alone, ``SURNAME F.``).

    A repeat is as uncertain as the name it repeats, so a doubtful name stays reported."""
    parts: dict[str, bool] = {}
    for f in names:
        n = text[f.start : f.end]
        for p in [n, *(w for w in re.split(r"[\s&,]+", n) if len(w) >= 4 and w.lower() not in _NOT_NAMES)]:
            parts[p] = parts.get(p, True) and f.uncertain
    out = []
    for p, uncertain in parts.items():
        for m in re.finditer(rf"(?<![\w-]){re.escape(p)}(?:\s+[A-Z]\.)?(?![\w-])", text, re.IGNORECASE):
            if m.group()[0].isupper():  # "BERNASCONI" yes; a lower-case common word ("financial") no
                out.append(Found("name", m.start(), m.end(), uncertain))
    return out


def _cued(text: str) -> list[Found]:
    """Names after a holder label or a salutation, which the model sometimes misses (lone surnames)."""
    out = []
    for m in _HOLDER.finditer(text):
        for part in re.split(r"\s+(?:&|e|und|et|and)\s+", m.group(1).strip()):
            if part and _cue_name(part) and not _is_firm(text, part.strip()):
                s = text.index(part, m.start(1))
                out.append(Found("name", s, s + len(part)))
    for m in _SALUTATION.finditer(text):
        n = _NAME_AFTER_SALUTATION.match(text, m.end())
        if n and _cue_name(n.group()) and not _is_firm(text, n.group()):
            out.append(Found("name", n.start(), n.end()))
    return out


# "6900 Lugano", "8001 Zürich", "I-20121 Milano", "SW3 4LY London": the town line under a street.
_POSTAL = re.compile(
    r"[ \t]*((?:[A-Z]{1,2}-)?\d{4,5}[ \t]+[A-ZÀ-ÖØ-Þ][\w'’ .-]{1,40}"
    r"|[A-Z]{1,2}\d[A-Z\d]? \d[A-Z]{2}[ \t]+[A-Z][\w .-]{1,40})[ \t]*$",
    re.MULTILINE,
)


def _postal_lines(text: str, streets: list[Found]) -> list[Found]:
    """The postcode-and-town line right under a found street address, or after it on the same line."""
    out = []
    for f in streets:
        line_end = text.find("\n", f.end)
        line_end = len(text) if line_end < 0 else line_end
        m = _POSTAL.match(text, f.end, line_end) if text[f.end : f.end + 1] in (",", " ") else None
        if not m and line_end < len(text):
            nxt_end = text.find("\n", line_end + 1)
            m = _POSTAL.match(text, line_end + 1, len(text) if nxt_end < 0 else nxt_end)
        if m:
            out.append(Found("address", m.start(1), m.end(1)))
    return out


def detect(text: str) -> Result:
    """Names, addresses and birth dates in ``text``. Raises if the model is not available."""
    found = [
        Found(k, s, e, uncertain=score < HIGH)
        for k, s, e, score in _propose(text)
        if _keep(k, text[s:e], text)
    ]
    found += _postal_lines(text, [f for f in found if f.kind == "address"])
    found += _cued(text)
    found += _repeats(text, [f for f in found if f.kind == "name"])
    found.sort(key=lambda f: (f.start, -(f.end - f.start)))
    kept: list[Found] = []
    for f in found:  # merge overlaps; a span stays uncertain only if nothing confident covers it
        if kept and f.start < kept[-1].end:
            last = kept[-1]
            kept[-1] = Found(last.kind, last.start, max(last.end, f.end), last.uncertain and f.uncertain)
            continue
        kept.append(f)
    return Result(kept)


def _download() -> None:
    from huggingface_hub import snapshot_download

    path = snapshot_download(MODEL_ID, revision=MODEL_REVISION)
    print(f"weights for {MODEL_ID} in {path}")


if __name__ == "__main__":
    if sys.argv[1:] == ["--download"]:
        _download()
    else:
        print(f"name model available: {available()}")
