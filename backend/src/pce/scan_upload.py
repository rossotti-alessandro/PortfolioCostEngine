"""Phone photos of paper pages into one PDF that the normal extraction path reads (SC-8.28).

Why a PDF: every later step (storage, OCR, evidence boxes, the PDF viewer) already works on PDFs, so a
photo becomes a scanned PDF and nothing downstream changes. The original photos are not kept.

The page cleanup (rotation, crop, deskew, lighting) belongs to ``pce.extraction.photo`` (accuracy
work, SC-9.8). Until that module exists this falls back to Pillow: EXIF rotation, RGB, one page per
photo. Pillow is already installed as a dependency of pdfplumber.
"""

from __future__ import annotations

import io

from PIL import Image, ImageOps, UnidentifiedImageError

from .errors import PceError

IMAGE_TYPES = {"image/jpeg", "image/png"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
MAX_PAGES = 30
MAX_PIXELS = 40_000_000  # a 40 MP photo is the most a phone sends; larger is a decompression bomb
PAGE_DPI = 300  # PDF page size follows the pixels at this density, so OCR sees scanner-like pages


class PhotoError(PceError):
    """A photo that cannot become a page."""


def _page(data: bytes) -> Image.Image:
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.width * im.height > MAX_PIXELS:
                raise PhotoError("photo has too many pixels")
            im = ImageOps.exif_transpose(im)  # phones store portrait shots as rotated landscape
            return im.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise PhotoError("not a readable JPEG or PNG photo") from exc


def photos_to_pdf(pages: list[bytes]) -> bytes:
    """One PDF page per photo, in the given order."""
    if not pages:
        raise PhotoError("no photos")
    if len(pages) > MAX_PAGES:
        raise PhotoError(f"at most {MAX_PAGES} pages per scan")
    try:  # the accuracy thread's cleanup, when merged
        from .extraction.photo import images_to_pdf  # type: ignore[attr-defined]
    except ImportError:
        images_to_pdf = None
    if images_to_pdf is not None:
        for p in pages:
            _page(p)  # same validation either way
        return images_to_pdf(pages)
    imgs = [_page(p) for p in pages]
    out = io.BytesIO()
    imgs[0].save(out, "PDF", resolution=PAGE_DPI, save_all=True, append_images=imgs[1:])
    return out.getvalue()
