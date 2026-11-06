---
id: SC-8.8
title: Prospect CRM pipeline and conversion funnel
status: Done
assignee: []
owner: "Add prospect CRM and conversion funnel"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-ms8qbh"
pr: ""
created_date: "2026-11-06 15:35"
updated_date: "2026-11-06 15:38"
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
  - "frontend/tests/e2e/crm.spec.ts"
  - "frontend/vitest.config.ts"
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

- [x] #1 Create, edit and move a contact between stages; every move is recorded with user and time
- [x] #2 Funnel endpoint returns per-stage reached counts, step conversion, overall win rate, lost reasons, median days in stage
- [x] #3 Tenant isolation: another tenant sees no contacts and gets 404 on ids
- [x] #4 CRM payloads never contain internal margin fields
- [x] #5 Pipeline, contact and funnel pages render the synthetic seed; E2E test covers create → move → won → funnel updates

## Implementation Notes

- Shared touch points agreed with the demo thread (2026-11-06): `backend/src/pce/api.py` (import + `app.include_router(crm_router)`),
  `frontend/src/main.tsx` (`...crmRoutes`), `frontend/src/components/Shell.tsx` (one nav entry "Clients & pipeline").
- `frontend/vitest.config.ts` added so vitest skips `tests/e2e/**` (Playwright specs share the `*.spec.ts` pattern).
  A `test` block in `vite.config.ts` does not type-check with vitest 2.1 + vite 6, hence the separate file.
- `@playwright/test` is added to `frontend/package.json` by the demo thread (its E2E suite); `crm.spec.ts` was run
  locally against 1.63.0 with backend on :8000 and Vite on :5173.

## Outcome

- Backend `pce.crm`: contacts, append-only stage events, activities, link/create cost review, funnel, synthetic seed (41 contacts).
- Funnel: reached per stage (furthest stage, lost included), step conversion, drop-off, win rate, lead-to-client,
  median days per stage and to win, lost reasons by stage, conversion by source, open AUM per stage (unknown counted, not 0).
- UI: board (drag or menu to move), contacts list (prospects / clients / lost), contact page (stage tracker, history,
  activities, next action, cost review link), funnel page (chart + table twin, filters by cohort, owner, source).
- CRM is the home page (`/` → `/crm`, first nav entry). The contact page drills into the linked cost review:
  key figures, the five workflow steps with progress, and one "Continue: <next step>" CTA. `GET /api/crm/by-prospect/{pid}`
  for the review breadcrumbs. The CRM seed also seeds the P-1042 cost review with its documents.
- Tests: 11 backend (`tests/test_crm.py`), 2 vitest, 5 Playwright E2E (`tests/e2e/crm.spec.ts`), all passing. Gate passed.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-ms8qbh | 70f7540 | 2026-11-06 | feat(api): CRM contacts, stage history and conversion funnel |
| claude/project-thread-ms8qbh | 6511adc | 2026-11-06 | feat(ui): CRM pipeline board, contact page and conversion funnel |
| claude/project-thread-ms8qbh | 395dc46 | 2026-11-06 | feat(ui): pipeline as home page, cost review drill-down |
