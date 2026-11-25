"""SC-9.8: phone photos become an upright, flat, evenly lit PDF page. Pages are SYNTHETIC."""

from __future__ import annotations

import io

import numpy as np
import pypdf
from PIL import Image, ImageDraw

from pce.extraction.photo import clean_photo, image_to_pdf, images_to_pdf, page_corners, perspective_coeffs


def _photo(angle: float = 0.0, exif_rotate: bool = False) -> bytes:
    """A white 'page' with black bars, tilted in perspective on a grey table, as JPEG."""
    page = Image.new("L", (420, 594), 255)
    d = ImageDraw.Draw(page)
    for y in range(60, 560, 40):
        d.rectangle([40, y, 380, y + 12], fill=0)
    table = Image.new("L", (700, 900), 90)
    table.paste(page, (140, 150))
    src = [(140, 150), (560, 150), (560, 744), (140, 744)]
    dst = [(170, 130), (540, 175), (575, 760), (120, 720)]
    img = table.transform((700, 900), Image.Transform.PERSPECTIVE, perspective_coeffs(src, dst), fillcolor=90)
    img = img.rotate(angle, fillcolor=90)
    buf = io.BytesIO()
    if exif_rotate:  # stored sideways with an EXIF "rotate 90" flag, as phones do
        exif = Image.Exif()
        exif[0x0112] = 6
        img.rotate(90, expand=True).save(buf, "JPEG", exif=exif)
    else:
        img.save(buf, "JPEG")
    return buf.getvalue()


def test_page_outline_is_found_and_flattened_to_a4_portrait() -> None:
    out = clean_photo(_photo())
    assert abs(out.height / out.width - 297 / 210) < 0.01
    a = np.asarray(out)
    assert a[: a.shape[0] // 20].mean() > 200  # the grey table is cropped away: the top edge is paper


def test_exif_rotation_is_applied() -> None:
    out = clean_photo(_photo(exif_rotate=True))
    assert out.height > out.width


def test_no_page_outline_keeps_the_whole_picture() -> None:
    flat = Image.new("L", (600, 800), 128)
    buf = io.BytesIO()
    flat.save(buf, "PNG")
    assert page_corners(flat) is None
    assert clean_photo(buf.getvalue()).size == (600, 800)


def test_several_photos_make_one_pdf_with_a_page_each() -> None:
    pdf = images_to_pdf([_photo(), _photo(2.0)])
    reader = pypdf.PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) == 2
    w, h = (float(x) for x in reader.pages[0].mediabox.upper_right)
    assert abs(w - 595) < 3 and abs(h - 842) < 4  # A4 in points
    assert pypdf.PdfReader(io.BytesIO(image_to_pdf(_photo()))).pages
