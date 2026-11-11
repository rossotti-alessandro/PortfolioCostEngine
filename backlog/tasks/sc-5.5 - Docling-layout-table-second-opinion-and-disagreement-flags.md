---
id: SC-5.5
title: Docling layout/table second opinion and disagreement flags
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
  - SC-9.1
parent_task_id: SC-5
priority: P1
paths_owned:
  - "backend/src/pce/extraction/docling/**"
  - "backend/tests/integration/docling/**"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs:
  - ".claude/rules/extraction.md"
---

> **One-liner**: Use Docling on complex tables and flag cells where it disagrees with pdfplumber.

## Description

### Context

Single engine.

### User Flow Impact

Fewer silent table errors; disagreements go to review.

### Performance / Efficiency Impact

Docling adds seconds per page; run only on pages with tables.

### Proposed Approach

1. Adapter behind a feature flag
2. Cell-level comparison
3. Evaluation on the golden corpus

### Risks & Follow-ups

See `docs/adr/0003-document-extraction-and-ocr.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Disagreeing cell produces needs_review with both values
- [ ] #2 Gate still passes without the docling extra installed

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
