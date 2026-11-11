"""Extraction toolchain health check.

Reports which document-extraction engines are importable and which system binaries
are on PATH, with versions, so a developer or CI job can see at a glance whether a
machine can parse born-digital PDFs, OCR scans, read spreadsheets and run Docling.

Run: ``uv run python -m pce.extraction.toolchain`` (exit code 1 if a required engine is missing).
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Component:
    """One engine or binary the extraction pipeline can use."""

    name: str
    purpose: str
    required: bool
    available: bool
    version: str | None


# (import name, distribution name, purpose, required)
PYTHON_ENGINES: tuple[tuple[str, str, str, bool], ...] = (
    ("pdfplumber", "pdfplumber", "born-digital PDF words/chars with bbox, tables", True),
    ("pypdfium2", "pypdfium2", "PDFium: page render for OCR and the viewer, text boxes", True),
    ("pypdf", "pypdf", "PDF metadata, encryption and structure checks", True),
    ("ocrmypdf", "ocrmypdf", "add Tesseract text layer to scanned PDFs", True),
    ("pytesseract", "pytesseract", "word-level OCR boxes on page crops", True),
    ("openpyxl", "openpyxl", "XLSX cells with sheet/cell provenance", True),
    ("xlrd", "xlrd", "legacy XLS", True),
    ("pandas", "pandas", "CSV and tabular normalisation", True),
    ("magic", "python-magic", "MIME sniffing at intake", True),
    ("stdnum", "python-stdnum", "ISIN check-digit validation", True),
    ("docling", "docling", "layout and table structure model (optional extra)", False),
    ("paddleocr", "paddleocr", "OCR/VLM benchmark candidate (optional extra)", False),
)

# (binary, version flag, purpose, required)
BINARIES: tuple[tuple[str, str, str, bool], ...] = (
    ("tesseract", "--version", "OCR engine (eng, ita, deu, fra language packs)", True),
    ("gs", "--version", "Ghostscript, used by ocrmypdf", True),
    ("qpdf", "--version", "PDF repair/linearise, used by ocrmypdf", True),
    ("pdftoppm", "-v", "poppler page rasteriser", False),
)


def _python_engine(module: str, dist: str, purpose: str, required: bool) -> Component:
    # find_spec, not import: importing heavy engines (docling, torch) is slow and has global side effects.
    if importlib.util.find_spec(module) is None:
        return Component(module, purpose, required, False, None)
    try:
        version = importlib.metadata.version(dist)
    except importlib.metadata.PackageNotFoundError:
        version = None
    return Component(module, purpose, required, True, version)


def _binary(name: str, flag: str, purpose: str, required: bool) -> Component:
    path = shutil.which(name)
    if path is None:
        return Component(name, purpose, required, False, None)
    out = subprocess.run([path, flag], capture_output=True, text=True, timeout=10, check=False)  # noqa: S603
    text = (out.stdout or out.stderr).strip().splitlines()
    return Component(name, purpose, required, True, text[0] if text else None)


def tesseract_languages() -> list[str]:
    """Return installed Tesseract language packs, or an empty list if Tesseract is missing."""
    path = shutil.which("tesseract")
    if path is None:
        return []
    out = subprocess.run([path, "--list-langs"], capture_output=True, text=True, timeout=10, check=False)  # noqa: S603
    return [line.strip() for line in out.stdout.splitlines()[1:] if line.strip()]


def check() -> list[Component]:
    """Probe every engine and binary; never raises."""
    return [_python_engine(*e) for e in PYTHON_ENGINES] + [_binary(*b) for b in BINARIES]


def main() -> int:
    """Print a table and return 1 when a required component is missing."""
    components = check()
    for c in components:
        mark = "ok " if c.available else ("MISSING" if c.required else "absent (optional)")
        print(f"{mark:18} {c.name:12} {c.version or '-':40.40} {c.purpose}")
    print(f"{'':18} tesseract languages: {', '.join(tesseract_languages()) or '-'}")
    missing = [c.name for c in components if c.required and not c.available]
    if missing:
        print(f"\nMissing required components: {', '.join(missing)}. See docs/SETUP.md.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
