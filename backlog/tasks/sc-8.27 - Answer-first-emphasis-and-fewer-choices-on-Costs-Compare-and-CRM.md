---
id: SC-8.27
title: Answer first emphasis and fewer choices on Costs, Compare and CRM
status: "In Progress"
assignee: []
owner: "Redesign FeeLens user flow and components"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-bj3sap"
pr: ""
created_date: "2026-11-14 00:36"
updated_date: "2026-11-14 00:36"
labels:
  - ui
dependencies: [SC-8.26]
parent_task_id: SC-8
priority: P1
paths_owned:
  - frontend/src/pages/Compare.tsx
  - frontend/src/pages/Costs.tsx
  - frontend/src/pages/crm/Board.tsx
  - frontend/src/components/ReviewPoints.tsx
  - frontend/src/lib/it.ts
  - frontend/tests/e2e/emphasis.spec.ts
  - docs/design/DESIGN_SYSTEM.md
spec_ref: docs/design/DESIGN_SYSTEM.md
rule_refs: [".claude/rules/frontend.md"]
---

> **One-liner**: Each screen leads with its answer and offers fewer choices at once; long lists open with "Show all".

## Description

### Context
Ale asked (2026-11-13 23:51 UTC) for every screen to follow UI/UX principles: Hick's law, emphasis, one clear
call to action, details on demand. An audit of the synthetic prospect at 1440 px found:
- Compare: the annual saving, the answer, is the third of four equal figure cards; layer names wrap onto three
  lines in the side-by-side grid; "every line of the proposal" lists 15 rows at once.
- Costs: "Documents to ask for" shows all four requests with two buttons each (eight choices) under all-caps
  eyebrows.
- CRM board: "Load synthetic CRM" appears in the header and again in the empty state, next to the primary
  "New contact".
- Points to review: "1 notes".

### User Flow Impact
- Compare opens on the annual saving; the layer table takes the full width below 1600 px; the proposal lines
  show six rows (undetermined first) and "Show all 15 lines".
- Costs shows the two biggest requests and "Show all 4 requests"; the priority line is sentence case.
- CRM header has one action, "New contact"; the synthetic seed stays in the empty state.

### Performance / Efficiency Impact
None measurable; fewer rows rendered by default.

### Proposed Approach
Reorder the figure cards, change the grid breakpoint, slice the two lists with the same "Show all" row as
Points to review, drop the duplicate header button, fix the plural.

### Risks & Follow-ups
- The firm-tariff PR (#40) also edits Compare.tsx (imports and the proposal editor); these hunks avoid both.

## Acceptance Criteria

- [ ] #1 Compare shows the annual saving as the first figure card, and the proposal lines open with six rows and a "Show all" control (E2E)
- [ ] #2 Costs shows two requests and "Show all 4 requests"; expanding shows all four (E2E)
- [ ] #3 Existing E2E suite passes

## Implementation Notes

## Outcome

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |

## Issues Encountered
