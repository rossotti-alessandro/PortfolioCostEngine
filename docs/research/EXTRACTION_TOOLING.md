# Document extraction and OCR tooling

Research notes, 2026-11-06. Versions and licences from PyPI/GitHub (`SRC-DOCLING` … `SRC-UNSTRUCTURED` in [`SOURCE_REGISTER.md`](SOURCE_REGISTER.md)). The app thread decides the final stack; this is the input.

## The documents we will see

Most Swiss bank statements are **born-digital PDFs** with a text layer: tables extract well without OCR. Scans appear when prospects photograph or re-scan paper statements, and with older insurance documents. So the pipeline should try text extraction first and fall back to OCR only per page.

## Candidates

| Tool | Version | Licence | Good at | Watch out | Verdict |
|---|---|---|---|---|---|
| **pdfplumber** | 0.11.10 | MIT | Exact words with coordinates; ruled and aligned tables; "works best on machine-generated PDFs" | No OCR | **Core**: text + bounding boxes for the evidence viewer |
| **Docling** | 2.148.0 | MIT | Layout, reading order, table structure, OCR hooks, runs locally / air-gapped | Heavier (ML models); model licences per package | **Core** for complex layouts, second opinion on tables |
| **Camelot** | 2.0.0 | MIT | Table extraction (lattice/stream/hybrid; ML flavour) | Text PDFs only unless `[ml,ocr]` | Optional, for stubborn tables |
| **Tesseract** | 5.x | Apache-2.0 | Classic OCR, 100+ languages incl. German, French, Italian | Needs language packs (`deu`, `fra`, `ita`); weak on tables alone | **Core OCR** |
| **OCRmyPDF** | — | MPL-2.0 | Adds a text layer to scanned PDFs using Tesseract, keeps layout; then pdfplumber works | Needs Ghostscript | **Core** for scans |
| **PaddleOCR** (PP-StructureV3, PaddleOCR-VL-1.6) | 3.7.0 | Apache-2.0 | Strong OCR + table cells with coordinates; small local VLM | Needs PaddlePaddle; heavier install | Candidate for hard scans; benchmark first |
| **PyMuPDF** | 2.0 | **AGPL-3.0** or commercial | Fast rendering and text | AGPL: a hosted or distributed closed product must buy a licence from Artifex | **Avoid** unless Safe Capital buys a licence (the ChatGPT kit recommended it) |
| **Marker** | — | Code Apache-2.0, **weights OpenRAIL-M** (free under USD 5M revenue/funding) | PDF to markdown with tables | Commercial limits; `--use_llm` sends content to cloud LLMs | Avoid for now |
| **MinerU** | 4.x | Apache-2.0 + extra terms | Strong layout | Online services must display attribution | Possible, check terms |
| **Unstructured** | — | Apache-2.0 | Generic partitioning | Its own benchmark shows weak OSS table accuracy (0.43 vs 0.87 paid) | Not for tables |
| Cloud (Azure Document Intelligence, AWS Textract, Google Document AI) | — | Commercial | Strong forms/tables | Client data leaves the office; residency not researched | Only under option C in the privacy note |

Renderer for page images in the evidence viewer without AGPL: **pypdfium2** (Apache-2.0/BSD) or `pdftoppm` from Poppler (GPL, used as an external program). Browser side: **PDF.js** (Apache-2.0).

## Recommended local stack for the demo

1. `pdfplumber` for words, coordinates and simple tables (evidence boxes come from here).
2. `Docling` for layout and complex tables; compare with pdfplumber, flag disagreements.
3. `OCRmyPDF` + `Tesseract` (`deu+fra+ita+eng`) when a page has no text layer.
4. Optional LLM step only on structured text (not raw PDFs), behind the privacy switch, with numbers re-checked against the source text by code.
5. `pypdfium2` for page rendering; PDF.js in the UI.

System packages: `tesseract-ocr`, `tesseract-ocr-deu`, `tesseract-ocr-fra`, `tesseract-ocr-ita`, `ghostscript`, `qpdf` (for OCRmyPDF), `poppler-utils`.

## How to validate extraction (no marketing benchmarks)

Build a small gold set: the kit's fictitious statement (3 pages) plus 5–10 real anonymised Safe Capital prospect documents. Measure per field: exact match on amounts, ISIN, dates; table row/column association; the share of values with a correct bounding box. A number with no evidence box does not reach the ledger.
