---
id: SC-7.17
title: Repeated fee lines summed, SP entry cost shown as one-off
status: Done
assignee: []
owner: "Audit cost categories for consistency"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-6oi8gs"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/80"
created_date: "2026-11-26 00:35"
updated_date: "2026-11-26 00:51"
labels:
  - finance
dependencies: []
parent_task_id: SC-7
priority: P0
paths_owned:
  - "backend/src/pce/analysis.py"
  - "backend/src/pce/finance/scenarios.py"
  - "backend/tests/test_repeated_fees.py"
  - "backend/tests/test_sp_entry_cost.py"
  - "frontend/src/pages/Costs.tsx"
  - "frontend/src/pages/Pipeline.tsx"
  - "frontend/src/components/Trace.tsx"
  - "frontend/src/lib/it.ts"
spec_ref: docs/research/FEE_TAXONOMY.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Two fee lines of one kind in a cost report no longer crash the analysis, a second report from the same bank never adds up twice, and a structured product's entry cost is a one-off instead of a yearly charge.

## Description

### Context

Cost-category audit (2026-11-26). In `analysis.py` every `fee_observed` line became atom
`cur:<bank>:<code>`. A second line with the same code ("Custody fee" and "Custody surcharge") or a second
cost report from the same bank raised `InclusionGraphError` and the whole analysis failed.
`product_atoms` in `finance/scenarios.py` creates `SP_ENTRY_COST` with the default `recurring=True`, so an
issuer margin paid once (fee table: `one_off`, FEE_TAXONOMY "one-off costs are shown separately") was
added to the annual total every year.

Ale approved both rules on 2026-11-26 00:09Z (decision card "Approve both as proposed"): same-kind lines
in one report are added; with two reports from one bank only the latest 12 months count; SP entry cost is
shown as a one-off, outside the annual total.

### User Flow Impact

Cost reports with sub-lines or several years analyse instead of failing; portfolios with structured
products no longer show the entry margin as a yearly cost (lower current total, smaller apparent saving).

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Fee-report loop: documents latest `period_end` first; lines of one report grouped by code and summed
   (formula lists the lines); a second report for the same period corroborates (counted once, mismatch
   flagged by the ledger); an older period is skipped with an info check.
2. `product_atoms`: `SP_ENTRY_COST` atoms are `recurring=False`, so the ledger puts them in
   `one_off_known`.

### Risks & Follow-ups

Two accounts at one bank with separate reports for the same period would now count once and be flagged
as a mismatch for review (safer than double counting). Cash debits from two statements of different
quarters still corroborate rather than add; follow-up if seen on real files.

## Acceptance Criteria

- [x] #1 Two lines with one code in one report are summed into one counted atom
- [x] #2 Two reports for the same period count once; a mismatch raises a warning
- [x] #3 With reports for two years only the latest counts, with an info check
- [x] #4 SP_ENTRY_COST with a disclosed rate is a one-off: in one_off_known, not in total_known
- [x] #5 Existing finance tests stay green

## Implementation Notes

`analysis.py` and `scenarios.py` were shared with SC-7.16 (thread "Cover costs for every asset type") by agreement: this story owns the fee-report loop and the SP_ENTRY_COST line in `product_atoms`; SC-7.16 owns holdings, lots and KID joins. Merged main after SC-7.16 before touching `product_atoms`. The UI needed a label for the existing ledger role `one_off` (Costs, Trace, Pipeline; EN and IT).

## Outcome

- **Status**: completed
- Fee-report loop sums same-code lines, runs reports latest period first, a same-period copy corroborates, older periods are skipped with an info check. `SP_ENTRY_COST` is `recurring=False`. Tests: `test_repeated_fees.py` (4) and `test_sp_entry_cost.py` (1), each failing on main. Full backend suite green.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-6oi8gs | 541fc01 | 2026-11-26 | Same-code lines summed, one report per period |
| claude/project-thread-6oi8gs | 8a5389d | 2026-11-26 | UI label for one-off costs |
| claude/project-thread-6oi8gs | aa21fbf | 2026-11-26 | SP entry cost is a one-off |
