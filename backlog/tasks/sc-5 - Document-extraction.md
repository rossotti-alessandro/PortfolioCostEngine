---
id: SC-5
title: Document extraction
status: To Do
assignee: []
created_date: "2026-11-06 15:05"
updated_date: "2026-11-06 15:05"
labels:
  - epic
  - extraction
dependencies: []
priority: P0
---

> **One-liner**: Positions, cash and fee lines from PDFs, scans and spreadsheets, each with evidence.

Status and progress are computed from the stories by `scripts/backlog-board.mjs`.

## Stories

- SC-5.1 Born-digital PDF: words, lines and tables with bbox
- SC-5.2 Scanned pages: OCR branch via OCRmyPDF subprocess
- SC-5.3 Spreadsheets and CSV with sheet+cell provenance
- SC-5.4 Bank statement adapters: positions, cash, fee lines (synthetic first)
- SC-5.5 Docling layout/table second opinion and disagreement flags
- SC-5.6 Local VLM benchmark (PaddleOCR-VL or similar) with adapter
