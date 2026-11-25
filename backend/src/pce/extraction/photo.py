"""Phone photos of paper documents to a clean PDF the OCR path can read (SC-9.8).

A camera picture is not a scan: the page is tilted in perspective, lies on a darker table, is lit
unevenly and is stored sideways, with or without an EXIF rotation flag. Each photo is turned upright, the
page's four corners are found (the page is the large bright region), the page is warped flat to A4
proportions, uneven lighting is divided out against a blurred copy of itself, and the result becomes
one PDF page.

Pillow and numpy only (no OpenCV). Never fails on a hard photo: if no page outline is found, the
whole picture is kept and only the lighting is corrected, so OCR still sees every pixel.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from . import layout

MAX_SIDE = 2600  # pixels on the long side after cleanup: ~300 dpi on A4, enough for OCR
A4_RATIO = 297 / 210
MIN_PAGE_SHARE = 0.25  # a page outline covering less of the picture is not trusted


def _otsu(gray: np.ndarray) -> int:
    hist = np.bincount(gray.ravel(), minlength=256).astype(float)
    total = gray.size
    cum, cum_mean = np.cumsum(hist), np.cumsum(hist * np.arange(256))
    w0 = cum / total
    w1 = 1 - w0
    with np.errstate(divide="ignore", invalid="ignore"):
        m0 = cum_mean / cum
        m1 = (cum_mean[-1] - cum_mean) / (total - cum)
        between = w0 * w1 * (m0 - m1) ** 2
    return int(np.nanargmax(between))


def page_corners(gray: Image.Image) -> list[tuple[float, float]] | None:
    """Top-left, top-right, bottom-right, bottom-left of the bright page, or None when unclear."""
    small = gray.resize((max(1, gray.width // 4), max(1, gray.height // 4))).filter(
        ImageFilter.GaussianBlur(3)
    )
    a = np.asarray(small)
    if a.min() == a.max():
        return None  # one flat tone: no page edge to find
    mask = a > _otsu(a)
    if mask.mean() < MIN_PAGE_SHARE or mask.mean() > 0.97:
        return None
    ys, xs = np.nonzero(mask)
    s, d = xs + ys, xs - ys
    pts = [(xs[s.argmin()], ys[s.argmin()]), (xs[d.argmax()], ys[d.argmax()]),
           (xs[s.argmax()], ys[s.argmax()]), (xs[d.argmin()], ys[d.argmin()])]  # fmt: skip
    quad = np.array(pts, dtype=float)
    x, y = quad[:, 0], quad[:, 1]
    area = 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
    if area < MIN_PAGE_SHARE * a.size:
        return None
    return [(float(px) * 4, float(py) * 4) for px, py in pts]


def perspective_coeffs(dst: list[tuple[float, float]], src: list[tuple[float, float]]) -> list[float]:
    """Coefficients Pillow's PERSPECTIVE transform needs: output pixel (dst) -> input pixel (src)."""
    rows = []
    for (x, y), (u, v) in zip(dst, src, strict=True):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    b = np.array([c for pt in src for c in pt], dtype=float)
    return list(np.linalg.solve(np.array(rows, dtype=float), b))


def _even_light(gray: Image.Image) -> Image.Image:
    """Divide by a heavily blurred copy: shadows and vignetting go, ink stays dark."""
    small = gray.resize((max(1, gray.width // 8), max(1, gray.height // 8)))
    bg = small.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(8)).resize(gray.size)
    a = np.asarray(gray, dtype=float)
    b = np.maximum(np.asarray(bg, dtype=float), 1.0)
    out = np.clip(a / b * 255.0, 0, 255).astype(np.uint8)
    return ImageOps.autocontrast(Image.fromarray(out), cutoff=1)


def clean_photo(data: bytes) -> Image.Image:
    """One photo (JPEG/PNG bytes) to an upright, flattened, evenly lit grayscale page."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
    gray = img.convert("L")
    corners = page_corners(gray)
    if corners:
        tl, tr, br, bl = corners
        width = max(np.hypot(tr[0] - tl[0], tr[1] - tl[1]), np.hypot(br[0] - bl[0], br[1] - bl[1]))
        portrait = width < max(np.hypot(bl[0] - tl[0], bl[1] - tl[1]), np.hypot(br[0] - tr[0], br[1] - tr[1]))
        w = (
            int(min(MAX_SIDE / A4_RATIO, max(width, 800)))
            if portrait
            else int(min(MAX_SIDE, max(width, 800)))
        )
        h = int(w * A4_RATIO) if portrait else int(w / A4_RATIO)
        coeffs = perspective_coeffs([(0, 0), (w, 0), (w, h), (0, h)], corners)
        gray = gray.transform((w, h), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC)
    elif max(gray.size) > MAX_SIDE:
        gray.thumbnail((MAX_SIDE, MAX_SIDE))
    return _not_upside_down(_text_horizontal(_even_light(gray)))


def _text_horizontal(page: Image.Image) -> Image.Image:
    """Turn a page whose text runs top to bottom (photo taken sideways, no EXIF flag) by 90 degrees.

    Lines of text make the ink profile across rows swing between line and gap; across columns it is
    flat. When the column profile swings more, the text is vertical. With RapidOCR the text boxes decide
    instead: most of them taller than wide means vertical text. A page that ends up upside down is
    righted next by ``_not_upside_down`` (SC-9.12).
    """
    small = page.copy()
    small.thumbnail((800, 800))
    a = np.asarray(small, dtype=float)
    if a.min() == a.max():  # one flat tone: nothing to tell
        return page
    ink = a < _otsu(a.astype(np.uint8))
    if ink.mean() < 0.005:
        return page
    if layout.ocr_engine() == "rapidocr":  # text boxes say it best; ink misjudges a near-empty page
        boxes = layout.rapid(np.asarray(small.convert("RGB")), use_cls=False, use_rec=False).boxes
        if boxes is not None and len(boxes) >= 3:  # a clear majority, or the ink decides
            b = np.asarray(boxes)
            wide = (np.hypot(*(b[:, 1] - b[:, 0]).T) > np.hypot(*(b[:, 3] - b[:, 0]).T)).mean()
            if wide >= 0.7 or wide <= 0.3:
                return page.rotate(90, expand=True) if wide <= 0.3 else page
    rows, cols = ink.mean(axis=1), ink.mean(axis=0)
    return page.rotate(90, expand=True) if cols.std() > 1.3 * rows.std() else page


def _not_upside_down(page: Image.Image) -> Image.Image:
    """Turn an upside-down page by 180 degrees.

    The OCR reader rights each upside-down line, but leaves the lines in reverse order with the amount
    before its label, which breaks every table row. Read a small copy both ways without that correction;
    upside-down text scores clearly lower (SC-9.12). Needs RapidOCR; without it the page is kept.
    """
    if layout.ocr_engine() != "rapidocr":
        return page
    small = page.copy()
    small.thumbnail((1000, 1000))
    a = np.asarray(small.convert("RGB"))

    def confidence(img: np.ndarray) -> float:
        scores = layout.rapid(np.ascontiguousarray(img), use_cls=False).scores or ()
        return sum(scores) / len(scores) if scores else 0.0

    return page.rotate(180) if confidence(a[::-1, ::-1]) > confidence(a) + 0.05 else page


def images_to_pdf(photos: list[bytes]) -> bytes:
    """Several photos of one document, in order, to one PDF with a page per photo."""
    if not photos:
        raise ValueError("no photos")
    pages = [clean_photo(p) for p in photos]
    buf = io.BytesIO()
    # 8.27 in is the A4 width: the PDF page comes out A4-sized whatever the photo's pixel count.
    res = pages[0].width / (8.27 if pages[0].height >= pages[0].width else 11.69)
    pages[0].save(buf, "PDF", resolution=res, save_all=True, append_images=pages[1:])
    return buf.getvalue()


def image_to_pdf(data: bytes) -> bytes:
    """One photo to a one-page PDF."""
    return images_to_pdf([data])
