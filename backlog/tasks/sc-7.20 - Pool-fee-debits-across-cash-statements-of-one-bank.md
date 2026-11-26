---
id: SC-7.20
title: Pool fee debits across cash statements of one bank
status: "In Progress"
assignee: []
owner: "Audit cost categories for consistency"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-6oi8gs"
pr: ""
created_date: "2026-11-26 01:12"
updated_date: "2026-11-26 01:11"
labels:
  - finance
dependencies:
  - SC-7.17
parent_task_id: SC-7
priority: P1
paths_owned:
  - "backend/src/pce/analysis.py"
  - "backend/tests/test_analysis_debits.py"
spec_ref: docs/research/FEE_TAXONOMY.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Four quarterly cash statements from one bank give the observed yearly fee, instead of the first quarter counting and the others only "confirming" it.

## Description

### Context

The cash-debit loop in `analysis.py` worked per statement: the first statement of a bank created atom
`cur:<bank>:<code>` and every later statement for the same fee became a corroborating atom of it. Four
quarterly statements of CHF 500 custody debits gave CHF 2,000 by extrapolating Q1 and flagged three
"mismatches" when quarters differed; two quarters were annualised from one quarter only.

Ale chose on 2026-11-26 01:02Z (decision card "Pool them over the days covered"): debits from statements of
different periods are added and annualised over all days covered; a statement repeating the same period
counts once.

### User Flow Impact

Several statements of one bank give one debit line per fee, observed when they cover a full year.

### Performance / Efficiency Impact

No measurable impact (a set of dates per fee and bank).

### Proposed Approach

1. Pool debits by (bank, fee code) across cash statements; a statement whose period is already in the
   pool is skipped with an info check.
2. Annualise the pool: stated frequency first, else over the union of days the periods cover (overlaps
   are not counted twice), else the flagged lower bound when any period is unknown.
3. A cost report for the bank still wins: the pooled figure corroborates it.

### Risks & Follow-ups

Two accounts at one bank with statements for the same period would now count once (flagged by the info
check) rather than twice.

## Acceptance Criteria

- [ ] #1 Four quarterly statements of CHF 500 give CHF 2,000 observed, one counted atom
- [ ] #2 Two consecutive quarters are annualised over the 181 days both cover
- [ ] #3 A statement repeating a period counts once, with an info check
- [ ] #4 Existing SC-7.7 debit tests stay green

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
