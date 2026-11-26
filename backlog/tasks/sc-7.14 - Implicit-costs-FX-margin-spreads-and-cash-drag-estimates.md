---
id: SC-7.14
title: Cash drag range and hidden-cost box beside the totals
status: "In Progress"
assignee: []
owner: "Compute every portfolio cost end to end"
model: "claude-opus-5-5"
progress: 90
branch: "claude/project-thread-p3z1fq"
pr: ""
created_date: "2026-11-25 20:50"
updated_date: "2026-11-26 11:27"
labels:
  - finance
dependencies:
  - SC-7.8
  - SC-7.11
  - SC-7.12
parent_task_id: SC-7
priority: P2
paths_owned:
  - "backend/src/pce/finance/implicit.py"
  - "backend/src/pce/finance/checklist.py"
  - "backend/src/pce/analysis.py"
  - "backend/src/pce/api.py"
  - "backend/src/pce/report.py"
  - "backend/tests/test_implicit.py"
  - "backend/tests/test_checklist.py"
  - "frontend/src/pages/Costs.tsx"
  - "frontend/src/lib/it.ts"
  - "frontend/src/lib/types.ts"
spec_ref: docs/research/COST_PROTOCOL.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Estimate FX margin, spreads and cash drag only from trade data and reference rates, and keep them out of the headline totals.

## Description

### Context

FX_MARGIN and BID_ASK_SPREAD exist in the taxonomy (L6) but nothing estimates them; cash drag has no category. These are often the largest hidden costs for active or cash-heavy portfolios.

### User Flow Impact

A separate implicit-cost box with method, data and range; never mixed into proven or estimated totals.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. FX margin = (applied rate - reference mid on trade date) x amount, from FX confirmations.
2. Spread = half quoted spread x traded amount when quote data exists.
3. Cash drag = (reference rate - credited rate) x average cash.
4. Without data: unknown with a labelled typical range.

### Risks & Follow-ups

Reference rates are external data (ISIN-free). Typical ranges need sources in SOURCE_REGISTER.md. Ale's approval for finance semantics.

## Acceptance Criteria

- [ ] #1 FX confirmation at 1.0850 vs reference 1.0800 on 100k gives 500 implicit cost (moved to SC-7.23)
- [x] #2 No FX confirmations: FX margin listed as not estimated, with the document that would estimate it
- [x] #3 Implicit box never changes the headline totals
- [x] #4 USD 50'000 cash (CHF 45'000) with SOFR 12-month average 3.7883% gives a cash drag range 0 to 1'704.74

## Implementation Notes

- Ale's decision (card, 2026-11-26 10:29Z, "Cash drag range now, trades next"): cash drag as a range now;
  FX margin, spreads and stamp duty from parsed transaction lists later (SC-7.18 then SC-7.23).
- Range without assumptions: the credited rate is between 0 and the benchmark, so the yearly cost is between
  0 and benchmark x cash. Benchmarks: SARON, ESTR, SOFR, SONIA, TONA, monthly averages from the SNB data
  portal cube `zimoma` (one host, already approved for SNB rates; no NY Fed needed), averaged over the 12
  months up to the valuation date. Negative benchmark (SARON 2025-26) gives no drag.
- Cash at the statement date stands in for the year's average cash (said in the row note).
- `analysis` output gains `hidden_range` {low, high, estimated, not_estimated}; Costs page shows it as a
  folded row "Hidden costs, not in the total"; the client PDF prints one line. Totals and scenarios are
  byte-identical with and without the range (test).

## Outcome

## Issues Encountered
