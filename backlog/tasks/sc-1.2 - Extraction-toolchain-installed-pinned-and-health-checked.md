---
id: SC-1.2
title: Extraction toolchain installed, pinned and health-checked
status: In Progress
assignee: []
owner: "Set up multi-agent dev protocol"
model: "claude-opus-5-5"
progress: 90
branch: "claude/project-thread-pd19xu"
pr: ""
created_date: "2026-11-06 15:05"
updated_date: "2026-11-06 15:05"
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

- [ ] #1 `python -m pce.extraction.toolchain` lists all required engines as ok
- [ ] #2 Tests prove bbox / OCR box / sheet+cell provenance on synthetic input
- [ ] #3 uv.lock contains no pymupdf

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
