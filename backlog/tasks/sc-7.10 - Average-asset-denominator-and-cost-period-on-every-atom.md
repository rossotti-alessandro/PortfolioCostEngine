---
id: SC-7.10
title: Average-asset denominator and cost period on every atom
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-25 20:50"
updated_date: "2026-11-25 20:50"
labels:
  - finance
dependencies: []
parent_task_id: SC-7
priority: P1
paths_owned:
  - "backend/src/pce/finance/ledger.py"
  - "backend/src/pce/finance/scenarios.py"
  - "backend/src/pce/analysis.py"
  - "backend/tests/unit/finance/**"
spec_ref: docs/research/COST_PROTOCOL.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Compute product costs on average holding value, use the bank's printed average assets, and record the period and denominator on every cost.

## Description

### Context

scenarios.py:192 multiplies the current value by the annual rate although FEE_TAXONOMY.md specifies average value x rate x days/365. parsers.py:619 extracts meta:average_assets but analysis never uses it. FeeAtom has no period_start/period_end or denominator type.

### User Flow Impact

bps figures stay correct when assets moved during the year; the analyst sees which base each rate was applied to.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Add period_start, period_end and basis_kind to FeeAtom.
2. Average value from start and end statements when both exist, else end value with a note.
3. Use average_assets for the bps denominator when printed.

### Risks & Follow-ups

Pinned demo totals use end value; update them in the same PR with a note. Finance formulas: Ale's approval.

## Acceptance Criteria

- [ ] #1 Test: holding 800k at start and 1m at end with 1% TER gives 9000
- [ ] #2 Test: bps uses printed average assets when present
- [ ] #3 Every atom in the report payload carries its period

## Implementation Notes

## Outcome

## Issues Encountered
