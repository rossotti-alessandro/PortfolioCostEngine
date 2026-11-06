---
id: SC-7.5
title: Internal contribution margin (analyst-only)
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
  - SC-7.4
parent_task_id: SC-7
priority: P1
paths_owned:
  - "backend/src/pce/finance/internal/**"
  - "backend/tests/unit/finance/internal/**"
spec_ref: docs/adr/0004-privacy-local-first.md
rule_refs:
  - ".claude/rules/finance.md"
  - ".claude/rules/privacy.md"
---

> **One-liner**: Show Safe Capital what the prospect would earn them, without it ever reaching the client.

## Description

### Context

No margin view.

### User Flow Impact

Internal page only.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Revenue minus acquisition and operating cost assumptions
2. Separate endpoint with role check

### Risks & Follow-ups

See `docs/adr/0004-privacy-local-first.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Client report payload and PDF contain no margin fields (test)
- [ ] #2 Endpoint refuses non-internal role

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
