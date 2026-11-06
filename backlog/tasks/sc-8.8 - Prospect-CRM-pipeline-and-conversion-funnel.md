---
id: SC-8.8
title: Prospect CRM pipeline and conversion funnel
status: "In Progress"
assignee: []
owner: "Add prospect CRM and conversion funnel"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-ms8qbh"
pr: ""
created_date: "2026-11-06 15:35"
updated_date: "2026-11-06 15:24"
labels:
  - ui
  - api
dependencies: []
parent_task_id: SC-8
priority: P1
paths_owned:
  - "backend/src/pce/crm/**"
  - "backend/tests/test_crm*.py"
  - "frontend/src/pages/crm/**"
spec_ref: docs/design/DESIGN_SYSTEM.md
rule_refs:
  - ".claude/rules/frontend.md"
  - ".claude/rules/privacy.md"
  - ".claude/rules/testing.md"
---

> **One-liner**: Let a wealth manager track leads, prospects and clients through a pipeline and see how many convert.

## Description

### Context

Ale asked (2026-11-06) for the tool to work as a light CRM: create potential clients and clients, and
see a funnel analysis of how many prospects convert. FeeLens already has a cost-review `prospect`
record (SC-8.2 / demo thread); the CRM sits beside it and links to it, it does not change it.

### User Flow Impact

New "Pipeline" area: a board of contacts by stage (Lead → Qualified → Documents received → Cost review
→ Proposal sent → Won / Lost), a contact page with stage history and next action, and a funnel page with
stage-to-stage conversion, win rate, time per stage, lost reasons and AUM by stage.

### Performance / Efficiency Impact

Funnel metrics are computed in one pass over stage events; fine for thousands of contacts on SQLite.

### Proposed Approach

1. Own package `pce.crm` (tables prefixed `crm_`), APIRouter mounted at `/api/crm`, tenant-scoped like the rest of the API.
2. Stage changes are append-only events, so the funnel is computed from history, not from current state.
3. Synthetic seed of about 40 contacts (all labelled SYNTHETIC) for the demo.
4. Frontend pages under `frontend/src/pages/crm/**`, design-system tokens only.

### Risks & Follow-ups

- Personal data: names in the seed are synthetic. Real use needs the privacy rules (ADR 0004) and consent.
- No internal margin or Safe Capital revenue appears in the CRM payloads (tested).

## Acceptance Criteria

- [ ] #1 Create, edit and move a contact between stages; every move is recorded with user and time
- [ ] #2 Funnel endpoint returns per-stage reached counts, step conversion, overall win rate, lost reasons, median days in stage
- [ ] #3 Tenant isolation: another tenant sees no contacts and gets 404 on ids
- [ ] #4 CRM payloads never contain internal margin fields
- [ ] #5 Pipeline, contact and funnel pages render the synthetic seed; E2E test covers create → move → won → funnel updates

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
