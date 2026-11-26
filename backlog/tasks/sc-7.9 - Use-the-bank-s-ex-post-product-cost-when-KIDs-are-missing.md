---
id: SC-7.9
title: Use the bank's ex-post product cost when KIDs are missing
status: "Done"
assignee: []
owner: "Design complete portfolio cost protocol"
model: "claude-opus-5-5"
progress: 100
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

- [x] #1 Prospect with ex-post report and no KIDs: product cost known at bank figure, not unknown
- [x] #2 Prospect with both: counted once, reconciliation warning when they differ over 5%

## Implementation Notes

- Owned paths as listed, plus docs/research/COST_PROTOCOL.md (gap 4 status).
- Changed from the proposed approach: KID figures (tier T3) outrank the bank aggregate (tier T4), so they stay
  counted. Only the part of the bank figure they do not explain is added, as one residual atom
  `cur:<bank>:PRODUCT_REPORTED`. If the KIDs already explain the whole bank figure, nothing is added and the
  gaps stay unknown (a parent equal to the bank figure would have cut CHF 450 of KID-evidenced cost from the
  P-1042 demo).
- The residual exists only in the current cost picture. Comparison scenarios keep per-holding product costs,
  so it can create no saving.
- Unknown product atoms the residual covers stay visible with materiality `minor`, so the cost can read complete.

## Outcome

- **Status**: completed
- `backend/tests/test_expost_fallback.py`: 6 tests, 3 fail on main, all pass here. P-1042 gold totals unchanged.
- Existing reconciliation check (KID sum vs bank figure, warn over 5%) kept.

## Issues Encountered

- `make_synthetic_isin` keeps only 10 characters of the seed, so "EXPOST0001" and "EXPOST0002" collided.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-7crdzy | 3e9f4d6 | 2026-11-26 | Residual from the bank product-cost figure, tests |
