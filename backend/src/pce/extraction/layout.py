"""Page layout reading: born-digital text with geometry, OCR fallback for scans.

Output is a list of ``Line`` objects per page, each made of ``Cell`` spans with a
bounding box in PDF points, origin top-left (the coordinate system pdf.js uses
after viewport scaling). Rotated text (watermarks, side notes) is ignored.

Scanned pages are OCR'd on a small thread pool (SC-5.11): Tesseract runs as a subprocess, so threads
overlap without the GIL; pdfium rendering is not thread safe and is serialised by a lock.

When the optional ``rapidocr`` extra is installed, scans are read with RapidOCR (PP-OCR models as ONNX,
bundled in the wheel, CPU, no network) instead of Tesseract: on the ocrbench scan pages it found 70% of the
printed fees against 53%, with fewer misreads (SC-5.22, ADR 0003).
"""

from __future__ import annotations

import importlib.util
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber
import pypdfium2

OCR_DPI = 300
MIN_TEXT_CHARS = 25  # below this a page is treated as scanned
MAX_OCR_WORKERS = 4  # each worker holds one ~26 MB page image plus a Tesseract process
CGROUP_CPU_MAX = Path("/sys/fs/cgroup/cpu.max")
_PDFIUM_LOCK = threading.Lock()
# Tesseract processes running at once in this process, or across document workers (SC-5.20): a worker
# process gets one shared semaphore from documents.py, so OCR never runs more processes than cores.
_OCR_SLOTS: threading.BoundedSemaphore | None = None
# Page readers for scans; anything that asks "was this page OCR'd?" checks membership here.
OCR_ENGINES = ("tesseract-ocr", "rapidocr")
_RAPID = None
_RAPID_LOCK = threading.Lock()


def use_ocr_slots(slots: threading.BoundedSemaphore) -> None:
    global _OCR_SLOTS
    _OCR_SLOTS = slots


def ocr_slot() -> threading.BoundedSemaphore:
    """Hold one while a page image is rendered for and read by Tesseract."""
    global _OCR_SLOTS
    if _OCR_SLOTS is None:
        _OCR_SLOTS = threading.BoundedSemaphore(ocr_workers())
    return _OCR_SLOTS


def ocr_workers() -> int:
    """Pages OCR'd at once: ``PCE_OCR_WORKERS``, else the CPU quota this process really has.

    ``os.cpu_count()`` reports the host's cores; a container's quota (Render free: 0.15 CPU) is in
    cgroup ``cpu.max``. Oversubscribing a fractional CPU only adds memory, so the floor is used."""
    env = os.environ.get("PCE_OCR_WORKERS")
    if env:
        return max(1, int(env))
    cpus = len(os.sched_getaffinity(0))
    try:
        quota, period = CGROUP_CPU_MAX.read_text().split()
        if quota != "max":
            cpus = min(cpus, int(quota) // int(period))
    except (OSError, ValueError):
        pass
    return max(1, min(cpus, MAX_OCR_WORKERS))


@dataclass
class Cell:
    text: str
    bbox: tuple[float, float, float, float]
    # word boxes inside the cell (start offset in text, box), when the reader gives them: lets a number
    # inside a longer cell get its own exact box instead of an estimate
    words: list[tuple[int, tuple[float, float, float, float]]] = field(default_factory=list)


@dataclass
class Line:
    page: int  # 1-based
    cells: list[Cell]
    engine: str  # "pdfplumber-text" or one of OCR_ENGINES
    confidence: float = 1.0

    @property
    def text(self) -> str:
        return " ".join(c.text for c in self.cells)

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        xs0, ys0, xs1, ys1 = zip(*(c.bbox for c in self.cells), strict=True)
        return (min(xs0), min(ys0), max(xs1), max(ys1))

    def bbox_of(self, cells: list[Cell]) -> tuple[float, float, float, float]:
        xs0, ys0, xs1, ys1 = zip(*(c.bbox for c in cells), strict=True)
        return (min(xs0), min(ys0), max(xs1), max(ys1))


@dataclass
class PageInfo:
    number: int
    width: float
    height: float
    engine: str
    lines: list[Line] = field(default_factory=list)


def _digital_lines(page: pdfplumber.page.Page, number: int) -> list[Line]:
    def horizontal(o: dict) -> bool:
        if o.get("object_type") != "char":
            return True
        a, b, c, _d, *_ = o.get("matrix", (1, 0, 0, 1, 0, 0))
        return abs(b) < 1e-3 and abs(c) < 1e-3 and a > 0  # drop rotated text such as watermarks

    upright = page.filter(horizontal)
    words = upright.extract_words(x_tolerance=1.5, y_tolerance=2, keep_blank_chars=False, use_text_flow=False)
    # merge words into cells: a horizontal gap wider than ~1.5 spaces starts a new column cell
    words.sort(key=lambda w: (round((w["top"] + w["bottom"]) / 2), w["x0"]))
    cells: list[Cell] = []
    for w in words:
        bb = (w["x0"], w["top"], w["x1"], w["bottom"])
        if cells:
            prev = cells[-1]
            same_row = abs((prev.bbox[1] + prev.bbox[3]) / 2 - (bb[1] + bb[3]) / 2) <= 2
            if same_row and 0 <= bb[0] - prev.bbox[2] < 6:
                cells[-1] = Cell(
                    prev.text + " " + w["text"],
                    (prev.bbox[0], min(prev.bbox[1], bb[1]), bb[2], max(prev.bbox[3], bb[3])),
                    [*prev.words, (len(prev.text) + 1, bb)],
                )
                continue
        cells.append(Cell(w["text"], bb, [(0, bb)]))
    cells = [
        Cell(
            c.text,
            tuple(round(v, 2) for v in c.bbox),
            [(o, tuple(round(v, 2) for v in b)) for o, b in c.words],
        )
        for c in cells
    ]
    return _group(cells, number, "pdfplumber-text", 1.0)


def _group(cells: list[Cell], number: int, engine: str, conf: float, tol: float = 3.0) -> list[Line]:
    cells.sort(key=lambda c: ((c.bbox[1] + c.bbox[3]) / 2, c.bbox[0]))
    lines: list[list[Cell]] = []
    for c in cells:
        yc = (c.bbox[1] + c.bbox[3]) / 2
        if lines:
            last = lines[-1]
            lyc = sum((x.bbox[1] + x.bbox[3]) / 2 for x in last) / len(last)
            if abs(yc - lyc) <= tol:
                last.append(c)
                continue
        lines.append([c])
    return [Line(number, sorted(ln, key=lambda c: c.bbox[0]), engine, conf) for ln in lines]


def ocr_engine() -> str:
    """The reader used for scanned pages on this machine."""
    return "rapidocr" if importlib.util.find_spec("rapidocr") else "tesseract-ocr"


def _rapid_lines(pdf: pypdfium2.PdfDocument, index: int, number: int) -> list[Line]:
    import numpy as np
    from rapidocr import RapidOCR

    global _RAPID
    with ocr_slot():
        with _PDFIUM_LOCK:
            img = np.array(pdf[index].render(scale=OCR_DPI / 72).to_pil().convert("RGB"))
        # One engine per process (loading the models takes about a second); onnxruntime already uses
        # every core per call, so calls are serialised rather than run side by side.
        with _RAPID_LOCK:
            if _RAPID is None:
                _RAPID = RapidOCR(params={"Global.log_level": "critical"})
            res = _RAPID(img)
        del img
    scale = 72.0 / OCR_DPI
    cells, confs = [], []
    boxes = [] if res.boxes is None else res.boxes  # None on a blank page
    for box, text, score in zip(boxes, res.txts or (), res.scores or (), strict=True):
        if text.strip():
            xs, ys = [p[0] for p in box], [p[1] for p in box]
            bbox = tuple(round(float(v) * scale, 2) for v in (min(xs), min(ys), max(xs), max(ys)))
            cells.append(Cell(text.strip(), bbox))
            confs.append(float(score))
    # RapidOCR boxes one text run each and does not group them into lines; group by vertical centre.
    return _group(cells, number, "rapidocr", round(sum(confs) / len(confs), 3) if confs else 0.0, tol=4.0)


def _ocr_lines(pdf: pypdfium2.PdfDocument, index: int, number: int, lang: str) -> list[Line]:
    if ocr_engine() == "rapidocr":
        return _rapid_lines(pdf, index, number)
    import pytesseract

    with ocr_slot():
        with _PDFIUM_LOCK:
            img = pdf[index].render(scale=OCR_DPI / 72).to_pil()
        data = pytesseract.image_to_data(
            img, lang=lang, output_type=pytesseract.Output.DICT, config="--psm 6"
        )
        del img
    scale = 72.0 / OCR_DPI
    groups: dict[tuple[int, int, int], list[tuple[str, tuple[float, float, float, float], float]]] = {}
    for i, word in enumerate(data["text"]):
        w = (word or "").strip()
        conf = float(data["conf"][i])
        if not w or conf < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        x, y, wd, ht = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        groups.setdefault(key, []).append(
            (w, (x * scale, y * scale, (x + wd) * scale, (y + ht) * scale), conf)
        )
    lines = []
    for words in groups.values():
        words.sort(key=lambda t: t[1][0])
        # merge words into cells; a gap wider than ~2 spaces starts a new cell (column)
        cells: list[Cell] = []
        confs = []
        for w, bb, cf in words:
            confs.append(cf)
            if cells and bb[0] - cells[-1].bbox[2] < 9:
                prev = cells[-1]
                cells[-1] = Cell(
                    prev.text + " " + w,
                    (prev.bbox[0], min(prev.bbox[1], bb[1]), bb[2], max(prev.bbox[3], bb[3])),
                )
            else:
                cells.append(Cell(w, bb))
        cells = [Cell(c.text, tuple(round(v, 2) for v in c.bbox)) for c in cells]
        lines.append(Line(number, cells, "tesseract-ocr", round(sum(confs) / len(confs) / 100, 3)))
    lines.sort(key=lambda ln: (ln.bbox[1], ln.bbox[0]))
    return lines


def read_pdf(path_or_bytes, ocr_lang: str = "eng+ita+deu+fra", max_pages: int = 200) -> list[PageInfo]:
    import io

    data = path_or_bytes if isinstance(path_or_bytes, bytes) else open(path_or_bytes, "rb").read()
    try:
        plumber = pdfplumber.open(io.BytesIO(data))
    except Exception as exc:  # pdfminer raises several types for encrypted/corrupt files
        raise ValueError(f"unreadable or encrypted PDF: {type(exc).__name__}") from exc
    with plumber:
        if len(plumber.pages) > max_pages:
            raise ValueError(f"PDF has {len(plumber.pages)} pages; limit is {max_pages}")
        routes = [len((page.extract_text() or "").strip()) >= MIN_TEXT_CHARS for page in plumber.pages]
        pdfium = None if all(routes) else pypdfium2.PdfDocument(data)
        workers = min(ocr_workers(), routes.count(False)) or 1
        with ThreadPoolExecutor(workers) as pool:
            ocr = {
                i: pool.submit(_ocr_lines, pdfium, i, i + 1, ocr_lang)
                for i, digital in enumerate(routes)
                if not digital
            }
            pages = []
            for i, page in enumerate(plumber.pages):
                if routes[i]:
                    lines, engine = _digital_lines(page, i + 1), "pdfplumber-text"
                else:
                    lines = ocr[i].result()
                    engine = lines[0].engine if lines else ocr_engine()
                pages.append(
                    PageInfo(i + 1, round(float(page.width), 2), round(float(page.height), 2), engine, lines)
                )
        if pdfium is not None:
            pdfium.close()
    return pages
