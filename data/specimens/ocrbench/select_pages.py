"""Pick a stratified benchmark page set from the specimen corpus and render it (SC-5.6).

For each stratum (document family x language) it takes the first files in name order
that are present in ``var/specimens`` and keeps the page with the most fee lines
(a fee word and a number on the same line). The choice is deterministic so a re-run on
the same corpus gives the same pages.

It also makes "scan-sim" copies of some pages: grey, 150 dpi, slight skew, blur, noise
and JPEG artefacts. They are real pages degraded on purpose (labelled SIMULATED SCAN),
because the corpus holds only two true scans.

Usage (bench venv, see README):
    python data/specimens/ocrbench/select_pages.py
Writes var/ocrbench/pages/<page_id>.png, <page_id>.pdf (single page) and
data/specimens/ocrbench/pages.json (committed: file, sha256, page, stratum).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import random
import re
from itertools import zip_longest
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "data" / "reference" / "specimen_corpus.csv"
FILES = ROOT / "var" / "specimens"
OUT = ROOT / "var" / "ocrbench" / "pages"
PAGES_JSON = Path(__file__).with_name("pages.json")
SCALE = 2

FEE_WORDS = re.compile(
    r"(fee|cost|charge|commission|expense|ter\b|ocf|spread|custody|brokerage|"
    r"geb[üu]hr|kosten|kommission|courtage|depot|spesen|entgelt|"
    r"frais|commission|droits? de garde|courtage|"
    r"costi|commissione|spese|oneri|custodia|diritti)",
    re.I,
)
NUMBER = re.compile(r"\d[\d'’ .,]*\s?(%|chf|eur|usd|gbp|bp|bps|p\.a\.)|\d+[.,]\d+", re.I)

# (stratum name, document types, languages, how many files)
STRATA = [
    ("KID fund EN", {"kid_priips"}, {"en"}, 2),
    ("KID fund DE", {"kid_priips"}, {"de"}, 2),
    ("KID fund FR", {"kid_priips"}, {"fr"}, 2),
    ("KID fund IT", {"kid_priips"}, {"it"}, 2),
    ("KID insurance", {"insurance_kid", "insurance_dip"}, {"it", "de", "fr", "en"}, 2),
    ("KID Swiss FinSA", {"kid_finsa"}, {"de", "fr", "it", "en"}, 1),
    ("Price list DE", {"general_price_list"}, {"de"}, 2),
    ("Price list FR", {"general_price_list"}, {"fr"}, 2),
    ("Price list IT", {"general_price_list"}, {"it"}, 2),
    ("Price list EN", {"general_price_list"}, {"en"}, 1),
    ("Custody tariff", {"custody_tariff"}, {"de", "fr", "it", "en"}, 3),
    ("Cost disclosure", {"cost_disclosure"}, {"de", "fr", "it", "en"}, 3),
    ("Annual cost report", {"annual_cost_report"}, {"de", "fr", "it", "en"}, 2),
    ("Portfolio statement", {"portfolio_statement"}, {"de", "fr", "it", "en"}, 2),
    ("Factsheet", {"factsheet"}, {"de", "fr", "it", "en"}, 3),
    ("SP termsheet", {"sp_termsheet"}, {"de", "fr", "it", "en"}, 2),
    ("Fund report / prospectus", {"annual_report_fund", "prospectus"}, {"de", "fr", "it", "en"}, 2),
    ("Mandate contract", {"mandate_contract"}, {"de", "fr", "it", "en"}, 1),
]
SCAN_SIM_EVERY = 6
# True scans have no text layer, so fee lines cannot be counted: pages picked by eye.
TRUE_SCAN_PAGES = {"sample-utrade-sg-statement.pdf": 2, "sample-scotia-swm-releves-fr.pdf": 3}  # every 6th born-digital page also gets a simulated-scan copy


def fee_lines(page) -> int:
    text = page.extract_text() or ""
    return sum(1 for ln in text.splitlines() if FEE_WORDS.search(ln) and NUMBER.search(ln))


def best_page(path: Path) -> tuple[int, int, bool]:
    """(1-based page, fee lines, has text layer) for the page with the most fee lines."""
    with pdfplumber.open(path) as pdf:
        best = (1, -1, False)
        for i, p in enumerate(pdf.pages[:40]):
            n = fee_lines(p)
            has_text = len(p.chars) > 50
            if n > best[1]:
                best = (i + 1, n, has_text)
        return best


def simulate_scan(img: Image.Image, seed: int) -> Image.Image:
    rnd = random.Random(seed)
    g = img.convert("L").resize((img.size[0] * 150 // 144, img.size[1] * 150 // 144))
    g = g.rotate(rnd.uniform(-1.2, 1.2), expand=False, fillcolor=255, resample=Image.BICUBIC)
    g = g.filter(ImageFilter.GaussianBlur(0.7))
    px = g.load()
    for _ in range(g.size[0] * g.size[1] // 60):
        x, y = rnd.randrange(g.size[0]), rnd.randrange(g.size[1])
        px[x, y] = max(0, min(255, px[x, y] + rnd.randint(-90, 90)))
    buf = io.BytesIO()
    g.save(buf, "JPEG", quality=55)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB").resize(img.size)


def main() -> None:
    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8")))
    OUT.mkdir(parents=True, exist_ok=True)
    used: set[str] = set()
    pages: list[dict] = []

    def add(row: dict, stratum: str, page: int, n: int, has_text: bool) -> None:
        path = FILES / row["file"]
        pid = re.sub(r"[^a-z0-9]+", "-", row["file"].lower().removesuffix(".pdf"))[:60] + f"-p{page}"
        src = pdfium.PdfDocument(path)
        one = pdfium.PdfDocument.new()
        one.import_pages(src, [page - 1])
        one.save(OUT / f"{pid}.pdf")
        img = src[page - 1].render(scale=SCALE).to_pil().convert("RGB")
        with pdfplumber.open(path) as pl:  # text layer of the chosen page itself
            has_text = len(pl.pages[page - 1].chars) > 50
        img.save(OUT / f"{pid}.png")
        pages.append({
            "id": pid, "file": row["file"], "sha256": row["sha256"], "page": page,
            "stratum": stratum, "document_type": row["document_type"], "language": row["language"],
            "issuer": row["issuer"], "fee_lines": n, "text_layer": has_text, "variant": "original",
            "width": img.size[0], "height": img.size[1],
        })
        used.add(row["file"])

    def present(r: dict) -> bool:
        p = FILES / r["file"]
        return p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == r["sha256"]

    for stratum, types, langs, k in STRATA:
        pool = sorted(
            (r for r in rows if r["document_type"] in types and r["language"] in langs
             and r["file"] not in used and r["scanned"] != "true"),
            key=lambda r: (r["issuer"], r["file"]),
        )
        # Round-robin over languages (en, fr, it, de) so a stratum is not all German.
        by_lang = {lg: [r for r in pool if r["language"] == lg] for lg in ("en", "fr", "it", "de")}
        cands = [r for tier in zip_longest(*by_lang.values()) for r in tier if r]
        taken, issuers = 0, set()
        for r in cands:  # spread over issuers and languages: one file per issuer per stratum
            if taken >= k or r["issuer"] in issuers or not present(r):
                continue
            page, n, has_text = best_page(FILES / r["file"])
            if n < 2:  # no fee content worth benchmarking on this file
                continue
            add(r, stratum, page, n, has_text)
            taken += 1
            issuers.add(r["issuer"])
    for r in rows:  # the corpus's true scans
        if r["scanned"] == "true" and present(r):
            page, n, has_text = best_page(FILES / r["file"])
            page = TRUE_SCAN_PAGES.get(r["file"], page)
            add(r, "Scanned / image content", page, n, has_text)

    originals = [p for p in pages if p["text_layer"] and p["stratum"] != "Scanned / image content"]
    for i, p in enumerate(originals[::SCAN_SIM_EVERY]):
        img = simulate_scan(Image.open(OUT / f"{p['id']}.png"), seed=i)
        sid = p["id"] + "-scan"
        img.save(OUT / f"{sid}.png")
        # Image-only PDF: no text layer, exactly like a scanned upload.
        img.save(OUT / f"{sid}.pdf", "PDF", resolution=72 * SCALE)
        pages.append({**p, "id": sid, "variant": "scan-sim", "stratum": "Simulated scan", "text_layer": False, "gt_from": p["id"]})
    PAGES_JSON.write_text(json.dumps(pages, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(pages)} pages -> {OUT}")
    for p in pages:
        print(f"{p['stratum']:<26} {p['language']} {p['fee_lines']:>3} {p['id']}")


if __name__ == "__main__":
    main()
