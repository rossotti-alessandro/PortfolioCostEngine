---
id: SC-8.26
title: Drag and drop files anywhere on Documents, and CRM cards between stages
status: "In Progress"
assignee: []
owner: "Redesign FeeLens user flow and components"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-bj3sap"
pr: ""
created_date: "2026-11-14 00:30"
updated_date: "2026-11-14 00:25"
labels:
  - ui
dependencies: [SC-8.25]
parent_task_id: SC-8
priority: P1
paths_owned:
  - frontend/src/pages/Documents.tsx
  - frontend/src/pages/crm/Board.tsx
  - frontend/src/lib/it.ts
  - frontend/tests/e2e/dragdrop.spec.ts
  - docs/design/DESIGN_SYSTEM.md
spec_ref: docs/design/DESIGN_SYSTEM.md
rule_refs: [".claude/rules/frontend.md"]
---

> **One-liner**: Files can be dropped anywhere on the Documents page with a clear drop state, wrong files are refused at once, and CRM cards drag between stages with visible feedback.

## Description

### Context
Ale asked for proper drag and drop (2026-11-13 23:53 UTC). On main the Documents page accepts files only on the
drop box itself, with no page-level feedback; a file of the wrong type or over 25 MB goes to the server and
comes back as an error. The CRM board drags cards, but the dragged card gives no feedback, Firefox starts no
drag (no data set on dragstart), the column highlight flickers when the pointer crosses a card, and a move is
not announced to screen readers.

### User Flow Impact
- Documents: dragging files over any part of the page shows a full-page overlay "Drop to add 3 files to this
  cost review"; dropping uploads them. Files that are not PDF or XLSX, or larger than 25 MB, appear at once in
  the upload list as refused, with the reason. The drop box says files can be dropped anywhere; "Choose files"
  stays as the keyboard and touch path.
- CRM board: cards have a grip, a grab cursor and dim while dragged; the target column shows a dashed teal
  outline only when the card would move; the move is announced. "Move to…" stays for keyboard and touch.

### Performance / Efficiency Impact
Fewer wasted uploads: refused files never leave the browser.

### Proposed Approach
1. `Documents.tsx`: `useFileDrag` window listeners with an enter/leave depth counter, `DropOverlay`,
   `refusal()` with the API's limits.
2. `Board.tsx`: dataTransfer data and effect, dragend reset, relatedTarget-safe leave, live region.
3. E2E `dragdrop.spec.ts`.

### Risks & Follow-ups
- HTML5 drag and drop does not run on touch screens; the existing "Choose files" and "Move to…" cover them.

## Acceptance Criteria

- [ ] #1 Dragging files over the Documents page shows the overlay; a dropped non-PDF/XLSX file is refused at once with its reason (E2E)
- [ ] #2 A CRM card dragged to another column moves there and the move is announced (E2E)
- [ ] #3 Existing E2E suite passes

## Implementation Notes

## Outcome

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |

## Issues Encountered
