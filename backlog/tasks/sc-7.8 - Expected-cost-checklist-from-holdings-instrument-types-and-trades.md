---
id: SC-7.8
title: Expected-cost checklist from holdings, instrument types and trades
status: "Done"
assignee: []
owner: "Design complete portfolio cost protocol"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-7crdzy"
pr: ""
created_date: "2026-11-25 20:50"
updated_date: "2026-11-25 23:59"
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
  - "docs/research/COST_PROTOCOL.md"
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

- [x] #1 A fund with a KID that omits transaction costs yields FUND_TRANSACTION unknown
- [x] #2 A portfolio with foreign-currency positions yields FX_MARGIN unknown in the implicit block
- [x] #3 Totals of the synthetic demo prospects unchanged

## Implementation Notes

- Owned paths as listed, plus docs/research/COST_PROTOCOL.md (decisions and gap status).
- Scope kept small: only product gaps become ledger atoms (FUND_TRANSACTION when the KID is silent). FX margin,
  spreads and transaction taxes go to `hidden_costs` (finance/checklist.py), never to the ledger, per Ale's
  2026-11-25 decision. No typical ranges yet: they need recorded sources (SC-7.14). Cash drag waits for its
  taxonomy row (SC-2.5).

## Outcome

- **Status**: completed
- New tests in `backend/tests/test_checklist.py` (2 of 4 fail on main, all pass here); full backend suite green.
- Totals unchanged: unknown atoms and hidden rows add nothing. `is_complete` turns false for funds whose KID
  omits transaction costs, which is the point.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-7crdzy | 7d93d59 | 2026-11-25 | Product gaps as unknowns, hidden_costs block, tests |
