---
id: SC-7.4
title: Scenarios: current, same holdings, changed holdings, first year, payback
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
  - SC-7.2
parent_task_id: SC-7
priority: P0
paths_owned:
  - "backend/src/pce/scenarios/**"
  - "backend/tests/unit/scenarios/**"
spec_ref: docs/research/FEE_TAXONOMY.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Compare today's all-in cost with a Safe Capital proposal honestly and reproducibly.

## Description

### Context

No scenarios.

### User Flow Impact

Compare screen with annual and first-year savings, payback and comparability caveats.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Editable proposal tariff
2. Same-holdings vs changed-holdings separation
3. One-off costs and payback
4. Versioned snapshots

### Risks & Follow-ups

See `docs/research/FEE_TAXONOMY.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Synthetic demo case: current, same-holdings, changed-holdings, first-year and payback match a hand calculation committed next to the test
- [ ] #2 Negative saving shown as negative

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
