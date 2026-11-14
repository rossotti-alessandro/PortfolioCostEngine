---
id: SC-8.25
title: Page layouts for phone and tablet, and tap to open info
status: "In Progress"
assignee: []
owner: "Redesign FeeLens user flow and components"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-bj3sap"
pr: ""
created_date: "2026-11-14 00:40"
updated_date: "2026-11-14 00:14"
labels:
  - ui
dependencies: [SC-8.24]
parent_task_id: SC-8
priority: P1
paths_owned:
  - frontend/src/components/ui.tsx
  - frontend/src/pages/Compare.tsx
  - frontend/src/pages/Documents.tsx
  - frontend/tests/e2e/responsive.spec.ts
  - docs/design/DESIGN_SYSTEM.md
spec_ref: docs/design/DESIGN_SYSTEM.md
rule_refs: [".claude/rules/frontend.md"]
---

> **One-liner**: Every screen fits a phone and a tablet without sideways scrolling, and every (i) opens on a tap, not only on hover.

## Description

### Context
Follow-up to SC-8.24 (Ale, 2026-11-13 23:51 UTC: complete for different window sizes and mobile, details
behind (i)). Audit after the shell fix: Compare scrolls sideways at 390 px (cost-by-layer and proposal-lines
tables, card headers with a legend), the Documents table squeezes six columns into 360 px so names, types and
dates collapse into ellipses, and the (i) tooltips open only on hover or keyboard focus, so on a phone or
tablet a tap shows nothing.

### User Flow Impact
- (i) opens on tap and closes on a second tap or a tap outside; still opens on hover and focus.
- Card headers wrap their actions under the title instead of pushing the card wider; cards never grow wider
  than their column.
- Compare: on a phone the bar column hides (the numbers are the twin), the total's "at least" goes on its own
  line, and both tables scroll inside their card if still too wide.
- Documents: below 1360 px the type and bank sit under the file name instead of in their own columns; the
  date column hides on phones and the status shows its icon only (the label stays for screen readers).

### Performance / Efficiency Impact
None: classes only, one state per (i).

### Proposed Approach
1. `ui.tsx`: `Card` `min-w-0`; `CardHeader` wraps; `Tip` controlled, `InfoTip` toggles on click.
2. `Compare.tsx`, `Documents.tsx`: responsive columns as above.
3. E2E: no sideways scroll on every prospect page at 390 and 820 px; (i) opens on tap.

### Risks & Follow-ups
- PR #40 rewrites the Compare proposal editor; this story touches only the layer table and the proposal
  lines card opening tag, so the hunks do not overlap.

## Acceptance Criteria

- [ ] #1 No page scrolls sideways at 390 and 820 px, Compare included (E2E)
- [ ] #2 Tapping (i) shows its text (E2E)
- [ ] #3 Existing E2E suite passes

## Implementation Notes

## Outcome

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |

## Issues Encountered
