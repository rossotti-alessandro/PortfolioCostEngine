---
id: SC-8.15
title: Workspace header with steps and a simpler sidebar
status: "Done"
assignee: []
owner: "Redesign FeeLens user flow and components"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-bj3sap"
pr: ""
created_date: "2026-11-12 22:58"
updated_date: "2026-11-12 22:58"
labels:
  - ui
dependencies: []
parent_task_id: SC-8
priority: P1
paths_owned:
  - frontend/src/components/Shell.tsx
  - frontend/src/pages/Catalogue.tsx
  - frontend/src/pages/HowItWorks.tsx
  - frontend/src/lib/it.ts
  - frontend/tests/e2e/feelens.spec.ts
  - docs/design/DESIGN_SYSTEM.md
spec_ref: docs/design/DESIGN_SYSTEM.md
rule_refs: [".claude/rules/frontend.md"]
---

> **One-liner**: The five steps of a cost review sit across the top of the prospect workspace with live counts, and the sidebar shrinks to three places plus one account menu.

## Description

### Context
Design canvas (thread "Redesign FeeLens user flow and components", board "New user flow"):
https://claude.ai/artifact/KLMvQa2NbwCHhYsibvgRnj. Today the sidebar carries four main links, the prospect
steps, a privacy note, a language switch, a role picker and the account, so the steps of a review sit below
the fold of the sidebar and nothing says how much work is left in each. Ale asked to continue the redesign
after SC-8.11 and SC-8.13 (2026-11-12 22:57 UTC).

### User Flow Impact
- Prospect header: breadcrumb, name, key facts, then the steps Documents, Check values, Costs, Compare,
  Report across the top, always visible, each with its state (done tick, or the number of values still to
  check). Internal economics is a lock link at the right end of the steps.
- Sidebar: Clients, Cost reviews, Library (data catalogue and how it works). The local-only note becomes a
  shield with a tooltip. Language, demo role and sign-out move into one account menu at the bottom.

### Performance / Efficiency Impact
None: the header reuses the analysis and documents queries the pages already load.

### Proposed Approach
1. `Shell.tsx`: `StepBar` in `ProspectLayout`; remove `ProspectNav` from the sidebar; `AccountMenu`
   (details popover) with language buttons, role select and sign-out; Library link active on both pages.
2. Catalogue and How it works link to each other. EN/IT strings.
3. E2E: open the account menu before switching language or role.

### Risks & Follow-ups
- Page headings keep their names (E2E anchors); renaming "Review evidence" to "Check values" on the page
  itself comes with the Check values queue story.

## Acceptance Criteria

- [x] #1 On every prospect page the five steps show across the top with done state and the count of values still to check; clicking a step navigates
- [x] #2 Sidebar shows Clients, Cost reviews, Library and an account menu that holds language, demo role and sign-out
- [x] #3 E2E suite passes, including language and role switching through the menu

## Implementation Notes

- Owned paths as listed. No backend change. The step count is `review.facts - reviewed - rejected` from the
  analysis payload already loaded by every prospect page.
- The account menu is a `<details>` popover; it closes when the language changes (the app re-renders), so
  the E2E reopens it before switching back.

## Outcome

- **Status**: completed
- Prospect header: breadcrumb, name, facts, then the five steps (Documents, Check values with the count
  still to check, Costs, Compare, Report) and a lock link to Internal economics.
- Sidebar: Clients & pipeline, Cost reviews, Library (catalogue and how it works link to each other), a
  "Local only" shield with tooltip, and the account menu (language, demo role, sign-out).
- E2E 17/17 passed locally; `local-gate.sh` GATE PASSED. Screenshots: project files
  `feelens-redesign/nav-*.png`.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-bj3sap | bfa3322 | 2026-11-12 | Steps across the workspace header, simpler sidebar |

## Issues Encountered
