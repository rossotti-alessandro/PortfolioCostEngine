---
id: SC-7.23
title: FX margin, spreads and stamp duty from transaction lists
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-26 10:45"
updated_date: "2026-11-26 10:45"
labels:
  - finance
dependencies:
  - SC-7.18
  - SC-7.14
parent_task_id: SC-7
priority: P1
paths_owned:
  - "backend/src/pce/finance/implicit.py"
  - "backend/src/pce/finance/checklist.py"
  - "backend/tests/test_implicit.py"
spec_ref: docs/research/COST_PROTOCOL.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Measure the FX margin, spreads and stamp duty a portfolio paid from its transaction list, and show them in the hidden-cost range.

## Description

### Context

Split from SC-7.14 (Ale, 2026-11-26: "Cash drag range now, trades next"). These costs depend on trading,
so they need the transactions SC-7.18 reads.

### User Flow Impact

The hidden-cost box fills with measured FX margins and taxes instead of "not estimated".

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. FX margin = (applied rate - ECB reference on the trade date) x amount, signed by direction.
2. Spread = half quoted spread x traded amount when quotes exist; else not estimated.
3. Swiss stamp duty from trade value and security domicile (rates to verify in SOURCE_REGISTER).

### Risks & Follow-ups

Stamp duty rates and split need a verified source. Ale's approval for finance semantics.

## Acceptance Criteria

- [ ] #1 FX confirmation at 1.0850 vs reference 1.0800 on 100k gives 500 implicit cost
- [ ] #2 No trades: rows stay "not estimated" with the document that would estimate them

## Implementation Notes

## Outcome

## Issues Encountered
