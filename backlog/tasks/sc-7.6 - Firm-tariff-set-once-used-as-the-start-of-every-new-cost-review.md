---
id: SC-7.6
title: Firm tariff set once, used as the start of every new cost review
status: "In Progress"
assignee: []
owner: "Build FeeLens proposal for Massimo"
model: "claude"
progress: 100
branch: "claude/sc-7.6-firm-tariff"
pr: ""
created_date: "2026-11-13 12:05"
updated_date: "2026-11-13 11:56"
labels:
  - scenarios
  - ui
dependencies: []
parent_task_id: SC-7
priority: P0
paths_owned:
  - backend/src/pce/api.py
  - backend/src/pce/db.py
  - backend/tests/test_firm_tariff.py
  - frontend/src/pages/FirmTariff.tsx
  - frontend/src/pages/Compare.tsx
  - frontend/src/components/ProposalForm.tsx
  - frontend/src/components/Shell.tsx
  - frontend/src/main.tsx
  - frontend/src/lib/api.ts
  - frontend/src/lib/it.ts
  - frontend/tests/e2e/feelens.spec.ts
spec_ref: docs/research/FEE_TAXONOMY.md
rule_refs: [".claude/rules/finance.md", ".claude/rules/frontend.md"]
---

> **One-liner**: Safe Capital enters its own fee schedule once; every new cost review starts from it instead of the synthetic demo defaults.

## Description

### Context
Every new prospect copies `demo.spec.PROPOSAL_DEFAULTS` (the synthetic Safe Capital tariff) into its proposal.
The only way to enter the real tariff is the "Proposal inputs" editor on each prospect's Compare page, so an
analyst must retype the firm's prices for every review, and a forgotten edit silently compares against
invented prices.

### User Flow Impact
A senior opens "Firm tariff" from the account menu, enters the management fee bands, custody, brokerage, FX
margin and VAT once, and saves. New cost reviews start from these prices; the Compare page editor still
adjusts one prospect. Analysts can read the firm tariff but not change it.

### Performance / Efficiency Impact
No measurable impact: one small row per firm.

### Proposed Approach
1. `db.FirmSettings` (tenant_id primary key, proposal JSON, updated_by, updated_at); `create_all` adds the table.
2. `GET /api/firm/tariff` (any signed-in user) and `PUT /api/firm/tariff` (senior only, validated with the
   same checks as the prospect proposal, audited). Only tariff keys are stored; per-prospect estimates
   (turnover, FX volume, migration, product swaps) stay per prospect.
3. `create_prospect` starts from `PROPOSAL_DEFAULTS` overlaid with the firm tariff. The synthetic demo seed
   keeps the pinned defaults.
4. Frontend: the Compare editor's form becomes `ProposalForm`, reused by a new `FirmTariff` page linked from
   the account menu; EN and IT strings.

### Risks & Follow-ups
- Existing prospects keep their saved proposal; there is no bulk re-apply (follow-up if wanted).

## Acceptance Criteria

- [x] #1 A senior saves the firm tariff; a prospect created afterwards has those prices in its proposal (test).
- [x] #2 An analyst cannot change the firm tariff (403) and another firm never sees it (test).
- [x] #3 Invalid inputs are refused with 422 and nothing is saved (test).
- [x] #4 The synthetic demo totals pinned in test_pipeline.py are unchanged.
- [x] #5 The page works in English and Italian.

## Implementation Notes

- Paths as declared, plus `frontend/src/lib/i18n` strings in `it.ts` only.
- `check_proposal` is the prospect proposal's existing validation, moved into a function so both endpoints share it;
  it now also refuses non-numeric text with 422 (it raised a 500 before).
- Firm tariff keys: firm name, custodian, fee bands and method, VAT, custody, custody minimum, brokerage, FX margin,
  internal costs. Turnover, FX volume, migration costs and product swaps stay per prospect.
- `finance/` untouched: the firm tariff only changes the inputs a new prospect starts from.

## Outcome

- **Status**: completed
- Tests: `backend/tests/test_firm_tariff.py` (4 tests: new review uses saved tariff; analyst 403, other firm isolated,
  internal hidden from analysts; invalid input 422 and nothing saved; prospect-only keys not stored). E2E
  `12 firm tariff` (senior saves custody minimum in the UI, a new prospect's proposal carries it). Full E2E 18/18.
- Synthetic demo totals unchanged (`test_pipeline.py` pinned figures pass; the demo seed keeps the spec defaults).

## Branch & Commits

- `claude/sc-7.6-firm-tariff`

## Issues Encountered

- None.
