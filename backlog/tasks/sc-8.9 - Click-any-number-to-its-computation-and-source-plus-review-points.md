---
id: SC-8.9
title: Click any number to its computation and source, plus review points
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-11 19:20"
updated_date: "2026-11-11 19:20"
labels:
  - ui
  - api
dependencies: []
parent_task_id: SC-8
priority: P0
paths_owned:
  - "backend/src/pce/api.py"
  - "backend/src/pce/review_points.py"
  - "backend/tests/unit/test_review_points.py"
  - "backend/tests/test_trace.py"
  - "frontend/src/components/**"
  - "frontend/src/pages/Costs.tsx"
  - "frontend/src/pages/Compare.tsx"
  - "frontend/src/lib/**"
spec_ref: docs/research/UX_RECOMMENDATIONS.md
rule_refs:
  - ".claude/rules/frontend.md"
  - ".claude/rules/finance.md"
  - ".claude/rules/privacy.md"
---

> **One-liner**: An analyst clicks any result number, sees the computation that produced it, then the exact page and box in the source file, and gets a ranked list of points to review.

## Description

### Context

The cost ledger rows open a dialog with the formula and the highlighted source, but the headline numbers
(known total, debited, inside products, layer totals, comparison saving) are not clickable, the dialog finds
the source by fetching every document's facts, and anomalies are spread across the checks list.

### User Flow Impact

Result → computation (the counted lines that make it up, unknowns listed apart, linked items shown not added)
→ line (formula, inputs, status) → source (page with the box highlighted, snippet, engine, confidence,
review status). A "Points to review" panel ranks what an analyst should look at first. Sections on the cost
page can be shown or hidden per analyst.

### Performance / Efficiency Impact

One less round of N document fact fetches per click: provenance arrives inline with the analysis.

### Proposed Approach

1. `api.compute`: attach inline `evidence` (fact id, document, page, bbox, sheet/cell, snippet, engine,
   confidence, review status) to every atom.
2. `review_points.py`: pure function over the analysis + facts that returns ranked review points
   (low confidence, unreviewed source of a counted cost, corrected values, cost from list price or estimate,
   single large driver, rate outside review thresholds, failed or warning checks, not determined items).
3. Frontend `TraceDialog`: breadcrumb levels result → computation → line → source; make KPIs, layer rows
   and comparison figures clickable.
4. Costs page: "Points to review" panel and a "Customise view" menu (sections shown, stored per browser).

### Risks & Follow-ups

- Review thresholds are heuristics for attention, not market data; they are labelled so.
- Extraction thread's `review` object on facts (needs_review + reasons) is consumed when present.

## Acceptance Criteria

- [ ] #1 Every headline number on Costs and Compare opens its computation, and every line opens its source page with the box highlighted.
- [ ] #2 Review points are computed server-side and tested (unit tests per rule).
- [ ] #3 Internal margin never appears in the trace or review payloads (existing client-safe test still green).
- [ ] #4 Existing pinned P-1042 totals unchanged.

## Implementation Notes

## Outcome

- **Status**:

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
