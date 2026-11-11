---
id: SC-5.2
title: Scanned pages: OCR branch via OCRmyPDF subprocess
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
  - SC-5.1
parent_task_id: SC-5
priority: P0
paths_owned:
  - "backend/src/pce/extraction/ocr/**"
  - "backend/tests/integration/ocr/**"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs:
  - ".claude/rules/extraction.md"
---

> **One-liner**: Read scanned or photographed statements with the same evidence guarantees as digital ones.

## Description

### Context

No OCR path.

### User Flow Impact

Scans work; low-confidence words are flagged for review.

### Performance / Efficiency Impact

OCR ~2-5 s per page; runs as a background job with progress.

### Proposed Approach

1. Detect pages without text layer
2. ocrmypdf CLI subprocess with eng+ita+deu+fra, --skip-text
3. Re-run 5.1 on the OCRed PDF; carry OCR confidence

### Risks & Follow-ups

See `docs/adr/0003-document-extraction-and-ocr.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 A rendered (image-only) synthetic page yields the same amounts as the digital one
- [ ] #2 No process imports ocrmypdf (canary test still passes)

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
