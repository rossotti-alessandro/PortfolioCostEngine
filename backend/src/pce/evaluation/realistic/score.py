"""Score the app's own ``extract()`` on every statement and condition, against the gold files.

Per document it measures, with no tolerance on values (Decimal equality):
- words and figures: tokens of the born-digital text layer found again in what the reader produced
  (multiset recall); figures are tokens with a digit. This is "how much of the wording was read right".
- holdings: gold ISIN read with the exact value; wrong = an ISIN read with another value, or an ISIN that
  is not on the statement.
- assets: the printed total read exactly.
- fees: each gold fee read with the exact amount (and, separately, with the right fee code); wrong = a fee
  figure on the fee page that matches no printed fee.
- wrong_accepted: wrong holdings or fees the app did not flag for review. The safety number.
- PII: planted identifiers the local detector (``pce.pii``) covers, and gold figures that masking destroys.
"""

from __future__ import annotations

import re
import time
from collections import Counter
from decimal import Decimal, InvalidOperation

from ... import pii
from ...extraction.parsers import extract

DETECTABLE = ("iban", "account", "phone", "email", "ahv")  # name and address need a model (SC-11.9)
_TOKEN = re.compile(r"[^\s|]+")
_WATERMARK = {"synthetic", "s", "y", "n", "t", "h", "e", "i", "c", "sy", "ic", "tic", "syn", "the"}


def _tokens(text: str) -> list[str]:
    out = []
    for t in _TOKEN.findall(text):
        t = t.strip(".,:;()").lower()
        if t and t not in _WATERMARK:
            out.append(t)
    return out


def _recall(gold: list[str], got: list[str]) -> tuple[int, int]:
    g, r = Counter(gold), Counter(got)
    return sum(min(n, r[t]) for t, n in g.items()), sum(g.values())


def page_text(pages: list) -> dict[int, str]:
    return {p.number: "\n".join(ln.text for ln in p.lines) for p in pages}


def _dec(v: object) -> Decimal | None:
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def _accepted(f) -> bool:
    return f.review is None or f.review.status == "accepted"


def _norm(s: str) -> str:
    return re.sub(r"[\s.\-/]", "", s).upper()


def score_pii(texts: dict[int, str], gold: dict) -> dict:
    out = {
        "gold": 0,
        "found": 0,
        "misread": 0,
        "by_kind": {},
        "names_addresses": 0,
        "damage": 0,
        "figures": 0,
    }
    for page, text in texts.items():
        spans = pii.detect(text)
        covered = {_norm(text[s.start : s.end]) for s in spans}
        flat = _norm(text)
        for g in (x for x in gold["pii"] if x["page"] == page):
            if g["kind"] not in DETECTABLE:
                out["names_addresses"] += 1
                continue
            k = out["by_kind"].setdefault(g["kind"], [0, 0])
            out["gold"] += 1
            k[1] += 1
            target = _norm(g["text"])
            if any(target in c or (c and c in target and len(c) >= 0.8 * len(target)) for c in covered):
                out["found"] += 1
                k[0] += 1
            elif target not in flat:
                out["misread"] += 1  # the reader garbled it: nothing a text rule could catch
        masked = pii.mask(text, spans)
        figures = [p["isin"] for p in gold["positions"] if p["page"] == page]
        figures += [f["value"] for f in gold["fees"] if f["page"] == page]
        for fig in figures:
            raw = re.sub(r"[^0-9A-Z]", "", fig.upper())
            before = raw in re.sub(r"[^0-9A-Z]", "", text.upper())
            after = raw in re.sub(r"[^0-9A-Z]", "", masked.upper())
            out["figures"] += before
            out["damage"] += before and not after
    return out


def score_doc(name: str, data: bytes, gold: dict, digital_text: dict[int, str]) -> dict:
    t0 = time.perf_counter()
    res, pages = extract(name, data)
    secs = time.perf_counter() - t0
    texts = page_text(pages)
    got_all = _tokens(" ".join(texts.values()))
    gold_all = _tokens(" ".join(digital_text.values()))
    w_ok, w_n = _recall(gold_all, got_all)
    f_ok, f_n = _recall(
        [t for t in gold_all if any(c.isdigit() for c in t)],
        [t for t in got_all if any(c.isdigit() for c in t)],
    )

    pos = [f for f in res.facts if f.kind == "position" and f.isin]
    by_isin = {p["isin"]: Decimal(p["value"]) for p in gold["positions"]}
    found = wrong = wrong_acc = 0
    seen = set()
    for f in pos:
        v = _dec(f.value)
        if f.isin in by_isin and v == by_isin[f.isin] and f.isin not in seen:
            found += 1
            seen.add(f.isin)
        elif f.isin not in seen:
            wrong += 1
            wrong_acc += _accepted(f)
    total_facts = [f for f in res.facts if f.kind == "doc_total"]
    total_ok = any(_dec(f.value) == Decimal(gold["total"]) for f in total_facts)

    fee_page = gold["fees"][0]["page"] if gold["fees"] else None
    fee_facts = [  # mentions (a rate in a heading, "VAT 8.1%") are scored apart, as in SC-9.5
        f
        for f in res.facts
        if f.fee_code and f.kind != "fee_mention" and f.evidence and f.evidence.page == fee_page
    ]
    gold_fee_vals = {Decimal(x["value"]) for x in gold["fees"]}
    fee_total = sum(gold_fee_vals, Decimal(0))
    fee_found = fee_code_ok = 0
    for g in gold["fees"]:
        hits = [f for f in fee_facts if _dec(f.value) == Decimal(g["value"])]
        fee_found += bool(hits)
        fee_code_ok += any(f.fee_code == g["code"] for f in hits)
    fee_wrong = [f for f in fee_facts if _dec(f.value) not in gold_fee_vals and _dec(f.value) != fee_total]
    wrong += len(fee_wrong)
    wrong_acc += sum(_accepted(f) for f in fee_wrong)
    return {
        "file": name,
        "doc_type": res.profile.doc_type.value,
        "engines": res.profile.engines,
        "seconds": round(secs, 2),
        "pages": len(pages),
        "words": [w_ok, w_n],
        "figures": [f_ok, f_n],
        "holdings": [found, len(by_isin)],
        "total_ok": total_ok,
        "fees": [fee_found, len(gold["fees"])],
        "fee_codes": [fee_code_ok, len(gold["fees"])],
        "wrong": wrong,
        "wrong_accepted": wrong_acc,
        "facts_read": len(pos) + len(fee_facts),
        "pii": score_pii(texts, gold),
    }


def score_handwritten(name: str, data: bytes, figures: list[str]) -> dict:
    t0 = time.perf_counter()
    res, pages = extract(name, data)
    text = " ".join(page_text(pages).values())
    digits = Counter(re.sub(r"\D", "", t) for t in _TOKEN.findall(text) if any(c.isdigit() for c in t))
    want = Counter(re.sub(r"\D", "", f) for f in figures)
    ok = sum(min(n, digits[k]) for k, n in want.items())
    return {
        "file": name,
        "seconds": round(time.perf_counter() - t0, 2),
        "figures": [ok, sum(want.values())],
        "app_values": sum(1 for f in res.facts if f.value is not None),
        "warnings": res.profile.warnings,
    }
