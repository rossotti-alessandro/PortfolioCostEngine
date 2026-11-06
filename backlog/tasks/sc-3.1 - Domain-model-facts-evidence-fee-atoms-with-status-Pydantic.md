---
id: SC-3.1
title: Domain model: facts, evidence, fee atoms with status (Pydantic)
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
  - data
dependencies: []
parent_task_id: SC-3
priority: P0
paths_owned:
  - "backend/src/pce/domain/**"
  - "backend/src/pce/errors.py"
  - "backend/tests/unit/domain/**"
spec_ref: docs/research/FEE_TAXONOMY.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Define the typed shapes every other story exchanges, so evidence and missing states survive end to end.

## Description

### Context

Kit had a SQL sketch only; no typed contract.

### User Flow Impact

No direct change; every number shown later carries status and source because the type requires it.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Evidence (pdf page+bbox / sheet+cell / url+anchor)
2. Document, Account, Instrument, Position, CashMovement
3. FeeAtom with status enum, basis, Decimal amount|None, parent atom
4. Scenario and result types; ClientReport type without margin fields

### Risks & Follow-ups

See `docs/research/FEE_TAXONOMY.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Constructing a non-unknown FeeAtom without evidence raises
- [ ] #2 Unknown amount is None and serialises as null, never 0
- [ ] #3 ClientReport schema has no internal-margin field (test)

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
