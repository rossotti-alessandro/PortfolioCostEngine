---
id: SC-7.1
title: Fee ledger and inclusion graph (no double counting)
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
  - SC-3.1
parent_task_id: SC-7
priority: P0
paths_owned:
  - "backend/src/pce/finance/ledger/**"
  - "backend/tests/unit/finance/ledger/**"
spec_ref: docs/research/FEE_TAXONOMY.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Store every cost as an evidenced atom and sum only what is not already included elsewhere.

## Description

### Context

Kit had a reference fee_engine.py with no inclusion graph persistence.

### User Flow Impact

Cost totals are trustworthy and explainable line by line.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Atom store keyed by economic event
2. Inclusion and replacement edges
3. Totals as 'at least X + unknowns'

### Risks & Follow-ups

See `docs/research/FEE_TAXONOMY.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 AMF-in-OCF and wrap-replaces-custody property tests
- [ ] #2 Report-vs-cash duplicate collapses to one atom with two evidences
- [ ] #3 Unknown never becomes 0 in any total

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
