"""Turn a born-digital SYNTHETIC statement into the conditions an analyst really receives.

Variants (deterministic per seed):
- ``digital``: the PDF as generated.
- ``scan``: 300 dpi grey office scan, slight skew, sensor noise.
- ``scan_poor``: 150 dpi black-and-white fax-like scan, more skew, speckles.
- ``photo``: phone photo on a table: perspective, rotation, shadow, blur, JPEG; then ``photo.images_to_pdf``.
- ``photo_hard``: the same in low light with a stronger angle and more blur.
- ``annotated``: the scan with pen marks a client adds: ticks, a circled figure, margin notes.
- ``handwritten``: a separate page of handwritten holdings and fees on lined paper (no printed text).

Handwriting uses OFL/Apache handwriting fonts cached in ``var/fonts`` (``ensure_fonts`` downloads them
from the Google Fonts repository and checks their SHA-256).
"""

# ruff: noqa: S311  (seeded test-data generator, not cryptography)
from __future__ import annotations

import hashlib
import io
import random
import urllib.request
from decimal import Decimal
from pathlib import Path

import numpy as np
import pypdfium2
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ...extraction.photo import images_to_pdf, perspective_coeffs
from .generate import fmt
from .universe import ROOT

FONT_DIR = ROOT / "var" / "fonts"
FONTS = {
    "Kalam-Regular.ttf": ("ofl/kalam/Kalam-Regular.ttf",
                          "57cecb63d4608019371954274ae1d8c397764debd5b19d4a33c1efa4dc923c0b"),
    "HomemadeApple-Regular.ttf": ("apache/homemadeapple/HomemadeApple-Regular.ttf",
                                  "dd1baaca3cde1b1f8415aed3b0aea6808655c9d9ca5a99c7282d9accc16c1a58"),
    "ReenieBeanie.ttf": ("ofl/reeniebeanie/ReenieBeanie.ttf",
                         "0ea608aa325bf9e11c9590cc0b63dcf7cd215e270784f1ebbe6fad4927b31ff8"),
}  # fmt: skip
VARIANTS = ("digital", "scan", "scan_poor", "photo", "photo_hard", "annotated", "handwritten")
INK = (20, 40, 140)


def ensure_fonts() -> list[Path]:
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for name, (path, sha) in FONTS.items():
        f = FONT_DIR / name
        if not f.exists():
            url = f"https://raw.githubusercontent.com/google/fonts/main/{path}"
            with urllib.request.urlopen(url, timeout=30) as r:
                f.write_bytes(r.read())
        if hashlib.sha256(f.read_bytes()).hexdigest() != sha:
            f.unlink()
            raise RuntimeError(f"font {name} failed its checksum")
        out.append(f)
    return out


def render_pages(pdf: bytes, dpi: int) -> list[Image.Image]:
    doc = pypdfium2.PdfDocument(pdf)
    try:
        return [doc[i].render(scale=dpi / 72).to_pil().convert("L") for i in range(len(doc))]
    finally:
        doc.close()


def _to_pdf(pages: list[Image.Image], dpi: int) -> bytes:
    buf = io.BytesIO()
    pages[0].save(buf, "PDF", resolution=dpi, save_all=True, append_images=pages[1:])
    return buf.getvalue()


def _noise(img: Image.Image, rng: np.random.Generator, sigma: float) -> Image.Image:
    a = np.asarray(img, dtype=float) + rng.normal(0, sigma, (img.height, img.width))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def scan(pdf: bytes, seed: int, poor: bool = False) -> bytes:
    rnd, rng = random.Random(seed), np.random.default_rng(seed)
    dpi = 150 if poor else 300
    out = []
    for p in render_pages(pdf, dpi):
        p = p.rotate(rnd.uniform(-1.6, 1.6) if poor else rnd.uniform(-0.6, 0.6), fillcolor=255, expand=False)
        p = _noise(p.filter(ImageFilter.GaussianBlur(0.6)), rng, 14 if poor else 6)
        if poor:
            p = p.point(lambda v: 255 if v > 150 else 0).convert("L")
            a = np.asarray(p).copy()
            speck = rng.random(a.shape) < 0.002
            a[speck] = 0
            p = Image.fromarray(a)
        out.append(p)
    return _to_pdf(out, dpi)


def _photo_one(page: Image.Image, rnd: random.Random, rng: np.random.Generator, hard: bool) -> bytes:
    pw, ph = page.size
    margin = int(pw * 0.18)
    canvas_w, canvas_h = pw + 2 * margin, ph + 2 * margin
    table = Image.fromarray(
        np.clip(rng.normal(95 if hard else 120, 12, (canvas_h, canvas_w)), 0, 255).astype(np.uint8)
    ).filter(ImageFilter.GaussianBlur(2))
    table.paste(page, (margin, margin))
    j = 0.09 if hard else 0.05
    src = [(margin, margin), (margin + pw, margin), (margin + pw, margin + ph), (margin, margin + ph)]
    dst = [(x + rnd.uniform(-j, j) * pw, y + rnd.uniform(-j, j) * ph) for x, y in src]
    coeffs = perspective_coeffs(src, dst)
    img = table.transform(
        (canvas_w, canvas_h), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC, fillcolor=90
    )
    yy, xx = np.mgrid[0:canvas_h, 0:canvas_w]
    angle = rnd.uniform(0, np.pi)
    grad = np.cos(angle) * xx / canvas_w + np.sin(angle) * yy / canvas_h
    light = (0.55 if hard else 0.8) + (0.35 if hard else 0.25) * (grad - grad.min()) / np.ptp(grad)
    band = np.exp(-(((xx - rnd.uniform(0.3, 0.7) * canvas_w) / (0.12 * canvas_w)) ** 2))
    light *= 1 - (0.35 if hard else 0.2) * band  # the phone's shadow across the page
    a = np.asarray(img, dtype=float) * light
    img = _noise(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)), rng, 9 if hard else 5)
    img = img.filter(ImageFilter.GaussianBlur(1.6 if hard else 0.9)).rotate(
        rnd.uniform(-4, 4), fillcolor=80, expand=True
    )
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=55 if hard else 72)
    return buf.getvalue()


def photos(pdf: bytes, seed: int, hard: bool = False) -> list[bytes]:
    rnd, rng = random.Random(seed), np.random.default_rng(seed)
    return [_photo_one(p, rnd, rng, hard) for p in render_pages(pdf, 170)]


def photo(pdf: bytes, seed: int, hard: bool = False) -> bytes:
    return images_to_pdf(photos(pdf, seed, hard))


def _font(rnd: random.Random, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(rnd.choice(ensure_fonts())), size)


def annotated(pdf: bytes, gold: dict, seed: int) -> bytes:
    """A scan with a client's pen marks: ticks beside rows, a circled total, notes in the margin."""
    rnd, rng = random.Random(seed), np.random.default_rng(seed)
    pages = [p.convert("RGB") for p in render_pages(pdf, 300)]
    notes = ["check!", "too high?", "ask bank", "ok", "sold in Oct", "?", "compare"]
    for p in pages:
        d = ImageDraw.Draw(p)
        w, h = p.size
        for _ in range(rnd.randint(4, 8)):
            x, y = rnd.randint(int(w * 0.93), int(w * 0.97)), rnd.randint(int(h * 0.25), int(h * 0.9))
            d.line([(x, y), (x + 12, y + 14), (x + 34, y - 18)], fill=INK, width=5)
        cx, cy = rnd.randint(int(w * 0.6), int(w * 0.85)), rnd.randint(int(h * 0.3), int(h * 0.8))
        d.ellipse([cx - 160, cy - 40, cx + 160, cy + 40], outline=INK, width=4)
        d.text((rnd.randint(30, 80), rnd.randint(int(h * 0.12), int(h * 0.2))), rnd.choice(notes),
               font=_font(rnd, 70), fill=INK)  # fmt: skip
    gray = [_noise(p.convert("L"), rng, 5) for p in pages]
    return _to_pdf(gray, 300)


def handwritten(gold: dict, seed: int) -> tuple[bytes, list[str]]:
    """A client's handwritten list of holdings and fees on lined paper; returns the PDF and the
    figures written on it (the gold for figure recall)."""
    rnd, rng = random.Random(seed), np.random.default_rng(seed)
    w, h = 2480, 3508
    page = Image.new("RGB", (w, h), (250, 248, 240))
    d = ImageDraw.Draw(page)
    for y in range(300, h - 200, 110):
        d.line([(120, y), (w - 120, y)], fill=(170, 190, 220), width=3)
    font = _font(rnd, 78)
    nf = "ch" if gold["currency"] == "CHF" else ("it" if gold["layout"].startswith("it") else "us")
    y = 200
    d.text((160, y), f"My portfolio ({gold['currency']})", font=font, fill=INK)
    figures = []
    for pos in gold["positions"][:10]:
        y += 220 if y == 200 else 110
        name = pos["name"].split(" ")[0] + (
            " " + pos["name"].split(" ")[1] if len(pos["name"].split()) > 1 else ""
        )
        qty = fmt(Decimal(pos["quantity"]), nf, 0)
        val = fmt(Decimal(pos["value"]), nf, 0 if rnd.random() < 0.5 else 2)
        d.text((160 + rnd.randint(-10, 10), y - 70), f"{qty}  {name}", font=font, fill=INK)
        d.text((1700 + rnd.randint(-15, 15), y - 70), val, font=font, fill=INK)
        figures.append(val)
    y += 220
    d.text((160, y - 70), "Bank fees this year:", font=font, fill=INK)
    for fee in gold["fees"][:3]:
        y += 110
        val = fmt(Decimal(fee["value"]), nf)
        d.text((220, y - 70), fee["label"][:24], font=font, fill=INK)
        d.text((1700, y - 70), val, font=font, fill=INK)
        figures.append(val)
    d.text((160, h - 260), "SYNTHETIC test page", font=_font(rnd, 50), fill=(200, 60, 60))
    img = _noise(page.convert("L").rotate(rnd.uniform(-1.5, 1.5), fillcolor=250), rng, 6)
    return _to_pdf([img], 300), figures
