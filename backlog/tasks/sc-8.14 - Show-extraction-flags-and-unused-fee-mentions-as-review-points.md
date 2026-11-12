---
id: SC-8.14
title: Show extraction flags and unused fee mentions as review points
status: "Done"
assignee: []
owner: "Trace numbers back to source documents"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-6txgxv"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/33"
created_date: "2026-11-12 21:25"
updated_date: "2026-11-12 21:23"
labels:
  - ui
  - api
dependencies:
  - SC-8.9
  - SC-5.8
parent_task_id: SC-8
priority: P1
paths_owned:
  - "backend/src/pce/api.py"
  - "backend/src/pce/review_points.py"
  - "backend/tests/test_review_points.py"
  - "frontend/src/components/ReviewPoints.tsx"
  - "frontend/src/pages/Costs.tsx"
  - "frontend/src/lib/types.ts"
  - "frontend/src/lib/it.ts"
  - "frontend/tests/e2e/feelens.spec.ts"
spec_ref: docs/research/UX_RECOMMENDATIONS.md
rule_refs:
  - ".claude/rules/frontend.md"
---

> **One-liner**: Values the extractor flagged and fee amounts it found but nobody used now reach the analyst's "Points to review", in plain words.

## Description

### Context

SC-5.8 added `review` (needs_review + reason codes) on facts and `fee_mention` facts that never enter a total.
SC-8.9 review points only looked at counted lines, so the five flagged KID readings on P-1042 (all on lines
that are shown but not added) raised no point, flag reasons were shown as codes, and fee mentions were invisible.

### User Flow Impact

"Points to review" lists flagged readings on any ledger line (high when the line is counted, low otherwise),
with the reasons in plain EN/IT words, and one point per document whose fee amounts are not used in any
total; opening it lists those amounts with their page, and evidence review accepts or rejects each.

### Performance / Efficiency Impact

No measurable impact: one more list built from facts already loaded.

### Proposed Approach

1. `api.compute`: `unused_mentions` = provenance of non-rejected `fee_mention` facts.
2. `review_points`: flag points on non-counted lines (low), `unused_mentions` grouped per document (medium).
3. Frontend: reuse `reasonText` from `lib/trail.ts`; open unused mentions in the trace source pane.

### Risks & Follow-ups

- The row highlight band discussed with SC-5.8 is covered by SC-8.11's source crop; not added.

## Acceptance Criteria

- [x] #1 Flagged readings on lines not added produce a low review point; on counted lines a high one (unit tests).
- [x] #2 Unused fee mentions are grouped per document and never carry an amount (unit test).
- [x] #3 E2E: the P-1042 review list shows "Reasons: the readers disagree"; full feelens suite green.

## Implementation Notes

## Outcome

- **Status**: completed
- Flags on any ledger line and unused fee mentions now reach Points to review, reasons in plain EN/IT words.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-6txgxv | 1693643 | 2026-11-12 | Extraction flags and unused fee mentions in review points |
