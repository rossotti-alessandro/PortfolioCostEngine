---
id: SC-7.14
title: Implicit costs: FX margin, spreads and cash drag estimates
status: "In Progress"
assignee: []
owner: "Compute every portfolio cost end to end"
model: "claude-opus-5-5"
progress: 5
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
  - "backend/tests/unit/finance/test_implicit.py"
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

- [ ] #1 FX confirmation at 1.0850 vs reference 1.0800 on 100k gives 500 implicit cost
- [ ] #2 No FX confirmations: FX margin unknown, range labelled
- [ ] #3 Implicit box never changes the headline totals

## Implementation Notes

## Outcome

## Issues Encountered
