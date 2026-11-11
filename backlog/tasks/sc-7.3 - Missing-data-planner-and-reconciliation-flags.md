---
id: SC-7.3
title: Missing-data planner and reconciliation flags
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
  - finance
dependencies:
  - SC-7.1
  - SC-4.2
parent_task_id: SC-7
priority: P0
paths_owned:
  - "backend/src/pce/validation/**"
  - "backend/tests/unit/validation/**"
spec_ref: docs/research/DOCUMENT_TAXONOMY.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Tell the analyst which documents are missing, ranked by how much cost they leave undetermined.

## Description

### Context

No gap detection.

### User Flow Impact

Gaps panel and a ready-to-send document request letter.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Expected cost categories per account type
2. Coverage metric
3. Materiality ranking
4. Request letter text (it/de/en)

### Risks & Follow-ups

See `docs/research/DOCUMENT_TAXONOMY.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Positions-only upload asks for fee statement and mandate, and shows no verified total
- [ ] #2 Coverage % matches categories evidenced / expected

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
