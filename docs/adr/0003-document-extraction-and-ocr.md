# ADR 0003 — Document extraction and OCR toolchain

Status: Accepted, 2026-11-06. Research input: `docs/research/EXTRACTION_TOOLING.md`.

## Context

Prospects bring bank statements (mostly born-digital PDFs), annual cost reports, tariff sheets, mandate
agreements, fund KIDs/factsheets, spreadsheets, and sometimes scans or phone photos. Every extracted value
must keep its source location (page + bbox, or sheet + cell) for the evidence viewer. The tool will be
used commercially by a wealth manager, so licences matter. The ChatGPT handoff recommended PyMuPDF; it is
AGPL-3.0 (or a paid Artifex licence), which would oblige a hosted or distributed closed product to release
its source or buy a licence.

## Decision

Engines, tried per page in this order (`.claude/rules/extraction.md`):

| Need | Engine | Licence |
|---|---|---|
| Words/chars with bbox, simple tables (born-digital) | pdfplumber 0.11.10 (pdfminer.six) | MIT |
| Page rendering (OCR input, thumbnails) | pypdfium2 5.15.0 | Apache-2.0 / BSD-3 |
| Layout, reading order, complex tables (second opinion) | Docling 2.148.0, optional extra | MIT (check each model card) |
| Scans: add text layer | OCRmyPDF 17.13.0 → Tesseract 5 (`eng+ita+deu+fra`), via CLI subprocess | MPL-2.0 / Apache-2.0 |
| Scans: page reader when installed (SC-5.22) | RapidOCR 3.10.0 (PP-OCR ONNX models bundled in the wheel) + onnxruntime 1.32.0, extra `rapidocr`; Tesseract otherwise | Apache-2.0 / MIT |
| Word boxes on a crop | pytesseract 0.3.13 | Apache-2.0 |
| XLSX / XLS / CSV | openpyxl 3.1.5, xlrd 2.0.2, pandas 3.1.1 | MIT / BSD |
| Identifiers | python-stdnum 2.2 (ISIN check digit) | LGPL-2.1+ (library use) |
| Browser viewer | PDF.js | Apache-2.0 |
| VLM for hard scans | PaddleOCR 3.7 / PaddleOCR-VL as **benchmark candidate only** (extra `vlm`) | Apache-2.0 |

Rules that follow from testing in this repo (`backend/tests/test_toolchain.py`):

- **OCRmyPDF is run as a subprocess, never imported** next to pdfplumber: importing it monkeypatches
  pdfminer's `PDFSimpleFont`, after which text in standard fonts without `/Encoding` extracts as empty.
  A canary test pins this behaviour.
- PyMuPDF is excluded directly and transitively (`uv.lock` contains no `pymupdf`).
- The toolchain health check (`python -m pce.extraction.toolchain`) uses `find_spec`, not imports, to avoid
  side effects and slow start-up.

Model choice is empirical: the golden-corpus evaluation (SC-9.1) decides when Docling or a VLM is used,
measured per field (exact amounts, ISINs, dates, row association, bbox correctness, abstention), not by
vendor benchmarks.

## Consequences

- Core install is light (no PyTorch). `--extra docling` adds PyTorch; on Linux the default PyPI wheel
  bundles NVIDIA CUDA libraries under NVIDIA's proprietary redistributable licence and ~6 GB; CPU wheels
  avoid both (docs/SETUP.md).
- Dependency upgrades go in `deps:` PRs with a licence line per new package.

## Amendment 2026-11-13: RapidOCR reads scans (SC-5.22)

On the 11 scan pages of the ocrbench gold, production `extract()` found 69.7% of the printed fees with
RapidOCR against 52.8% with Tesseract, with 3 wrong values against 10, at 4.3 s/page against 6.9 s/page
on CPU. RapidOCR runs locally (ONNX, no GPU, no network: models ship in the wheel), so ADR 0004 is
unaffected. It is an optional extra; without it Tesseract reads scans as before. The Tesseract crop
re-read (`verify.second_reading`) stays, and is now an independent engine from the page reader.
OCRmyPDF still adds text layers where a searchable PDF is wanted.

## Alternatives rejected

- PyMuPDF / pymupdf4llm: AGPL. Reconsider only if the organisation buys an Artifex licence (new ADR).
- Marker: model weights under OpenRAIL-M with revenue limits; optional LLM mode sends content to the cloud.
- Cloud OCR (Azure Document Intelligence, AWS Textract, Google Document AI): client data leaves the machine; only under ADR 0004 option C.
- Unstructured OSS for tables: weak table accuracy in its own published comparison.
