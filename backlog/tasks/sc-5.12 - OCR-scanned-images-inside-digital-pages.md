---
id: SC-5.12
title: OCR scanned images embedded inside born-digital pages
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-12 14:30"
updated_date: "2026-11-12 14:30"
labels:
  - extraction
dependencies:
  - SC-5.11
parent_task_id: SC-5
priority: P2
paths_owned:
  - "backend/src/pce/extraction/layout.py"
  - "backend/tests/test_embedded_scans.py"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs:
  - ".claude/rules/extraction.md"
  - ".claude/rules/finance.md"
---

> **One-liner**: A fee table pasted into a PDF as a picture is read instead of silently skipped.

## Description

### Context
`read_pdf` routes a whole page to OCR only when its text layer has fewer than 25 characters. A
born-digital page with a header and footer in text but a fee table pasted as an image (common in
annual cost reports and scanned annexes merged into digital PDFs) goes to the text reader, which never
sees the table. Those fees are missed without any warning.

### User Flow Impact
Fees inside embedded pictures appear as OCR values with the same review rules as other OCR values
(engine `tesseract-ocr`, confidence, `needs_review` where verification fails). Pages where this happened
say so in the processing view.

### Performance / Efficiency Impact
Only images larger than a size threshold and not overlapped by text are OCR'd; cost is one Tesseract call
per such image, on the SC-5.11 worker pool.

### Proposed Approach
1. Detect large image objects on digital pages (`page.images`) with no text chars inside their box.
2. OCR the image region (rendered from the page, so masks and rotation are applied) and merge the lines
   into the page with engine `tesseract-ocr` and their real confidence.
3. Test on a SYNTHETIC page: text header plus a fee table as an image; the fees are found and flagged
   for review like other OCR values.

### Risks & Follow-ups
- Logos and charts are images too: size and "no text inside" filters, plus nothing becomes a total
  without review.

## Acceptance Criteria

- [ ] #1 SYNTHETIC digital page with an image-only fee table yields those fees with OCR evidence
- [ ] #2 No change on the synthetic corpora and ocrbench pages without embedded tables (`python -m pce.evaluation`)

## Implementation Notes

## Outcome

- **Status**: 

## Issues Encountered
