---
id: SC-7.9
title: Use the bank's ex-post product cost when KIDs are missing
status: "In Progress"
assignee: []
owner: "Design complete portfolio cost protocol"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-7crdzy"
pr: ""
created_date: "2026-11-25 20:50"
updated_date: "2026-11-26 00:09"
labels:
  - finance
dependencies:
  - SC-7.8
parent_task_id: SC-7
priority: P1
paths_owned:
  - "backend/src/pce/analysis.py"
  - "backend/tests/test_expost_fallback.py"
spec_ref: docs/research/COST_PROTOCOL.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: When the bank's own cost report states product costs, use it to fill missing KIDs instead of leaving the biggest layer blank.

## Description

### Context

analysis.py:921 reads reported_product_costs only to reconcile against the KID-based estimate. If no KID is uploaded, product costs stay UNKNOWN although the bank states a figure for the same period.

### User Flow Impact

Fewer unknowns on EU-booked accounts, where the ex-post report is mandatory.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Create a portfolio-level FUND_ONGOING-type atom per institution from the reported figure (status estimated, tier T4).
2. Per-ISIN KID atoms of that institution become its children (included_in) so the total equals the bank figure or the KID sum, never both.
3. Keep the reconciliation check; flag when the KID sum exceeds the bank figure.

### Risks & Follow-ups

Bank figures may cover different periods or scopes; period alignment comes with SC-7.10.

## Acceptance Criteria

- [ ] #1 Prospect with ex-post report and no KIDs: product cost known at bank figure, not unknown
- [ ] #2 Prospect with both: counted once, reconciliation warning when they differ over 5%

## Implementation Notes

## Outcome

## Issues Encountered
