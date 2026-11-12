---
id: SC-8.13
title: Professional visual system: square cards, figures and one primary action
status: "Done"
assignee: []
owner: "Redesign FeeLens user flow and components"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-bj3sap"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/29"
created_date: "2026-11-12 20:45"
updated_date: "2026-11-12 20:52"
labels:
  - ui
dependencies: []
parent_task_id: SC-8
priority: P1
paths_owned:
  - frontend/src/styles/tokens.css
  - frontend/src/index.css
  - frontend/src/components/ui.tsx
  - frontend/src/components/ReadSummary.tsx
  - frontend/src/pages/Costs.tsx
  - frontend/src/pages/Compare.tsx
  - frontend/src/pages/Internal.tsx
  - frontend/src/pages/Report.tsx
  - frontend/src/pages/Documents.tsx
  - frontend/src/pages/Pipeline.tsx
  - frontend/src/pages/Review.tsx
  - frontend/src/lib/it.ts
  - docs/design/DESIGN_SYSTEM.md
spec_ref: docs/design/DESIGN_SYSTEM.md
rule_refs: [".claude/rules/frontend.md"]
---

> **One-liner**: Square controls and cards, key figures in equal cards that never wrap, and exactly one filled primary action per screen.

## Description

### Context
Ale reviewed the app (thread "Redesign FeeLens user flow and components", 2026-11-12 20:39 UTC): the numbers
and information did not look professional; asked for square components, proper calls to action, and each
number inside a proper container and card. Audit of every screen found: pill badges and 10 px rounded
cards; KPI values that wrapped onto two lines in a four-column grid (worse with the evidence panel open);
the currency code at the same weight as the figure; two filled buttons side by side on Documents and
Pipeline (teal "accent" next to navy primary), so no single next step; Report figures on grey tiles unlike
the other cards; the Documents table scrolled horizontally and broke file names letter by letter; Compare
layer names wrapped to three lines; the cost-by-layer chart cut its "+ not determined" labels.

### User Flow Impact
- Every key figure sits in a card of the same height: short label, the figure on one line with the currency
  code small and muted, then one line of context. Cards reflow to fewer columns instead of squeezing.
- Each screen has one filled navy button for the next step; secondary actions are outlined.
- Badges, buttons, inputs and cards use square corners (4 px controls, 6 px cards), no drop shadows.
- Documents: file, type, issuer and date, values, without horizontal scrolling; how the file was read and
  its fingerprint move under the file name.

### Performance / Efficiency Impact
None: styling and markup only. No new dependency, no backend change.

### Proposed Approach
1. Tokens: `--radius-control` 4 px, `--radius-card` 6 px. `Button`, inputs, `Badge`, `Card` use them.
2. `Money` (currency code split from the figure, never wraps) and `StatGrid` (auto-fit, min 220 px) in
   `ui.tsx`; `Kpi` rebuilt on them. Costs, Compare, Internal and Report use `StatGrid`.
3. `accent` button variant becomes a teal outline; primary actions on Documents, Pipeline, Review, Report
   and the empty states become the default navy button, partners become outline.
4. Table and layout fixes listed in Context. EN/IT strings updated.

### Risks & Follow-ups
- The report audit trail still lists "document uploaded" eleven times: grouped decision log is the Report
  story in the design canvas.
- `Money` splits only strings of the form `CHF 1'234`; other formats render unchanged.

## Acceptance Criteria

- [x] #1 KPI and report figures render on one line with a small currency code at 1280 and 1440 px, also with the evidence panel open
- [x] #2 Every screen shows at most one filled primary button; other actions are outlined
- [x] #3 Buttons, inputs, badges and cards use the square radius tokens; no pill badges remain in `ui.tsx`
- [x] #4 Documents table has no horizontal scroll at 1440 px; existing E2E tests keep passing

## Implementation Notes

- Owned paths as listed. No backend change. Built on SC-8.11 (evidence panel, PR #28).

## Outcome

- **Status**: completed
- Radius tokens 4 px controls / 6 px cards, square badges, no card shadows. `Money` and `StatGrid` in
  `ui.tsx`; `Kpi`, the coverage card and the report figures share one card shape with figures on one line.
- One filled primary per screen: Documents "Review extracted values", Pipeline "Review its values", Review
  "Accept", Report PDF in the current language, empty state "Upload documents"; partners outlined.
- Documents table: issuer and date in one column, read-with badge and short fingerprint under the file
  name, no horizontal scroll at 1440 px. Compare layer names on one line; chart labels no longer cut.
- Full E2E 17/17 passed locally; `local-gate.sh` GATE PASSED.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-bj3sap | 9fc71d6 | 2026-11-12 | Square visual system, figure cards, one primary action |

## Issues Encountered
