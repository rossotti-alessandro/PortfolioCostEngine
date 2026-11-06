---
id: SC-7.2
title: Tariff calculator: tiers, minimums, caps, proration, FX
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
parent_task_id: SC-7
priority: P0
paths_owned:
  - "backend/src/pce/finance/tariffs/**"
  - "backend/tests/unit/finance/tariffs/**"
spec_ref: docs/research/FEE_TAXONOMY.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Compute custody, advisory and brokerage charges from a tariff exactly as banks bill them.

## Description

### Context

No calculator.

### User Flow Impact

Contractual fees appear when a statement lacks them, labelled contractual.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Marginal vs whole-base tiers
2. Min/max per period
3. Day-count proration
4. Dated FX
5. Jurisdiction and validity checks

### Risks & Follow-ups

See `docs/research/FEE_TAXONOMY.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Golden cases for each tier type match hand calculations to the centime
- [ ] #2 Luxembourg tariff on Swiss booking is rejected

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
