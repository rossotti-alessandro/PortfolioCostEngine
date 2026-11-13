---
id: SC-5.20
title: Read several uploaded documents at once, with progress per file
status: "In Progress"
assignee: []
owner: "Validate accuracy and speed up processing"
model: "claude-opus-5-5"
progress: 5
branch: "claude/sc-5.20-parallel-documents"
pr: ""
created_date: "2026-11-13 13:11"
updated_date: "2026-11-13 13:12"
labels:
  - extraction
  - backend
  - ui
dependencies: []
parent_task_id: SC-5
priority: P1
paths_owned:
  - "backend/src/pce/extraction/documents.py"
  - "backend/src/pce/extraction/layout.py"
  - "backend/src/pce/extraction/verify.py"
  - "backend/src/pce/api.py"
  - "backend/tests/unit/extraction/test_documents.py"
  - "frontend/src/pages/Documents.tsx"
  - "frontend/src/lib/it.ts"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs: [".claude/rules/extraction.md"]
---

> **One-liner**: A prospect pack of 20 to 30 files is read several documents at a time instead of one
> after the other, and the upload list shows each file waiting, reading and done.

## Description

### Context
SC-5.11 (PR #21) OCRs the scanned pages of one document in parallel. Documents themselves are still read
one at a time: the Documents page sends one request per file and waits for each before sending the next,
and each request runs `extract()` in the API thread. Born-digital reading (pdfplumber, finder, verify)
is pure Python, so threads alone would not run it in parallel, and pdfium is not thread-safe.

### User Flow Impact
The analyst drops the whole pack; several rows show "reading" at once and finish in any order.

### Performance / Efficiency Impact
Measured on a SYNTHETIC 29-file pack (P-1042 and P-2077, each PDF also as an image-only scan), 4 cores:
see Outcome. Render free (1 CPU) keeps the old path: one worker, no extra process.

### Proposed Approach
1. `pce.extraction.documents.extract`: same signature as `parsers.extract`; runs it in a process pool
   sized `PCE_DOC_WORKERS`, else the CPU quota (`layout.ocr_workers()`); inline when that is 1.
2. One cross-process Tesseract limit (`layout.ocr_slot()`), so several documents never start more OCR
   processes than cores: a lone 50-page scan still uses every core for its pages.
3. `api.ingest` calls it; the Documents page sends up to 3 files at once and keeps per-file progress.

### Risks & Follow-ups
- Not a durable queue: a restart during an upload loses that request, as today. SC-5.15 stays open for that.
- Memory: one Python process per worker (about 150 MB each) on top of the API.

## Acceptance Criteria

- [ ] #1 The 29-file SYNTHETIC pack gives identical facts sequentially and in parallel, and is faster in parallel (measured, before/after in Outcome)
- [ ] #2 One worker (Render free) runs inline with no pool; existing pipeline and API tests pass

## Implementation Notes

## Outcome

- **Status**:

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
