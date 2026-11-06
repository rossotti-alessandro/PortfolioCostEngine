---
id: SC-8.2
title: Prospects list and intake screen
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
  - SC-3.3
  - SC-4.1
parent_task_id: SC-8
priority: P0
paths_owned:
  - "frontend/src/routes/prospects/**"
  - "frontend/src/routes/intake/**"
spec_ref: docs/research/UX_RECOMMENDATIONS.md
rule_refs:
  - ".claude/rules/frontend.md"
---

> **One-liner**: Let an analyst create an analysis and upload a prospect's documents with a live checklist.

## Description

### Context

No UI.

### User Flow Impact

Drop files, see classification and what is missing.

### Performance / Efficiency Impact

Uploads stream with progress.

### Proposed Approach

1. Prospect list
2. New analysis form with consent
3. Drop zone + checklist from 4.2

### Risks & Follow-ups

See `docs/research/UX_RECOMMENDATIONS.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Upload of the synthetic set shows each file classified and the checklist updated
- [ ] #2 Unsupported file shows the reason

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
