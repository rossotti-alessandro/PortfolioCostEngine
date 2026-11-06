---
id: SC-8.3
title: Review split screen with PDF evidence viewer
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
  - SC-5.1
parent_task_id: SC-8
priority: P0
paths_owned:
  - "frontend/src/routes/review/**"
  - "frontend/src/components/source-viewer/**"
spec_ref: docs/design/DESIGN_SYSTEM.md
rule_refs:
  - ".claude/rules/frontend.md"
---

> **One-liner**: Let the analyst check every extracted value against the highlighted source and approve or correct it.

## Description

### Context

No review.

### User Flow Impact

Click a value: PDF opens at the page with the box highlighted; accept/edit/reject with audit.

### Performance / Efficiency Impact

Page render < 500 ms.

### Proposed Approach

1. PDF.js viewer with overlay
2. Review table with keyboard
3. Corrections create revisions

### Risks & Follow-ups

See `docs/design/DESIGN_SYSTEM.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Clicking a fee opens the correct page and highlights its bbox (e2e)
- [ ] #2 Correction keeps the original value in history

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
