---
id: SC-8.4
title: Cost dashboard: totals, layers, drivers, gaps
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
  - ui
dependencies:
  - SC-8.1
  - SC-7.1
  - SC-7.3
parent_task_id: SC-8
priority: P0
paths_owned:
  - "frontend/src/routes/costs/**"
spec_ref: docs/research/UX_RECOMMENDATIONS.md
rule_refs:
  - ".claude/rules/frontend.md"
---

> **One-liner**: Show the all-in cost with coverage, by layer and driver, and what is still unknown.

## Description

### Context

No dashboard.

### User Flow Impact

Headline cost + coverage meter, waterfall, top drivers, gaps panel.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Headline + CoverageMeter
2. CostWaterfall with table twin
3. Top drivers
4. Gaps panel → request letter

### Risks & Follow-ups

See `docs/research/UX_RECOMMENDATIONS.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 No headline total renders without the coverage meter
- [ ] #2 Unknown layer is hatched with label, not a zero bar

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
