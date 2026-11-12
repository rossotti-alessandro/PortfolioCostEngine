"""Document extraction: born-digital parsing, OCR and spreadsheet readers with provenance."""

import os

# Tesseract's OpenMP threads busy-wait: on a CPU shared with other work one page went from 2 s to 87 s.
# pytesseract runs Tesseract as a subprocess that inherits this. An explicit operator value wins. SC-5.9.
os.environ.setdefault("OMP_THREAD_LIMIT", "1")
