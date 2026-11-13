---
id: SC-8.21
title: Compact documents list with details behind the row
status: "Done"
assignee: []
owner: "Redesign FeeLens user flow and components"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-bj3sap"
pr: ""
created_date: "2026-11-13 12:30"
updated_date: "2026-11-13 12:45"
labels:
  - ui
dependencies: []
parent_task_id: SC-8
priority: P1
paths_owned:
  - frontend/src/pages/Documents.tsx
  - frontend/src/lib/it.ts
  - docs/design/DESIGN_SYSTEM.md
spec_ref: docs/design/DESIGN_SYSTEM.md
rule_refs: [".claude/rules/frontend.md"]
---

> **One-liner**: The Documents page lists each file on one line (file, type, bank or issuer, date, values, status) and keeps the technical details behind the row.

## Description

### Context
Design canvas board "Documents" (thread "Redesign FeeLens user flow and components"):
https://claude.ai/artifact/KLMvQa2NbwCHhYsibvgRnj. On main each document row is four to six lines tall: file
name, read-with badge, fingerprint, "How it was processed" link, warnings and a type dropdown. With eleven
files the list is longer than two screens, and the drop zone stays full height after the first upload.
Ale asked to make the app complete and simple from start to finish (2026-11-13 11:53 UTC).

### User Flow Impact
- One line per document: File, Type, Bank or issuer, Date, Values, Status ("Needs a check" when the type
  is unknown or the reader left a warning, otherwise "Ready"), and an icon link to how it was processed.
- Documents that need a check come first. The first 6 show; "Show all {n} documents" reveals the rest.
- Clicking a row opens its details underneath: how it was read (digital text, OCR, spreadsheet cells),
  fingerprint, warnings, the type selector, and a link to check its values.
- Once documents exist, the drop zone shrinks to one line.

### Performance / Efficiency Impact
None: same documents payload, fewer DOM nodes per row.

### Proposed Approach
1. `Documents.tsx`: `DocTable` with a summary row and an expandable detail row; slice to 6 with a toggle;
   compact `Dropzone` when documents exist. EN/IT strings.
2. E2E unchanged: the synthetic E2E prospect has 4 documents, below the 6-row cut.

### Risks & Follow-ups
- The type selector moves into the details; correcting a type takes one more click.

## Acceptance Criteria

- [x] #1 Each document row is one line with file, type, bank or issuer, date, values and status; details open under the row
- [x] #2 At most 6 rows show until "Show all"; documents needing a check come first
- [x] #3 E2E suite passes (upload, pipeline links, type change)

## Implementation Notes

- Owned paths as listed. No backend change. The checklist column narrows from 340 to 300 px so the list keeps its columns at 1440 px.

## Outcome

- **Status**: completed
- One line per document (File, Type, Bank or issuer, Date, Values, Status, icon link to how it was processed); needs-a-check first; 6 shown, then "Show all {n} documents".
- Details under the row: read with, pages, period, jurisdiction, fingerprint, warnings, type selector, links to its values and its processing.
- Drop zone is one line once documents exist.
- E2E 17/17 passed locally; `local-gate.sh` GATE PASSED. Screenshot: project files `feelens-redesign/documents-compact.png`.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-bj3sap | d3c27ce | 2026-11-13 | Compact documents list, details under the row, one-line drop zone |

## Issues Encountered
