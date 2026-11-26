---
id: SC-7.21
title: Cost edge-case matrix and fixes for bad periods and negative fees
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-26 10:05"
updated_date: "2026-11-26 10:05"
labels:
  - finance
dependencies: []
parent_task_id: SC-7
priority: P1
paths_owned:
  - "backend/src/pce/analysis.py"
  - "backend/tests/test_cost_edge_cases.py"
spec_ref: docs/research/COST_PROTOCOL.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Test every asset class, currency, period and document edge case end to end, and stop bad periods, negative fee lines and structured products without an ISIN from distorting the total.

## Description

### Context

Probing `analyse()` with synthetic packs (2026-11-26) found four ways the all-in cost goes wrong while the
view still reports itself complete:

1. A cost report whose end date is before its start date (an OCR or extraction slip) is annualised by a
   negative day count: every fee turns negative and the total drops below zero.
2. A cost report covering a single day (or a few days) is annualised × 365/days: CHF 900 of fees on a
   CHF 100'000 portfolio became CHF 346'750.
3. A negative fee line (a refund, a reversal or a misread minus) is counted as a negative cost and lowers
   the total.
4. A structured product without a checksum-valid ISIN gets no product-cost atom at all: its embedded cost
   is a silent zero and the view says it is complete.

### User Flow Impact

The analyst no longer sees impossible totals. Each case becomes a visible check, and an amount that cannot
be trusted is an unknown, not a number.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Period end before start: period unknown, amounts not annualised, `fail` check.
2. Period shorter than 28 days: not annualised; the reported amount is a lower bound with a `warn` check.
3. A fee code whose lines sum below zero in a report or a cash-debit pool: not counted; UNKNOWN atom plus
   a `fail` check asking the analyst to confirm refund or misread.
4. STRUCTURED holdings are always a product-cost gap, like funds and ETFs.
5. An end-to-end matrix (`tests/test_cost_edge_cases.py`) pinning every asset class, multi-currency,
   partial periods, duplicates, missing KIDs, performance fees and the ledger invariants.

### Risks & Follow-ups

Changes finance semantics (rules 1-4): Ale's per-PR approval. The 28-day threshold is a proposal.

## Acceptance Criteria

- [ ] #1 Reversed cost-report period gives no negative fee and a fail check
- [ ] #2 A 1-day report is not annualised; counted as reported with a lower-bound warning
- [ ] #3 A negative fee total is an unknown with a fail check, never a negative cost
- [ ] #4 A structured product without ISIN is an unknown product cost
- [ ] #5 Matrix covers equity, bond, ETF, fund share classes, structured, derivative, commodity, cash; CHF/EUR/USD with and without printed rates; partial periods; duplicates; missing KIDs; performance fees

## Implementation Notes

## Outcome

## Issues Encountered
