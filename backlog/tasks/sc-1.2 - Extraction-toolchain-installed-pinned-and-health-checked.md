---
id: SC-1.2
title: Extraction toolchain installed, pinned and health-checked
status: "Done"
assignee: []
owner: "Set up multi-agent dev protocol"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-pd19xu"
pr: ""
created_date: "2026-11-06 15:05"
updated_date: "2026-11-06 15:04"
labels:
  - infra
  - extraction
dependencies: []
parent_task_id: SC-1
priority: P0
paths_owned:
  - "backend/pyproject.toml"
  - "backend/uv.lock"
  - "backend/.python-version"
  - "backend/src/pce/extraction/toolchain.py"
  - "backend/tests/test_toolchain.py"
  - "backend/tests/conftest.py"
  - "docs/SETUP.md"
  - "scripts/bootstrap.sh"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs:
  - ".claude/rules/extraction.md"
---

> **One-liner**: Install and pin every OCR and parsing engine so any machine can prove it can extract with evidence.

## Description

### Context

No toolchain. The kit recommended PyMuPDF, which is AGPL.

### User Flow Impact

No user-facing change; enables every extraction story.

### Performance / Efficiency Impact

Core install without PyTorch; Docling as an extra.

### Proposed Approach

1. Pin pdfplumber, pypdfium2, OCRmyPDF, Tesseract bindings, openpyxl, Docling extra
2. Health check module
3. Smoke tests: bbox from born-digital PDF, OCR box from a rendered page, XLSX cell, ISIN check digit

### Risks & Follow-ups

See `docs/adr/0003-document-extraction-and-ocr.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [x] #1 `python -m pce.extraction.toolchain` lists all required engines as ok
- [x] #2 Tests prove bbox / OCR box / sheet+cell provenance on synthetic input
- [x] #3 uv.lock contains no pymupdf

## Implementation Notes

## Outcome

- **Status**: completed
- backend/pyproject.toml + uv.lock: pdfplumber 0.11.10, pypdfium2 5.15.0, pypdf 7.0.0, OCRmyPDF 17.13.0, pytesseract 0.3.13, openpyxl 3.1.5, xlrd 2.0.2, pandas 3.1.1, python-stdnum 2.2; Docling 2.148.0 as extra; PaddleOCR 3.7.0 as `vlm` extra (not installed)
- System: Tesseract 5.3.4 with eng/ita/deu/fra, Ghostscript, qpdf, Poppler (scripts/bootstrap.sh for macOS and Debian/Ubuntu)
- `python -m pce.extraction.toolchain` health check; 9 tests in backend/tests/test_toolchain.py

## Issues Encountered

- PyMuPDF is AGPL-3.0: removed, including transitively (uv.lock has no pymupdf).
- `import ocrmypdf` monkeypatches pdfminer globally and blanks standard-font text: OCRmyPDF must run as a subprocess; canary test added.
- PyTorch CPU index unreachable from this sandbox; Linux docling install pulls CUDA wheels (~6 GB). Documented in docs/SETUP.md.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-pd19xu | b2d585f | 2026-11-06 | chore: multi-agent dev protocol, backlog and extraction toolchain |
| claude/project-thread-pd19xu | 22eb579 | 2026-11-06 | fix(infra): release claims with a commit, not a branch delete |
| claude/project-thread-pd19xu | c9a6b3a | 2026-11-06 | fix(infra): skip push gate on backlog-only pushes |
