---
id: SC-7.7
title: Sum repeated fee debits per period before annualising
status: "In Progress"
assignee: []
owner: "Prove and raise accuracy on realistic portfolios"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-12ht53"
pr: ""
created_date: "2026-11-25 20:50"
updated_date: "2026-11-25 21:15"
labels:
  - finance
  - bug
dependencies: []
parent_task_id: SC-7
priority: P0
paths_owned:
  - "backend/src/pce/analysis.py"
  - "backend/tests/test_analysis_debits.py"
spec_ref: docs/research/COST_PROTOCOL.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Four quarterly custody debits must give the annual custody fee, not one quarter of it labelled observed.

## Description

### Context

analysis.py:508-509 builds one atom id per institution and fee code; the second and later debits of the same fee become corroborating atoms and are not added. When the text lacks a quarter word, periods_per_year is None and the single debit is counted as an observed annual amount. Reproduced 2026-11-25 with a synthetic cash statement: 4 x CHF 500 custody debits give CHF 500 observed.

### User Flow Impact

Annual bank costs from cash statements stop being under-counted up to 4x.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Group cash debits by institution, fee code and statement period; sum them.
2. Annualise the sum by days covered by the statement (365/days); if the period is unknown, keep the sum as a lower bound with a note, not a plain observed annual figure.
3. Keep corroboration against the annual cost report on the summed amount.

### Risks & Follow-ups

Changes current totals on documents with repeated debits; demo P-1042 pinned totals must be re-checked. Finance-adjacent: ask Ale before merge.

## Acceptance Criteria

- [ ] #1 Test: 4 debits of 500 in a 12-month statement give 2000 annual
- [ ] #2 Test: one debit with unknown period is flagged as a lower bound
- [ ] #3 Existing corroboration test (debits x4 equal report) stays green

## Implementation Notes

## Outcome

## Issues Encountered
