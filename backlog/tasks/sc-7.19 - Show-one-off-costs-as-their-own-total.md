---
id: SC-7.19
title: Show one-off costs as their own total
status: Done
assignee: []
owner: "Audit cost categories for consistency"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-6oi8gs"
pr: ""
created_date: "2026-11-26 01:05"
updated_date: "2026-11-26 01:02"
labels:
  - report
  - ui
dependencies:
  - SC-7.17
parent_task_id: SC-7
priority: P2
paths_owned:
  - "backend/src/pce/report.py"
  - "backend/tests/test_one_off_total.py"
  - "frontend/src/pages/Costs.tsx"
  - "frontend/src/lib/it.ts"
spec_ref: docs/research/FEE_TAXONOMY.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Costs paid once (a structured product's entry margin) appear as "Paid once, not in the annual total" on the Costs page and in the client PDF, instead of vanishing.

## Description

### Context

SC-7.17 made `SP_ENTRY_COST` a one-off, so it moved from `total_known` to `one_off_known`. No view printed
`one_off_known`, so the cost no longer appeared in any total (only as a labelled line in the atom list).

### User Flow Impact

The analyst and the client see the one-off amount next to the annual figures, clearly outside them.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Costs page answer card: a row "Paid once, not in the annual total" when `one_off_known` > 0, clickable
   to its lines (role `one_off`).
2. Client PDF: one line with the same words after the layer table, EN and IT.

### Risks & Follow-ups

No formula change.

## Acceptance Criteria

- [x] #1 A structured product with a 2% entry margin gives one_off_known 2,000 and no annual cost
- [x] #2 The client PDF prints "Paid once, not in the annual total" when one_off_known > 0
- [x] #3 Existing report tests stay green

## Implementation Notes

## Outcome

- **Status**: completed
- Costs answer card row and PDF line, EN and IT. Two tests in `backend/tests/test_one_off_total.py` (the PDF one fails on main).

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-6oi8gs | d9cc22e | 2026-11-26 | One-off total on Costs page and client PDF |
