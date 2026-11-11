---
id: SC-8.5
title: Compare scenarios screen
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
  - SC-7.4
parent_task_id: SC-8
priority: P0
paths_owned:
  - "frontend/src/routes/compare/**"
spec_ref: docs/research/UX_RECOMMENDATIONS.md
rule_refs:
  - ".claude/rules/frontend.md"
---

> **One-liner**: Show current vs Safe Capital proposal side by side with honest caveats.

## Description

### Context

No compare.

### User Flow Impact

Edit proposal tariff, see annual and first-year saving and payback.

### Performance / Efficiency Impact

Recompute < 200 ms via API.

### Proposed Approach

1. Scenario cards
2. Editable tariff form
3. Comparability badge and caveats

### Risks & Follow-ups

See `docs/research/UX_RECOMMENDATIONS.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Changed-holdings saving is never labelled a fee saving
- [ ] #2 Scenario history persists across reload

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
