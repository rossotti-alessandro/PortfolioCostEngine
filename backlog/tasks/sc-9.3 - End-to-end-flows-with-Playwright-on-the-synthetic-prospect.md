---
id: SC-9.3
title: End-to-end flows with Playwright on the synthetic prospect
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
  - qa
  - ui
dependencies:
  - SC-8.3
  - SC-8.4
  - SC-8.6
parent_task_id: SC-9
priority: P0
paths_owned:
  - "frontend/tests/e2e/**"
spec_ref: docs/design/DESIGN_SYSTEM.md
rule_refs:
  - ".claude/rules/testing.md"
---

> **One-liner**: Guard the full upload → review → costs → compare → report flow with screenshots.

## Description

### Context

No e2e.

### User Flow Impact

No direct change.

### Performance / Efficiency Impact

Suite < 3 minutes.

### Proposed Approach

1. Seeded prospect
2. Flows with screenshots under artifacts/e2e/<ts>/

### Risks & Follow-ups

See `docs/design/DESIGN_SYSTEM.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Full flow passes headless in the gate
- [ ] #2 Screenshots show the SYNTHETIC watermark

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
