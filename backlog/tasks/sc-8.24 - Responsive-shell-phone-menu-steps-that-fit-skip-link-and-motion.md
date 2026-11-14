---
id: SC-8.24
title: Responsive shell, phone menu, steps that fit, skip link and motion
status: "Done"
assignee: []
owner: "Redesign FeeLens user flow and components"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-bj3sap"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/55"
created_date: "2026-11-14 00:05"
updated_date: "2026-11-14 00:08"
labels:
  - ui
dependencies: []
parent_task_id: SC-8
priority: P1
paths_owned:
  - frontend/src/components/Shell.tsx
  - frontend/src/index.css
  - frontend/src/lib/it.ts
  - frontend/tests/e2e/responsive.spec.ts
  - docs/design/DESIGN_SYSTEM.md
spec_ref: docs/design/DESIGN_SYSTEM.md
rule_refs: [".claude/rules/frontend.md"]
---

> **One-liner**: On a phone the app opens on the content, with the navigation behind a menu button and the five review steps in one scrollable row; everywhere, keyboard users can skip to the content and motion respects the system setting.

## Description

### Context
Ale asked for a full UI/UX pass, professional and clear, for every window size including mobile
(2026-11-13 23:51 UTC). Audit at 390 px wide on main: the sidebar stacks above every page and fills the
first screen (brand, three links, local-only note, account), the synthetic banner and title come only after
it, and the step bar cuts "Costs" off with no sign that it scrolls. There is no skip link, and nothing
honours `prefers-reduced-motion`. References checked: Vercel Web Interface Guidelines (skip link, focus,
reduced motion, touch-action, overscroll in drawers), Anthropic frontend-design skill (motion only to show
what changed).

### User Flow Impact
- Below 768 px: a top bar with the logo and a "Menu" button. The menu slides in from the left with the same
  places and account menu; it closes on navigation, on Escape and on a tap outside.
- The step bar keeps the current step in view and scrolls sideways; on a phone "Internal economics" shows as
  a lock icon with its name for screen readers.
- "Skip to content" is the first tab stop on every page.
- Menus, details rows and the evidence panel fade in briefly; with reduced motion they appear at once.

### Performance / Efficiency Impact
None: CSS and one small state in the shell.

### Proposed Approach
1. `Shell.tsx`: mobile top bar + drawer around the existing sidebar; skip link; `main#main`; step bar
   scrolls the active step into view.
2. `index.css`: `pce-in` keyframes, reduced-motion override, `touch-action: manipulation`.
3. E2E `responsive.spec.ts`: at 390 px the content is the first thing below the top bar, the menu opens and
   navigates, no page scrolls sideways.

### Risks & Follow-ups
- PR #40 and #48 each add one link to the sidebar nav; this story does not touch the nav links, so both merge cleanly.

## Acceptance Criteria

- [x] #1 At 390 px the page title is visible without scrolling and the menu button opens the navigation
- [x] #2 No shell-level sideways scroll at 390 px on Documents, Check values, Costs, Report and Cost reviews (E2E); Compare is fixed in the page story
- [x] #3 Skip link and reduced motion work; existing E2E suite passes

## Implementation Notes

- Owned paths as listed. Nav link lines untouched (PR #40 and #48 add links there). The account menu opens downwards in the phone drawer and upwards in the desktop sidebar.
- Compare still scrolls sideways at 390 px (cost-by-layer table): handled in the page-layout story, not here.

## Outcome

- **Status**: completed
- Phone top bar with Menu, drawer nav (Escape, tap outside, navigation close it), step bar centred on the current step, lock icon for Internal economics on phones, skip link, `pce-in`/`pce-fade` motion with reduced-motion override, `touch-action: manipulation`.
- E2E 19/19 (new `responsive.spec.ts`: phone content first, menu, no sideways scroll, skip link); `local-gate.sh` GATE PASSED.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-bj3sap | a8f668b | 2026-11-14 | Phone menu drawer, step bar, skip link, motion, responsive E2E |

## Issues Encountered
