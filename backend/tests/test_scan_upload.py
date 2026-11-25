"""Phone photos become one scanned PDF that the normal OCR path reads (SC-8.28). All images are SYNTHETIC."""

import io
import os
import tempfile

os.environ.setdefault("PCE_DATA_DIR", tempfile.mkdtemp(prefix="pce-test-"))
os.environ.setdefault("PCE_DATABASE_URL", f"sqlite:///{os.environ['PCE_DATA_DIR']}/t.sqlite")

import pypdfium2 as pdfium
import pytest
from conftest import session_headers
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from pce import scan_upload
from pce.api import app

client = TestClient(app)
A = session_headers("scan-firm", "scan.ana", "analyst")


def photo(
    text: str, fmt: str = "PNG", size: tuple[int, int] = (1240, 1754), exif_rotate: bool = False
) -> bytes:
    """A white 'page' with large black text, like a phone shot of a printed statement."""
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=56)
    for i, line in enumerate(["SYNTHETIC DEMO STATEMENT", text]):
        d.text((80, 120 + i * 110), line, fill="black", font=font)
    buf = io.BytesIO()
    if exif_rotate:  # stored sideways with "rotate 90" in EXIF, as phones do for portrait shots
        im = im.rotate(90, expand=True)
        exif = Image.Exif()
        exif[0x0112] = 6
        im.save(buf, fmt, exif=exif)
    else:
        im.save(buf, fmt)
    return buf.getvalue()


def new_prospect(code: str) -> int:
    r = client.post("/api/prospects", json={"code": code, "label": "SYNTHETIC", "domicile": "CH"}, headers=A)
    return r.json()["id"]


def test_photos_to_pdf_one_page_each_and_fixes_rotation():
    pdf = pdfium.PdfDocument(
        scan_upload.photos_to_pdf([photo("Page 1"), photo("Page 2", "JPEG", exif_rotate=True)])
    )
    assert len(pdf) == 2
    w, h = pdf[1].get_size()
    assert h > w  # the sideways-stored portrait shot is upright again


def test_bad_photos_are_refused():
    with pytest.raises(scan_upload.PhotoError):
        scan_upload.photos_to_pdf([b"not an image at all"])
    with pytest.raises(scan_upload.PhotoError):
        scan_upload.photos_to_pdf([])
    with pytest.raises(scan_upload.PhotoError):
        scan_upload.photos_to_pdf([photo("x")] * (scan_upload.MAX_PAGES + 1))


@pytest.mark.ocr
def test_three_photos_with_combine_become_one_ocr_read_document():
    pid = new_prospect("SCAN-1")
    files = [
        ("files", (f"IMG_{i}.jpg", photo(f"Custody fee page {i}", "JPEG"), "image/jpeg")) for i in (1, 2, 3)
    ]
    r = client.post(
        f"/api/prospects/{pid}/documents",
        files=files,
        data={"combine": "true", "scan_name": "Paper statement"},
        headers=A,
    )
    assert r.status_code == 200, r.text
    res = r.json()["results"]
    assert len(res) == 1 and res[0]["filename"] == "Paper statement.pdf"
    assert res[0]["status"] != "rejected", res
    doc = client.get(f"/api/prospects/{pid}/documents", headers=A).json()[0]
    assert len(doc["pages"]) == 3
    assert all(pg["engine"] != "pdfplumber" for pg in doc["pages"])  # no text layer: read by OCR
    stored = client.get(f"/api/documents/{doc['id']}/file", headers=A)
    assert stored.headers["content-type"] == "application/pdf"


def test_fake_photo_is_refused_and_pdf_upload_unchanged(statement_pdf):
    pid = new_prospect("SCAN-2")
    r = client.post(
        f"/api/prospects/{pid}/documents",
        files=[
            ("files", ("photo.jpg", b"%PDF-1.4 pretending to be a photo", "image/jpeg")),
            ("files", ("statement.pdf", statement_pdf.read_bytes(), "application/pdf")),
        ],
        headers=A,
    )
    res = {x["filename"]: x for x in r.json()["results"]}
    assert res["photo.jpg"]["status"] == "rejected"
    assert "not a JPEG or PNG" in res["photo.jpg"]["error"]
    assert res["statement.pdf"]["status"] in ("extracted", "needs_review")
