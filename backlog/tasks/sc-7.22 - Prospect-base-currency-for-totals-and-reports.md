---
id: SC-7.22
title: Prospect base currency for totals and reports
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-26 10:30"
updated_date: "2026-11-26 10:30"
labels:
  - finance
dependencies:
  - SC-7.11
parent_task_id: SC-7
priority: P2
paths_owned:
  - "backend/src/pce/analysis.py"
  - "backend/src/pce/report.py"
  - "frontend/src/**"
spec_ref: docs/research/COST_PROTOCOL.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Total and report a prospect in its own base currency (EUR, USD) instead of always CHF.

## Description

### Context

Split from SC-7.11. `analysis.py` fixes `BASE_CCY = "CHF"` while `Prospect.base_ccy` exists, and labels,
the PDF report and the frontend print CHF. An Italian client of a Lugano manager may think in EUR.

### User Flow Impact

A EUR prospect sees EUR totals; every converted figure names its rate.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Read the base from the prospect; printed rates into that base win, else the ECB cross rate (SC-7.11).
2. Replace hard-coded CHF labels in analysis, report and frontend with the base currency.

### Risks & Follow-ups

Wide UI surface; proposal tariffs are in CHF and need conversion for a EUR prospect.

## Acceptance Criteria

- [ ] #1 EUR base prospect totals in EUR with reference cross rates
- [ ] #2 CHF prospects unchanged (pinned demo totals)

## Implementation Notes

## Outcome

## Issues Encountered
