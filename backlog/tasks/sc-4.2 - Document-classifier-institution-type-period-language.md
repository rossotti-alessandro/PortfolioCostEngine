---
id: SC-4.2
title: Document classifier: institution, type, period, language
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
  - intake
  - extraction
dependencies:
  - SC-4.1
  - SC-2.1
parent_task_id: SC-4
priority: P0
paths_owned:
  - "backend/src/pce/intake/classify/**"
  - "backend/tests/unit/classify/**"
spec_ref: docs/research/DOCUMENT_TAXONOMY.md
rule_refs:
  - ".claude/rules/extraction.md"
---

> **One-liner**: Know what each upload is so the right parser runs and the missing-documents checklist is accurate.

## Description

### Context

No classification.

### User Flow Impact

Each file shows a type chip (e.g. 'UBS CH · Annual cost report · 2025') the analyst can correct.

### Performance / Efficiency Impact

Rule-based first: keywords and layout cues on page 1-2; no model call.

### Proposed Approach

1. Rules from document_types.csv
2. Booking entity and jurisdiction detection
3. Period and valuation date
4. Unknown → review

### Risks & Follow-ups

See `docs/research/DOCUMENT_TAXONOMY.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Synthetic samples of each top-6 type classify correctly
- [ ] #2 Unrecognised document is 'unknown', never forced into a type

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
