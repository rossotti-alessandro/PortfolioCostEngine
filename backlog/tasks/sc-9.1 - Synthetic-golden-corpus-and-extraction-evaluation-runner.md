---
id: SC-9.1
title: Synthetic golden corpus and extraction evaluation runner
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
  - qa
dependencies:
  - SC-5.1
parent_task_id: SC-9
priority: P0
paths_owned:
  - "backend/tests/evaluation/**"
  - "data/synthetic/golden/**"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs:
  - ".claude/rules/testing.md"
---

> **One-liner**: Measure extraction accuracy per field so engine choices are made on evidence.

## Description

### Context

No corpus.

### User Flow Impact

No direct change; quality numbers in every extraction PR.

### Performance / Efficiency Impact

Runs in minutes on a laptop.

### Proposed Approach

1. Generated synthetic statements with labels (digital + image-only + hard negatives)
2. Metrics: exact amount, ISIN, date, row association, bbox IoU, abstention
3. Report under artifacts/eval/<ts>/

### Risks & Follow-ups

See `docs/adr/0003-document-extraction-and-ocr.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Runner produces report.md with per-field metrics
- [ ] #2 A deliberately wrong extractor scores lower (sanity check)

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
