---
id: SC-6.1
title: ISIN validation and instrument resolver (local catalog first)
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
  - instruments
dependencies:
  - SC-3.1
parent_task_id: SC-6
priority: P0
paths_owned:
  - "backend/src/pce/instruments/**"
  - "backend/tests/unit/instruments/**"
  - "data/catalog/**"
spec_ref: docs/research/FEE_TAXONOMY.md
rule_refs:
  - ".claude/rules/extraction.md"
  - ".claude/rules/privacy.md"
---

> **One-liner**: Identify each holding's exact instrument and share class without leaking the portfolio.

## Description

### Context

No resolver.

### User Flow Impact

Each position shows its instrument, share class and resolution status.

### Performance / Efficiency Impact

Local lookup; external calls batched, ISIN only.

### Proposed Approach

1. stdnum ISIN check
2. Local catalog (import of the fund list)
3. Optional OpenFIGI identity lookup, ISIN only
4. Unresolved state with reason

### Risks & Follow-ups

See `docs/research/FEE_TAXONOMY.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Invalid check digit rejected
- [ ] #2 Name-only match never resolves a share class
- [ ] #3 No request body contains quantities or values (test on the client)

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
