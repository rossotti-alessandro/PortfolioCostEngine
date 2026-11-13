---
id: SC-8.19
title: Report ready-to-send checklist and grouped decision log
status: "In Progress"
assignee: []
owner: "Redesign FeeLens user flow and components"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-bj3sap"
pr: ""
created_date: "2026-11-13 12:16"
updated_date: "2026-11-13 12:14"
labels:
  - ui
dependencies: []
parent_task_id: SC-8
priority: P1
paths_owned:
  - frontend/src/pages/Report.tsx
  - frontend/src/lib/it.ts
  - docs/design/DESIGN_SYSTEM.md
spec_ref: docs/design/DESIGN_SYSTEM.md
rule_refs: [".claude/rules/frontend.md", ".claude/rules/privacy.md"]
---

> **One-liner**: Before the PDF goes out, the Report page says what is still open, and its audit trail reads as a short decision log.

## Description

### Context
Design canvas board "Report" (thread "Redesign FeeLens user flow and components"):
https://claude.ai/artifact/KLMvQa2NbwCHhYsibvgRnj. On main the Report page offers the PDF without saying
whether values still need a person or documents are still missing, and the audit trail lists "document
uploaded" once per file (eleven rows for P-1042). Ale asked to continue the canvas pieces and make the app
complete from start to finish (2026-11-13 11:53 UTC).

### User Flow Impact
- "Ready to send?" card above the PDF actions, one line per check, each with a status icon and text:
  values still needing a person (link "Check now" to Check values), documents to ask for (link "See the
  list" to Costs), costs not determined (listed in the report, never counted as zero), senior approval.
  Footer: internal margin and analyst notes are never in the PDF.
- "Audit trail" becomes "Decision log": consecutive events with the same action and user collapse into one
  row with a count ("11 documents uploaded"), actions in plain words.

### Performance / Efficiency Impact
None: reads the analysis and facts already loaded by the workspace; no new endpoint.

### Proposed Approach
1. `Report.tsx`: `ReadyCard` from the analysis (requests, unknown lines, review counts, approval);
   `group()` + `ACTION` map for the log. EN/IT strings.
2. DESIGN_SYSTEM.md: Report layout line.

### Risks & Follow-ups
- The checklist informs, it does not block the PDF: the analyst may send a lower-bound report on purpose.

## Acceptance Criteria

- [ ] #1 The Report page lists open checks (values to check, documents to ask for, undetermined costs, approval) with links to where each is resolved
- [ ] #2 Repeated consecutive audit events appear once with a count; no internal margin in the client report route
- [ ] #3 E2E suite passes (report, PDF, roles)

## Implementation Notes

## Outcome

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |

## Issues Encountered
