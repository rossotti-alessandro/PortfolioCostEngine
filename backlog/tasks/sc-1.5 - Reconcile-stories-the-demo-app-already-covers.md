---
id: SC-1.5
title: Reconcile stories the demo app already covers
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-12 21:05"
updated_date: "2026-11-12 21:05"
labels:
  - process
dependencies: []
parent_task_id: SC-1
priority: P1
paths_owned:
  - "backlog/tasks/sc-3.*.md"
  - "backlog/tasks/sc-4.*.md"
  - "backlog/tasks/sc-5.1 - *.md"
  - "backlog/tasks/sc-5.2 - *.md"
  - "backlog/tasks/sc-5.4 - *.md"
  - "backlog/tasks/sc-6.*.md"
  - "backlog/tasks/sc-7.*.md"
  - "backlog/tasks/sc-8.[1-7] - *.md"
  - "backlog/tasks/sc-9.2 - *.md"
  - "backlog/tasks/sc-9.3 - *.md"
  - "backlog/tasks/sc-1.3 - *.md"
  - "backlog/tasks/sc-10.2 - *.md"
spec_ref: backlog/TEMPLATE.md
rule_refs: [".claude/rules/task-lifecycle.md"]
---

> **One-liner**: Make the board tell the truth: about 30 stories say To Do although main already implements
> most of them, so SC-3.1 and SC-8.1 show as "ready to claim" for work that exists.

## Description

### Context

The demo app (PR #5) was built before story claims existed. SC-1.3, 3.x, 4.x, 5.1, 5.2, 5.4, 6.1, 7.1 to 7.5,
8.1 to 8.7, 9.2, 9.3 and 10.2 still say To Do. A new agent could rebuild existing code. HANDOFF.md (PR #11)
lists the drift but does not fix it. SC-2.1/2.2 are closed by PR #12 and SC-10.1 by PR #11.

### User Flow Impact

None in the app; the board and "ready to claim" list become reliable.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. For each story read the code and tests on main; tick the criteria that are met, citing test names.
2. Done where every criterion is met; otherwise rescope the story to the real gap.
3. Regenerate the board on main after merge.

### Risks & Follow-ups

Rescoping is a coordinator call; list any story whose scope changes in the PR.

## Acceptance Criteria

- [ ] #1 Each listed story is Done with test evidence or rescoped to a stated remaining gap
- [ ] #2 backlog-lint passes and `--ready` lists no story whose work already exists on main

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
