"""Shared fixtures: a tiny hand-built PDF so tests need no PDF-writing library."""

from __future__ import annotations

from pathlib import Path

import pytest

FEE_LINE = "Custody fee 0.25% p.a. CHF 1,250.00"


def write_text_pdf(path: Path, lines: list[tuple[float, float, int, str]]) -> None:
    """Write a one-page A4 PDF with Helvetica text lines given as (x, y_from_bottom, size, text)."""
    content = "".join(
        f"BT /F1 {size} Tf {x} {y} Td ({text.replace('(', r'\\(').replace(')', r'\\)')}) Tj ET\n"
        for x, y, size, text in lines
    ).encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    path.write_bytes(bytes(out))


@pytest.fixture
def statement_pdf(tmp_path: Path) -> Path:
    """A synthetic one-page statement with a custody fee line."""
    pdf = tmp_path / "statement.pdf"
    write_text_pdf(pdf, [(72, 742, 14, "SYNTHETIC DEMO STATEMENT"), (72, 702, 12, FEE_LINE)])
    return pdf
