---
id: SC-8.29
title: Simple CRM home for phone and desktop with a needs-you-today list
status: Done
assignee: []
owner: "Rebuild CRM for mobile and browser"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-m6dkdk"
pr: ""
created_date: "2026-11-25 20:10"
updated_date: "2026-11-25 19:54"
labels:
  - ui
  - crm
dependencies: []
parent_task_id: SC-8
priority: P1
paths_owned:
  - "frontend/src/pages/crm/**"
  - "frontend/src/lib/it.ts"
  - "frontend/tests/e2e/crm.spec.ts"
  - "frontend/tests/e2e/responsive.spec.ts"
spec_ref: docs/research/UX_RECOMMENDATIONS.md
rule_refs:
  - ".claude/rules/frontend.md"
---

> **One-liner**: The CRM home answers "who needs me today" first, shows a stage list on a phone instead of a sideways kanban, and drops the noise (orange on every card, a big select per card, a demo button in production).

## Description

### Context

Screenshots 2026-11-25 (seeded synthetic CRM): on a 390 px phone the home page scrolls sideways
(pipeline assets KPI overflows, 7 kanban columns of 260 px); every card carries a full-width "Move to…"
select and an orange overdue line, so nothing stands out; "Load synthetic CRM" sits next to "New contact"
even when real contacts exist. The activity type select on a contact shows raw ids ("note").

### User Flow Impact

- Top of the home: "Needs you today", the overdue and due-today next actions (5 on a phone, 3 on a desktop, oldest first,
  "show all" for the rest). One tap opens the contact.
- Phone and tablet (< 1024 px): stage chips with counts, then full-width rows for that stage.
  Desktop keeps the kanban with drag and drop.
- Cards: next action in grey, only the word "overdue" in amber; "Move to" is a small icon button that opens
  the native picker (keyboard and phone path kept).
- Demo seed button only in the empty state. KPI row fits a phone (pipeline assets full width; win rate on
  the Funnel tab only on phones).

### Performance / Efficiency Impact

No new requests; the list and the today panel reuse the contacts query.

### Proposed Approach

1. `pages/crm/Board.tsx`: `useWide()` (matchMedia 1024 px), `Today` panel, `StageList` for narrow screens,
   compact card with `MoveSelect`.
2. `pages/crm/common.tsx`: header actions; translate activity types.
3. E2E: phone CRM has no sideways page, shows the today list and a stage list; desktop tests unchanged.

### Risks & Follow-ups

Owner filter ("my contacts") needs named users (SC-11.12) and follows it.

## Acceptance Criteria

- [x] #1 On a 390 px phone the CRM home has no sideways scroll, shows "Needs you today" and a stage list; a tap opens the contact
- [x] #2 Desktop kanban, drag and drop and the existing CRM E2E tests still pass (regression guard)

## Implementation Notes

## Outcome

- **Status**: completed
- New Playwright test "phone CRM" (390 px, touch): today list, stage chips, row tap opens the contact, no
  sideways page on the home or the contact. All CRM, drag-and-drop and responsive tests still pass.
- Full gate GATE PASSED; Playwright 25/25.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-m6dkdk | ac82f03 | 2026-11-25 | today list, stage list on phones, quieter cards |
