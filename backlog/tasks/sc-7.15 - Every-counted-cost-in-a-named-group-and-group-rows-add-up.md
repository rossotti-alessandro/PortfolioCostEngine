---
id: SC-7.15
title: Every counted cost in a named group, and group rows add up
status: Done
assignee: []
owner: "Audit cost categories for consistency"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-6oi8gs"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/78"
created_date: "2026-11-26 00:12"
updated_date: "2026-11-26 00:25"
labels:
  - finance
  - report
dependencies: []
parent_task_id: SC-7
priority: P1
paths_owned:
  - "frontend/src/pages/Costs.tsx"
  - "backend/src/pce/finance/scenarios.py"
  - "backend/src/pce/report.py"
  - "backend/tests/test_cost_groups.py"
  - "frontend/src/pages/Report.tsx"
  - "frontend/src/pages/Compare.tsx"
  - "frontend/src/lib/format.ts"
spec_ref: docs/research/FEE_TAXONOMY.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Third-party trading fees go to "Trading & FX" as the fee table says, and the client report, Report page and Compare page show every group that holds money, so their rows add up to the total.

## Description

### Context

Cost-category audit (2026-11-26). `LAYER_BY_CODE` in `finance/scenarios.py` maps 12 of the 44 codes in
`data/taxonomy/fee_taxonomy.csv`. The extractor emits `THIRD_PARTY_TRADING` ("Fremde Spesen", "spese di
terzi", exchange and regulatory fees), which has no entry, so it lands in layer `other`. The ledger counts
it in `total_known`, but the PDF client report (`report.py` `LAYER_NAMES`), `Report.tsx` and `Compare.tsx`
list only L1, L2, L3, L4, L5 and L9. Reproduced: rows add to CHF 14,500 under a total of CHF 14,800.

### User Flow Impact

The client sees group rows that add up to the total, and exchange fees under "Trading & FX".

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. `LAYER_BY_CODE` gains every billed code of the fee table with layer L1-L3 and L9 (the codes the
   bank-fee paths can emit), with the layer the table gives.
2. A test asserts every L1-L10 code of the table maps to its table layer, so the two cannot drift again.
3. `report.py` `LAYER_NAMES` and the two pages list every layer (L1-L10 and other) and show a row
   only when it holds money or an unknown, as `Costs.tsx` already does.

### Risks & Follow-ups

No formula change: the mapping follows the existing taxonomy. Repeated fee lines with one code (crash)
and structured-product entry cost counted every year are a separate finance story pending Ale's OK.

## Acceptance Criteria

- [x] #1 A cost report with "Fremde Spesen" counts it under L3, and no counted atom has layer `other`
- [x] #2 Every L1-L10 code in fee_taxonomy.csv present in `LAYER_BY_CODE` has the table's layer
- [x] #3 PDF group rows sum to "Total known" when a cost sits outside the six usual groups
- [x] #4 Existing finance and report tests stay green

## Implementation Notes

Also owns `frontend/src/pages/Costs.tsx` (uses the shared `LAYER_ORDER`). PDF layer names now match the app ("Taxes on fees & trades", since L9 holds stamp duty and foreign transaction tax too).

## Outcome

- **Status**: completed
- `LAYER_BY_CODE` covers the 19 billed codes of the fee table; `report.py` `LAYER_NAMES` and `LAYER_ORDER` in `format.ts` list every layer. Four tests in `backend/tests/test_cost_groups.py` (three failed on main). Full backend suite green.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-6oi8gs | 44c36da | 2026-11-26 | LAYER_BY_CODE follows the fee table; every layer in report and pages |
