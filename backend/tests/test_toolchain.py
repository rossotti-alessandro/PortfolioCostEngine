"""Smoke tests proving the extraction toolchain works end to end on synthetic inputs.

Each test produces evidence in the shape the product needs: a value plus where it came
from (page + bbox for PDFs, sheet + cell for spreadsheets).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import openpyxl
import pdfplumber
import pypdfium2 as pdfium
import pytest
from stdnum import isin

from pce.extraction import toolchain


def test_required_components_present() -> None:
    missing = [c.name for c in toolchain.check() if c.required and not c.available]
    assert missing == []


def test_born_digital_pdf_words_carry_bbox(statement_pdf: Path) -> None:
    with pdfplumber.open(statement_pdf) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()  # dicts with text, x0, x1, top, bottom (PDF points, top-left origin)
        width, height = page.width, page.height
    hit = next(w for w in words if w["text"] == "1,250.00")
    assert 0 < hit["x0"] < hit["x1"] < width and 0 < hit["top"] < hit["bottom"] < height
    assert Decimal(hit["text"].replace(",", "")) == Decimal("1250.00")


@pytest.mark.ocr
@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract binary not installed")
def test_scanned_page_ocr_recovers_amount_with_box(statement_pdf: Path) -> None:
    import pytesseract

    pdf = pdfium.PdfDocument(statement_pdf)
    image = pdf[0].render(scale=300 / 72).to_pil()  # simulate a scan: pixels only, no text layer
    pdf.close()
    data = pytesseract.image_to_data(image, lang="eng", output_type=pytesseract.Output.DICT)
    idx = [i for i, t in enumerate(data["text"]) if t.strip() == "1,250.00"]
    assert idx, f"OCR did not find the amount; got {[t for t in data['text'] if t.strip()]}"
    i = idx[0]
    assert data["width"][i] > 0 and data["height"][i] > 0 and float(data["conf"][i]) > 50


def test_xlsx_value_keeps_sheet_and_cell(tmp_path: Path) -> None:
    xlsx = tmp_path / "positions.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Positions"
    ws.append(["ISIN", "Market value CHF"])
    ws.append(["CH0012221716", 150000.25])
    wb.save(xlsx)
    ws2 = openpyxl.load_workbook(xlsx, read_only=True)["Positions"]
    cell = ws2["B2"]
    assert (ws2.title, cell.coordinate, Decimal(str(cell.value))) == ("Positions", "B2", Decimal("150000.25"))


@pytest.mark.parametrize(
    ("code", "valid"),
    [("CH0012221716", True), ("IE00B4L5Y983", True), ("IE00B4L5Y984", False), ("NOTANISIN123", False)],
)
def test_isin_check_digit(code: str, valid: bool) -> None:
    assert isin.is_valid(code) is valid


def test_canary_ocrmypdf_import_patches_pdfminer_globally(statement_pdf: Path) -> None:
    """ocrmypdf monkeypatches pdfminer's PDFSimpleFont at import time (ocrmypdf/pdfinfo/layout.py).

    After `import ocrmypdf`, text drawn with a standard font that has no /Encoding (common in
    bank-generated PDFs) extracts as nothing. Rule (.claude/rules/extraction.md): run OCRmyPDF as a
    subprocess, never import it in a process that reads PDFs with pdfplumber. If this canary starts
    failing, upstream changed the patch: re-check and relax the rule.
    """
    code = (
        "import sys, ocrmypdf, pdfplumber\n"
        "words = [w['text'] for w in pdfplumber.open(sys.argv[1]).pages[0].extract_words()]\n"
        "print('1,250.00' in words)\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code, str(statement_pdf)], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "False"
    assert "ocrmypdf" not in sys.modules
