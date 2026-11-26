---
id: SC-7.17
title: Repeated fee lines summed, SP entry cost shown as one-off
status: "In Progress"
assignee: []
owner: "Audit cost categories for consistency"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-6oi8gs"
pr: ""
created_date: "2026-11-26 00:35"
updated_date: "2026-11-26 00:31"
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

- [ ] #1 Two lines with one code in one report are summed into one counted atom
- [ ] #2 Two reports for the same period count once; a mismatch raises a warning
- [ ] #3 With reports for two years only the latest counts, with an info check
- [ ] #4 SP_ENTRY_COST with a disclosed rate is a one-off: in one_off_known, not in total_known
- [ ] #5 Existing finance tests stay green

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
