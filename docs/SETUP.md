# Setup

## Quick start

```bash
git clone https://github.com/rossotti-alessandro/PortfolioCostEngine && cd PortfolioCostEngine
./scripts/bootstrap.sh            # add --docling for the layout/table models
cd backend && uv run python -m pce.extraction.toolchain
```

The toolchain check prints every engine and binary with its version and exits 1 if a required one is missing.

## What gets installed

### System packages

| Package | Why | macOS (brew) | Debian/Ubuntu (apt) |
|---|---|---|---|
| Tesseract 5 + language packs eng, ita, deu, fra | OCR of scanned pages | `tesseract tesseract-lang` | `tesseract-ocr tesseract-ocr-{eng,ita,deu,fra}` |
| Ghostscript | used by OCRmyPDF | `ghostscript` | `ghostscript` |
| qpdf | PDF repair, used by OCRmyPDF | `qpdf` | `qpdf` |
| Poppler (`pdftoppm`) | optional page rasteriser for debugging | `poppler` | `poppler-utils` |
| libmagic | MIME sniffing at upload | `libmagic` | `libmagic1` |
| uv, Node 22, pnpm | Python and frontend toolchains | `uv node pnpm` | see uv/nodejs docs |

Windows: use WSL2 with Ubuntu, then the apt column.

### Python (`backend/pyproject.toml`, exact pins, `uv.lock` committed)

| Package | Version | Licence | Role |
|---|---|---|---|
| pdfplumber (pdfminer.six) | 0.11.10 | MIT | words, chars, bbox, tables in born-digital PDFs |
| pypdfium2 | 5.15.0 | Apache-2.0 / BSD-3 | page rendering (OCR input, thumbnails) |
| pypdf | 7.0.0 | BSD-3 | metadata, encryption checks |
| ocrmypdf | 17.13.0 | MPL-2.0 | adds a Tesseract text layer to scans (run as CLI) |
| pytesseract | 0.3.13 | Apache-2.0 | word boxes on crops |
| openpyxl / xlrd | 3.1.5 / 2.0.2 | MIT / BSD | spreadsheets with cell provenance |
| pandas | 3.1.1 | BSD-3 | tabular normalisation |
| python-magic, defusedxml | 0.4.27, 0.7.1 | MIT, PSF | upload safety |
| python-stdnum | 2.2 | LGPL-2.1+ | ISIN check digits (unmodified library use) |
| httpx, beautifulsoup4, lxml | 0.28.1, 4.15.0, 6.1.3 | BSD, MIT, BSD | allowlisted public KID/factsheet retrieval |
| fastapi, pydantic, sqlalchemy, alembic, uvicorn | see pyproject | MIT/BSD | API and storage |
| **docling** (extra `docling`) | 2.148.0 | MIT (models: check per model) | layout and table structure; pulls PyTorch |
| **paddleocr** (extra `vlm`) | 3.7.0 | Apache-2.0 | benchmark candidate only (SC-5.6) |

Not used, on purpose: **PyMuPDF** (AGPL-3.0 or paid licence), Marker (model weights under OpenRAIL-M with
revenue limits). See ADR 0003.

### Docling and PyTorch size

`uv sync --extra docling` pulls PyTorch. On Linux, PyPI's default wheel bundles CUDA libraries (about 6 GB
in total). On a CPU-only Linux box, install the CPU wheel first to save ~4 GB:
`uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu` then `uv sync --extra docling --inexact`.
macOS wheels are CPU/Metal and small.

## Agent tooling

- Git hooks: `./scripts/setup-hooks.sh` (bootstrap runs it). Conventional commits, secret scan, no client
  documents outside fixture folders, ruff on staged Python, fast gate on push.
- Skills vendored in `.agents/skills/` (Codex reads them there; Claude Code via the `.claude/skills/` symlinks):
  - `caveman` (JuliusBrussee/caveman, Apache-2.0): terse replies to people, `lite` level by default.
  - `ponytail`, `ponytail-review` (DietrichGebert/ponytail, MIT): smallest complete change; review for necessity.
  Pinned hashes in `skills-lock.json`. Update by copying the new upstream `SKILL.md` and its hash.
- Claude Code users who prefer the plugin form can install caveman from its marketplace instead; the
  vendored copy keeps cloud sessions and Codex consistent.
