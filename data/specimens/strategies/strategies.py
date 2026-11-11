"""The extraction strategies compared in SC-5.8, one function per strategy.

Each function takes a benchmark page (a row of ocrbench/pages.json) and returns
``(predictions, extra_seconds)`` or ``None`` when it cannot run on that page (no stored output).
A prediction is a dict: label, snippet, value (Decimal string), bbox, fee_code, needs_review.

Readers:   text   = production reader ``pce.extraction.layout.read_pdf`` (pdfplumber text layer,
                    Tesseract 300 dpi on pages without one), run live
           <engine> = stored output of an SC-5.6 engine (rapidocr, paddleocr_vl, ...), reused
Linkers:   rules  = production per-type parsers (``parsers.extract`` on the whole document)
           line   = every rate/amount on a line with a fee word (the benchmark's simple rule)
           finder = layout-aware finder (``pce.extraction.finder``): row label, label above,
                    column header, section heading
"""

from __future__ import annotations

import json
import re
import time
from functools import cache
from pathlib import Path

from pce.extraction import finder, verify
from pce.extraction.layout import Cell, Line, PageInfo, _group, read_pdf
from pce.extraction.numbers import find_numbers
from pce.extraction.parsers import extract

ROOT = Path(__file__).resolve().parents[3]
PAGES = ROOT / "var" / "ocrbench" / "pages"
STORED = ROOT / "var" / "ocrbench" / "out"
SPECIMENS = ROOT / "var" / "specimens"
FEE_KINDS = {"fee_observed", "fee_rule", "product_cost", "cash_debit", "fee_mention"}


def _pred(f) -> dict:
    review = f.review
    return {
        "label": f.label,
        "snippet": f.evidence.snippet,
        "value": f.value,
        "bbox": f.evidence.bbox,
        "fee_code": None,  # gold has no fee codes: label words decide
        "needs_review": bool(review and review.status == "needs_review"),
        "reasons": review.reasons if review else [],
        "engine": f.evidence.engine,
    }


# ---------- readers ----------


@cache
def text_pages(pid: str) -> tuple[list[PageInfo], float]:
    t0 = time.perf_counter()
    pages = read_pdf(str(PAGES / f"{pid}.pdf"))
    return pages, time.perf_counter() - t0


@cache
def stored(engine: str, pid: str) -> dict | None:
    f = STORED / engine / f"{pid}.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text(encoding="utf-8"))
    return None if d.get("error") else d


def stored_pages(engine: str, p: dict) -> tuple[list[PageInfo], float] | None:
    """An engine's stored line boxes (pixels at 144 dpi) as production ``PageInfo`` lines (PDF points)."""
    d = stored(engine, p["id"])
    if d is None or not d.get("words"):
        return None
    cells = [Cell(w["t"], tuple(round(v / 2, 2) for v in w["b"])) for w in d["words"] if w.get("t", "").strip()]
    conf = sum(w.get("c", 1.0) for w in d["words"]) / max(len(d["words"]), 1)
    lines = _group(cells, 1, engine, round(conf, 3), tol=4.0)
    return [PageInfo(1, p["width"] / 2, p["height"] / 2, engine, lines)], d.get("seconds", 0.0)


def regions(engine: str, pid: str) -> tuple[dict, float]:
    d = stored(engine, pid)
    if d is None:
        return {}, 0.0
    return {1: [(r["label"], tuple(v / 2 for v in r["b"])) for r in d.get("regions", [])]}, d.get("seconds", 0.0)


# ---------- strategies ----------


@cache
def _rules_doc(file: str) -> tuple[tuple, float, int]:
    t0 = time.perf_counter()
    try:
        res, pages = extract(file, (SPECIMENS / file).read_bytes())
    except ValueError:  # the app refuses it too (e.g. over 200 pages): nothing extracted
        return (), time.perf_counter() - t0, 1
    return tuple(res.facts), time.perf_counter() - t0, max(len(pages), 1)


def production(p: dict):
    """``parsers.extract`` as the app runs it. Originals: whole document (it classifies on all pages),
    facts on the page; simulated scans: the single image page."""
    if p["variant"] == "scan-sim":
        t0 = time.perf_counter()
        res, _ = extract(f"{p['id']}.pdf", (PAGES / f"{p['id']}.pdf").read_bytes())
        facts, secs, n, page = res.facts, time.perf_counter() - t0, 1, 1
    else:
        facts, secs, n = _rules_doc(p["file"])
        page = p["page"]
    keep = [f for f in facts if f.kind in FEE_KINDS and f.value is not None and f.evidence.page == page]
    return keep, secs / n


def rules(p: dict):
    """The type parsers alone, as before SC-5.8 (finder facts and reviews ignored)."""
    keep, secs = production(p)
    return [{**_pred(f), "needs_review": False} for f in keep if f.kind != "fee_mention"], secs


def production_extract(p: dict):
    """What the app now does: type parser + finder, cross-checked and verified (parsers.extract)."""
    keep, secs = production(p)
    return [_pred(f) for f in keep], secs


def _line_rule(pages: list[PageInfo]) -> list[dict]:
    out = []
    for pg in pages:
        for ln in pg.lines:
            if not finder.FEE_WORDS.search(ln.text):
                continue
            for c in ln.cells:
                for n in find_numbers(c.text):
                    if finder._accepted(n, c.text[: n.start]):
                        out.append({"label": ln.text, "snippet": ln.text, "value": str(n.value),
                                    "bbox": list(finder._num_bbox(c, n)), "needs_review": False})
    return out


def line_text(p: dict):
    pages, secs = text_pages(p["id"])
    return _line_rule(pages), secs


def finder_text(p: dict):
    pages, secs = text_pages(p["id"])
    return [_pred(f) for f in finder.find_fees(pages)], secs


def _finder_layout(layout: str):
    def run(p: dict):
        pages, secs = text_pages(p["id"])
        reg, rsecs = regions(layout, p["id"])
        if not reg:
            return None
        return [_pred(f) for f in finder.find_fees(pages, reg)], secs + rsecs

    return run


def _finder_stored(engine: str):
    def run(p: dict):
        got = stored_pages(engine, p)
        if got is None:
            return None
        pages, secs = got
        return [_pred(f) for f in finder.find_fees(pages)], secs

    return run


def _verified(second: str | None, layout: str | None = None):
    """Finder on the production reader + verification: a second reader re-reads each value at its box,
    and cross-checks flag anything doubtful as needs_review instead of dropping it."""

    def run(p: dict):
        pages, secs = text_pages(p["id"])
        reg, rsecs = regions(layout, p["id"]) if layout else ({}, 0.0)
        facts = finder.find_fees(pages, reg or None)
        other, osecs = (None, 0.0)
        if second:
            got = stored_pages(second, p)
            if got is not None:
                other, osecs = got
        verify.verify(facts, pages, other)
        return [_pred(f) for f in facts], secs + rsecs + osecs

    return run


def verified_crops(p: dict):
    """Production path: finder on the production reader, verified by Tesseract on the value crops."""
    pages, secs = text_pages(p["id"])
    facts = finder.find_fees(pages)
    t0 = time.perf_counter()
    other = verify.second_reading((PAGES / f"{p['id']}.pdf").read_bytes(), facts)
    verify.verify(facts, pages, other)
    return [_pred(f) for f in facts], secs + time.perf_counter() - t0


def _verified_swap():
    """Scans: read with RapidOCR, verify against the production reader (Tesseract on scans)."""

    def run(p: dict):
        got = stored_pages("rapidocr", p)
        if got is None:
            return None
        pages, secs = got
        other, osecs = text_pages(p["id"])
        facts = finder.find_fees(pages)
        verify.verify(facts, pages, other)
        return [_pred(f) for f in facts], secs + osecs

    return run


def vlm_anchored(engine: str):
    """A VLM's table rows give the label association; each value is anchored to a box from the
    production reader (no box, no fact). Pages without stored VLM output are left out."""

    def run(p: dict):
        d = stored(engine, p["id"])
        if d is None:
            return None
        pages, secs = text_pages(p["id"])
        if not any(pg.lines for pg in pages):
            got = stored_pages("rapidocr", p)
            pages, secs = got if got else (pages, secs)
        cells = [c for pg in pages for ln in pg.lines for c in ln.cells]
        preds = []
        for t in d.get("tables", []):
            rows = t.get("rows") or []
            header = rows[0] if rows else []
            for row in rows:
                label = next((c for c in row if re.search(r"[^\W\d_]{3,}", c or "")), "")
                for ci, cell in enumerate(row):
                    for n in find_numbers(cell or ""):
                        if not finder._accepted(n, (cell or "")[: n.start]):
                            continue
                        ctx = f"{label} {header[ci] if ci < len(header) else ''}"
                        if not finder.FEE_WORDS.search(ctx + " " + " ".join(header)) or finder.NOT_FEE.search(ctx):
                            continue
                        box = _anchor(n.text, cells)
                        preds.append({"label": ctx.strip(), "snippet": " | ".join(c or "" for c in row)[:300],
                                      "value": str(n.value), "bbox": box,
                                      "needs_review": box is None})
        return preds, secs + d.get("seconds", 0.0)

    return run


def _anchor(printed: str, cells: list[Cell]) -> list[float] | None:
    want = find_numbers(printed)
    if not want:
        return None
    for c in cells:
        for n in find_numbers(c.text):
            if n.value == want[0].value and n.unit == want[0].unit:
                return list(finder._num_bbox(c, n))
    return None


STRATEGIES = {
    "rules (parsers before SC-5.8)": rules,
    "production extract() after SC-5.8": production_extract,
    "line rule @text": line_text,
    "finder @text": finder_text,
    "finder @rapidocr": _finder_stored("rapidocr"),
    "finder @tesseract-stored": _finder_stored("tesseract"),
    "finder @text + heron regions": _finder_layout("heron"),
    "finder @text + ppdoclayout3 regions": _finder_layout("ppdoclayout3"),
    "finder @text + verify(rapidocr)": _verified("rapidocr"),
    "finder @text + verify(tesseract)": _verified("tesseract"),
    "finder @text + ppdoclayout3 + verify(rapidocr)": _verified("rapidocr", "ppdoclayout3"),
    "finder @rapidocr + verify(text)": _verified_swap(),
    "finder @text + verify(tesseract crops)": verified_crops,
    "vlm-anchored paddleocr_vl": vlm_anchored("paddleocr_vl"),
    "vlm-anchored docling": vlm_anchored("docling"),
}
