"""Page layout reading: born-digital text with geometry, OCR fallback for scans.

Output is a list of ``Line`` objects per page, each made of ``Cell`` spans with a
bounding box in PDF points, origin top-left (the coordinate system pdf.js uses
after viewport scaling). Rotated text (watermarks, side notes) is ignored.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pdfplumber
import pypdfium2

OCR_DPI = 300
MIN_TEXT_CHARS = 25  # below this a page is treated as scanned


@dataclass
class Cell:
    text: str
    bbox: tuple[float, float, float, float]


@dataclass
class Line:
    page: int  # 1-based
    cells: list[Cell]
    engine: str  # "pdfplumber-text" | "tesseract-ocr"
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
                )
                continue
        cells.append(Cell(w["text"], bb))
    cells = [Cell(c.text, tuple(round(v, 2) for v in c.bbox)) for c in cells]
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


def _ocr_lines(pdf: pypdfium2.PdfDocument, index: int, number: int, lang: str) -> list[Line]:
    import pytesseract

    img = pdf[index].render(scale=OCR_DPI / 72).to_pil()
    data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT, config="--psm 6")
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
        pdfium = None
        pages = []
        for i, page in enumerate(plumber.pages):
            text = (page.extract_text() or "").strip()
            if len(text) >= MIN_TEXT_CHARS:
                lines, engine = _digital_lines(page, i + 1), "pdfplumber-text"
            else:
                pdfium = pdfium or pypdfium2.PdfDocument(data)
                lines, engine = _ocr_lines(pdfium, i, i + 1, ocr_lang), "tesseract-ocr"
            pages.append(
                PageInfo(i + 1, round(float(page.width), 2), round(float(page.height), 2), engine, lines)
            )
        if pdfium is not None:
            pdfium.close()
    return pages
