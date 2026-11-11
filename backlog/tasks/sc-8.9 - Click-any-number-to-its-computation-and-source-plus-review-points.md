---
id: SC-8.9
title: Click any number to its computation and source, plus review points
status: "Done"
assignee: []
owner: "Trace numbers back to source documents"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-6txgxv"
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
  - "backend/tests/test_api.py"
  - "backend/tests/test_review_points.py"
  - "frontend/tests/e2e/feelens.spec.ts"
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

- [x] #1 Every headline number on Costs and Compare opens its computation, and every line opens its source page with the box highlighted.
- [x] #2 Review points are computed server-side and tested (unit tests per rule).
- [x] #3 Internal margin never appears in the trace or review payloads (existing client-safe test still green).
- [x] #4 Existing pinned P-1042 totals unchanged.

## Implementation Notes

- Provenance is attached in `api.compute` (not in `finance/`), so no engine formula changed; P-1042 totals
  are unchanged (pinned tests green).
- A product cost's inputs are the KID rate fact and the statement holding fact (role `basis`); converted
  amounts also carry the printed FX rate fact (role `fx_rate`).
- Review wording lives in the frontend (`ReviewPoints.tsx`) so it is translated; the API sends `kind` + vars.
- Optional fields from the extraction strategy thread (`review`, `row_bbox`, `label_bbox`, `region`) are
  passed through when present; `review.status == needs_review` becomes an `extraction_flag` point.

## Outcome

- **Status**: completed
- Every headline number on Costs and Compare opens result → computation → line → source page with the box.
- Ranked Points to review panel (9 rules, unit tested), check sources clickable, Customise view menu.
- E2E test 11 drives the whole trace on P-1042 and writes screenshots 11–15 to artifacts/e2e/screens.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-6txgxv | b8ce801 | 2026-11-11 | Inline provenance per cost line and ranked review points |
| claude/project-thread-6txgxv | f2ebd64 | 2026-11-11 | Trace dialog, review points panel, customise view, e2e |
