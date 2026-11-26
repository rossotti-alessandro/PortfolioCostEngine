"""SC-9.8: phone photos become an upright, flat, evenly lit PDF page. Pages are SYNTHETIC."""

from __future__ import annotations

import importlib.util
import io

import numpy as np
import pypdf
import pytest
from PIL import Image, ImageDraw, ImageFont

from pce.extraction.photo import clean_photo, image_to_pdf, images_to_pdf, page_corners, perspective_coeffs

NO_RAPIDOCR = importlib.util.find_spec("rapidocr") is None
needs_rapidocr = pytest.mark.skipif(NO_RAPIDOCR, reason="rapidocr extra not installed")


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


def test_photo_taken_sideways_without_exif_flag_is_turned_so_text_runs_across() -> None:
    """SC-9.12: a landscape phone picture stored without a rotation flag read 0 of 15 holdings."""
    page = Image.new("L", (600, 850), 255)
    draw = ImageDraw.Draw(page)
    for y in range(60, 800, 22):
        draw.rectangle((40, y, 40 + (y * 7) % 400 + 120, y + 9), fill=0)  # text lines of varying length
    for turn in (90, 270):
        buf = io.BytesIO()
        page.rotate(turn, expand=True).save(buf, "PNG")
        out = clean_photo(buf.getvalue())
        assert out.size[1] > out.size[0], turn


@needs_rapidocr
def test_upside_down_photo_is_turned_back() -> None:
    """SC-9.12: the OCR reader rights each upside-down line but reverses the row order and the cells in a
    row, so an upside-down statement gave every holding a wrong value."""
    page = Image.new("L", (1000, 1400), 255)
    draw = ImageDraw.Draw(page)
    font = ImageFont.load_default(28)
    for i, y in enumerate(range(80, 1300, 60)):
        draw.text(
            (60, y), f"Synthetic Fund {i} Accumulation  CH00{i:02d}1234567  1'234.{i:02d}", font=font, fill=0
        )
    buf = io.BytesIO()
    page.rotate(180).save(buf, "PNG")
    out = np.asarray(clean_photo(buf.getvalue()).resize((100, 140)), dtype=float)
    ref = np.asarray(page.resize((100, 140)), dtype=float)
    assert np.abs(out - ref).mean() < np.abs(out[::-1, ::-1] - ref).mean()


@needs_rapidocr
def test_a_detection_only_call_does_not_switch_off_reading_for_later_calls() -> None:
    """SC-9.12: RapidOCR keeps the last call's switches; the orientation checks must not leak them."""
    from pce.extraction import layout

    page = Image.new("RGB", (600, 120), "white")
    ImageDraw.Draw(page).text((20, 40), "Custody fee 1'234.50", font=ImageFont.load_default(28), fill="black")
    a = np.asarray(page)
    layout.rapid(a, use_cls=False, use_rec=False)
    assert layout.rapid(a).txts
