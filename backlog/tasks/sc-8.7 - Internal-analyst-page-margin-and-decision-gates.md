---
id: SC-8.7
title: Internal analyst page: margin and decision gates
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
  - SC-7.5
  - SC-8.1
parent_task_id: SC-8
priority: P1
paths_owned:
  - "frontend/src/routes/internal/**"
spec_ref: docs/adr/0004-privacy-local-first.md
rule_refs:
  - ".claude/rules/frontend.md"
  - ".claude/rules/privacy.md"
---

> **One-liner**: Give Safe Capital the commercial view in a separate, clearly internal screen.

## Description

### Context

No internal view.

### User Flow Impact

Margin and go/no-go gates; insufficient evidence blocks a verdict.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Separate layout and route guard
2. Insufficient-evidence gate

### Risks & Follow-ups

See `docs/adr/0004-privacy-local-first.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Route not reachable from the client report
- [ ] #2 Insufficient evidence shows 'cannot decide' instead of a verdict

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
