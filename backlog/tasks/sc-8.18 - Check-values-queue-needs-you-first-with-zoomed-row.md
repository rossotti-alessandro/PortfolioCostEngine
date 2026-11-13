---
id: SC-8.18
title: Check values queue needs you first with zoomed row
status: "In Progress"
assignee: []
owner: "Redesign FeeLens user flow and components"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-bj3sap"
pr: ""
created_date: "2026-11-13 12:01"
updated_date: "2026-11-13 12:04"
labels:
  - ui
  - traceability
dependencies: []
parent_task_id: SC-8
priority: P1
paths_owned:
  - frontend/src/pages/Review.tsx
  - frontend/src/lib/trail.ts
  - frontend/src/lib/trail.test.ts
  - frontend/src/components/Shell.tsx
  - frontend/src/lib/it.ts
  - docs/design/DESIGN_SYSTEM.md
spec_ref: docs/design/DESIGN_SYSTEM.md
rule_refs: [".claude/rules/frontend.md", ".claude/rules/extraction.md"]
---

> **One-liner**: The Check values step opens on the values that need a person, says why, and shows the source row zoomed next to Accept, Correct and Reject.

## Description

### Context
Design canvas board "Check values" (thread "Redesign FeeLens user flow and components"):
https://claude.ai/artifact/KLMvQa2NbwCHhYsibvgRnj. On main the review step lists every value of a document
in reading order with the same weight, so an analyst cannot tell which of the 64 values the checks already
confirmed and which need a person, and the source is only the full page at about 40%. Ale asked on
2026-11-13 11:53 UTC for the app UI, UX and functionality to be complete before the pitch.

### User Flow Impact
- Above the value list: Needs you · n, Confirmed by checks · n, Checked by a person · n, All · n. A
  document opens on Needs you when it has any, otherwise on All.
- A value needs a person when nobody has handled it yet and the extraction flagged it (reasons from the
  extraction review), it comes from a scanned page (OCR), or the reading confidence is below 90%. The
  panel says "Why you: …" in words.
- The source row is shown zoomed (SourceCrop from SC-8.11) under the value, above the buttons.
- Keyboard: j/k move, a accept, e correct, r reject. Picking a box on the page outside the current queue
  switches to All instead of jumping away.
- The Check values step count has a tooltip: values not yet checked by a person.

### Performance / Efficiency Impact
None: same facts query; the crop reuses the PDF already loaded for the page.

### Proposed Approach
1. `lib/trail.ts`: pure `whyYou(fact)` with unit tests.
2. `Review.tsx`: queue tabs, default queue, reasons, crop, r key, select handler.

### Risks & Follow-ups
- The queue is per document; a cross-document queue needs the reasons in the analysis payload (backend).
- Documents list does not yet show which files need you.

## Acceptance Criteria

- [ ] #1 A document opens on the values that need a person, with the reason in words and the zoomed source row
- [ ] #2 `whyYou` is unit-tested: confident digital value, flags plus OCR plus low confidence, already handled
- [ ] #3 E2E review and trace tests pass; EN and IT strings present

## Implementation Notes

## Outcome

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |

## Issues Encountered
