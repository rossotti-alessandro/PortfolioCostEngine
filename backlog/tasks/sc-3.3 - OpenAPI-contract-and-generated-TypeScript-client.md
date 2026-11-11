---
id: SC-3.3
title: OpenAPI contract and generated TypeScript client
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
  - data
  - ui
dependencies:
  - SC-3.1
parent_task_id: SC-3
priority: P0
paths_owned:
  - "backend/src/pce/api/**"
  - "frontend/src/api/**"
spec_ref: docs/adr/0001-stack.md
rule_refs: []
---

> **One-liner**: Make the API the single contract between backend and frontend, with types generated, not hand-copied.

## Description

### Context

No API.

### User Flow Impact

Frontend shows only what the API returns; money arrives as strings.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. FastAPI routers per resource
2. `openapi-typescript` generation script
3. CI check that the generated client is up to date

### Risks & Follow-ups

See `docs/adr/0001-stack.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Changing a Pydantic field without regenerating fails the gate
- [ ] #2 Money fields are strings in the OpenAPI schema

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
