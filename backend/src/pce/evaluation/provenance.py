"""Provenance check: does the place a fact cites really show its value?

This is what the analyst relies on when they click a number and land on the page: the box (PDF) or
cell (spreadsheet) must hold that number. Checked independently of the extractor, from the file itself:
PDF text inside the cited box via pdfplumber, spreadsheet cell via openpyxl. Pages without a text layer
(scans) cannot be checked this way and are reported as ``unverifiable``, never as passed.
"""

from __future__ import annotations

import io
from collections import Counter
from decimal import Decimal

import openpyxl
import pdfplumber

from .metrics import fact_value, numbers

PAD = 2.0  # points, horizontal only: vertical padding pulls in the next line's glyphs on tight layouts


def _horizontal(o: dict) -> bool:
    if o.get("object_type") != "char":
        return True
    a, b, c, *_ = o.get("matrix", (1, 0, 0, 1, 0, 0))
    return abs(b) < 1e-3 and abs(c) < 1e-3 and a > 0


def _pdf_texts(data: bytes, wanted: set[tuple[int, tuple[float, ...]]]) -> dict:
    out: dict = {}
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page_no, box in wanted:
            if not 1 <= page_no <= len(pdf.pages):
                out[(page_no, box)] = None
                continue
            # rotated text (watermarks) is not content: the extractor ignores it, so must the check
            page = pdf.pages[page_no - 1].filter(_horizontal)
            if not page.chars:
                out[(page_no, box)] = None  # no text layer: unverifiable
                continue
            x0, y0, x1, y1 = box
            crop = (max(0, x0 - PAD), max(0, y0), min(page.width, x1 + PAD), min(page.height, y1))
            out[(page_no, box)] = page.crop(crop).extract_text() or ""
    return out


def _cell_value(data: bytes, sheet: str, cell: str) -> object:
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=False)
    return wb[sheet][cell].value if sheet in wb.sheetnames else None


def _holds(text: str, value: Decimal) -> bool:
    return any(n == value or abs(n) == abs(value) for n in numbers(text))


def check(filename: str, data: bytes, facts: list[dict]) -> Counter:
    """Count facts by provenance status: verified | mismatch | no_evidence | unverifiable.

    Facts without a value (unknown) have nothing to locate and are skipped.
    """
    res: Counter = Counter()
    valued = [(f, fact_value(f.get("value"))) for f in facts if f.get("value") not in (None, "")]
    if filename.lower().endswith((".xlsx", ".xlsm")):
        for f, v in valued:
            ev = f.get("evidence") or {}
            if not (ev.get("sheet") and ev.get("cell")):
                res["no_evidence"] += 1
                continue
            got = _cell_value(data, ev["sheet"], ev["cell"])
            res["verified" if v is not None and _holds(str(got), v) else "mismatch"] += 1
        return res
    wanted = {}
    for i, (f, _v) in enumerate(valued):
        ev = f.get("evidence") or {}
        if ev.get("page") and ev.get("bbox"):
            wanted[i] = (int(ev["page"]), tuple(float(x) for x in ev["bbox"]))
    texts = _pdf_texts(data, set(wanted.values())) if wanted else {}
    for i, (_f, v) in enumerate(valued):
        if i not in wanted:
            res["no_evidence"] += 1
        elif texts[wanted[i]] is None:
            res["unverifiable"] += 1
        else:
            res["verified" if v is not None and _holds(texts[wanted[i]], v) else "mismatch"] += 1
    return res
