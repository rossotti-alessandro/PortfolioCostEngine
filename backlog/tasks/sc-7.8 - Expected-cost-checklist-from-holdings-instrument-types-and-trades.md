---
id: SC-7.8
title: Expected-cost checklist from holdings, instrument types and trades
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
dependencies:
  - SC-7.7
parent_task_id: SC-7
priority: P0
paths_owned:
  - "backend/src/pce/analysis.py"
  - "backend/src/pce/finance/checklist.py"
  - "backend/tests/test_checklist.py"
spec_ref: docs/research/COST_PROTOCOL.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: List every cost that must exist for what the family holds and does, so missing costs show as unknown instead of disappearing.

## Description

### Context

analysis.py:38 SERVICE_CORE expects only service, custody and brokerage per bank. Fund transaction costs (when a KID lacks them), structured product costs, FX margin, stamp duty, VAT and cash interest are never created as UNKNOWN, so LedgerSummary.is_complete can be true while whole layers are unexamined.

### User Flow Impact

The coverage figure and the at-least wording become honest. Implicit rows (FX margin, spreads) appear in their own block and do not change the totals.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. New finance/checklist.py: rules per account, per instrument type, per transaction and per cash balance (COST_PROTOCOL.md step 6).
2. analysis.py creates UNKNOWN atoms for unmatched rows, with the document that would resolve each.
3. Implicit rows get materiality minor until SC-7.14 can estimate them, and are reported in a separate implicit block.

### Risks & Follow-ups

More unknowns on existing prospects; UI copy must explain the implicit block. Finance semantics: Ale's approval before merge.

## Acceptance Criteria

- [ ] #1 A fund with a KID that omits transaction costs yields FUND_TRANSACTION unknown
- [ ] #2 A portfolio with foreign-currency positions yields FX_MARGIN unknown in the implicit block
- [ ] #3 Totals of the synthetic demo prospects unchanged

## Implementation Notes

## Outcome

## Issues Encountered
