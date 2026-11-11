---
id: SC-5.1
title: Born-digital PDF: words, lines and tables with bbox
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-06 15:05"
updated_date: "2026-11-06 15:05"
labels:
  - extraction
dependencies:
  - SC-3.1
  - SC-4.1
parent_task_id: SC-5
priority: P0
paths_owned:
  - "backend/src/pce/extraction/pdf/**"
  - "backend/tests/unit/extraction/pdf/**"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs:
  - ".claude/rules/extraction.md"
---

> **One-liner**: Turn text-layer PDFs into rows and cells that keep their exact page coordinates.

## Description

### Context

Toolchain only.

### User Flow Impact

Review screen can highlight the exact rectangle of every value.

### Performance / Efficiency Impact

Target < 1 s per page on a laptop.

### Proposed Approach

1. pdfplumber words/lines; table finder with explicit settings
2. Locale-aware number parsing (1'234.50, 1.234,50)
3. Evidence objects in PDF points, top-left origin

### Risks & Follow-ups

See `docs/adr/0003-document-extraction-and-ocr.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Synthetic 3-page statement: every amount extracted with page and bbox inside the page
- [ ] #2 Swiss and German number formats parse to the same Decimal

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
