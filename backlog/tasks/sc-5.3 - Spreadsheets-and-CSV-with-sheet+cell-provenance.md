---
id: SC-5.3
title: Spreadsheets and CSV with sheet+cell provenance
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
  - "backend/src/pce/extraction/sheets/**"
  - "backend/tests/unit/extraction/sheets/**"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs:
  - ".claude/rules/extraction.md"
---

> **One-liner**: Import position lists and fee tables from Excel/CSV with the cell each value came from.

## Description

### Context

No sheet reader.

### User Flow Impact

Clicking a value opens the sheet at that cell.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Header detection, merged cells, formulas read as values with formula text kept
2. CSV dialect and decimal sniffing

### Risks & Follow-ups

See `docs/adr/0003-document-extraction-and-ocr.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Elenco_Fondi-style sheet imports ISINs with sheet+cell
- [ ] #2 Formula cells keep both value and formula

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
