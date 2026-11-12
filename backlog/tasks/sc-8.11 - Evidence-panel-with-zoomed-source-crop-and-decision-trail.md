---
id: SC-8.11
title: Evidence panel with zoomed source crop and decision trail
status: "Done"
assignee: []
owner: "Redesign FeeLens user flow and components"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-bj3sap"
pr: ""
created_date: "2026-11-12 20:20"
updated_date: "2026-11-12 20:11"
labels:
  - ui
  - traceability
dependencies: []
parent_task_id: SC-8
priority: P1
paths_owned:
  - frontend/src/components/Trace.tsx
  - frontend/src/components/EvidenceViewer.tsx
  - frontend/src/components/DecisionTrail.tsx
  - frontend/src/components/SourceCrop.tsx
  - frontend/src/lib/trail.ts
  - frontend/src/lib/trail.test.ts
  - frontend/src/lib/it.ts
  - frontend/src/lib/types.ts
  - frontend/src/index.css
  - frontend/tests/e2e/feelens.spec.ts
  - docs/design/DESIGN_SYSTEM.md
spec_ref: docs/design/DESIGN_SYSTEM.md
rule_refs: [".claude/rules/frontend.md", ".claude/rules/privacy.md"]
---

> **One-liner**: Clicking any number opens a side panel (not a modal) that shows the formula, a zoomed crop of the exact source row with only that box highlighted, and the decision trail of the value (read, checks, person, used in).

## Description

### Context
SC-8.9 added click-any-number tracing as a modal dialog. The modal covers the table the analyst came from,
the source page is rendered at about 40% so the text is ~5 px, every value on the page is boxed in the same
colour so the cited one does not stand out, and the only decision shown is "Not yet checked by an analyst".
Ale asked (thread "Redesign FeeLens user flow and components", 2026-11-12) for every decision and every
datum to be traceable back with proper retrieval and highlights. Design canvas:
https://claude.ai/artifact/KLMvQa2NbwCHhYsibvgRnj (boards "Costs with the evidence panel open" and "Components").

### User Flow Impact
- Any number on Costs and Compare opens a right-hand evidence panel; the page stays usable and clicking
  another number swaps the panel content. Escape or × closes it.
- A line shows: amount and status, formula, its inputs (rate, holding, FX), a zoomed crop of the cited
  row at readable size with the rest dimmed, "Show full page" with only the cited box drawn (toggle to show
  all values), then the decision trail.
- Decision trail: how it was read (digital text, OCR or spreadsheet cell, engine, confidence, text on the
  page); what the automatic checks said (review status, reasons, checks and second readers when the
  extraction provides them, SC-5.8/5.14); what a person did (accept, correct old → new with reason, reject,
  who and when, from the review history); and which totals the line feeds.

### Performance / Efficiency Impact
The crop re-uses the PDF already fetched for the page (react-query cache). One extra small request per
opened value (`/api/facts/{id}/history`). No backend change.

### Proposed Approach
1. `Trace.tsx`: render `TraceDialog` as a non-modal right sheet (Radix Dialog `modal={false}`, outside
   clicks do not close it); single-column layout for a line.
2. `SourceCrop.tsx`: render the page with pdf.js and show only the bbox region plus context, dimmed outside
   the row, one box with the value tag.
3. `EvidenceViewer.tsx`: `focus` prop on `PdfEvidence` draws only the active box unless "Show all values"
   is ticked.
4. `lib/trail.ts` (pure, unit-tested): builds the trail steps from an `EvidenceRef` and its review history.
   `DecisionTrail.tsx` renders them. EN/IT strings in `lib/it.ts`.
5. E2E test 11 keeps passing; screenshots refreshed.

### Risks & Follow-ups
- Review page queue ("Check values"), workspace header/nav, Costs page simplification, Documents and Report
  are separate stories (see the canvas).
- Reason codes from PR #15/#27 get plain wording here; new codes fall back to a readable form of the code.

## Acceptance Criteria

- [x] #1 Clicking a number opens a side panel that does not block the page; clicking another number replaces its content; Escape closes it
- [x] #2 A line with a PDF source shows a zoomed crop where only the cited row is highlighted, and a full page on demand with only the cited box drawn
- [x] #3 The decision trail lists read, automatic checks, person decisions (from history) and the totals the line feeds; unknown and missing steps say so, never invent a check
- [x] #4 Trail building is unit-tested (OCR vs text vs sheet, needs_review reasons, checks, corrections)
- [x] #5 E2E trace test passes; EN and IT strings present

## Implementation Notes

- Owned paths as listed. No backend change: the panel reads `review` (fact.extra.review) already exposed by
  the analysis payload and the existing `/api/facts/{id}/history` endpoint.
- `PdfEvidence` gained `focus` and a shared `usePdf` hook; the Review page keeps its current behaviour.
- The active highlight uses `mix-blend-mode: multiply` so the text under it stays legible everywhere.

## Outcome

- **Status**: completed
- Any number on Costs and Compare opens a non-modal right panel; the page reflows on screens ≥ 1280 px.
- Line view: amount, status, formula, inputs, a crop of the cited row (context dimmed, value tag), full page
  on demand with only the cited box (toggle for all values), the text on the page, then the decision trail
  with "Accept this value" when nobody has reviewed it yet.
- Tests: `lib/trail.test.ts` (6 cases); E2E test 11 extended (non-modal, trail steps, focus mode, accept
  shows "Accepted by <user>"). Full E2E 17/17 passed locally; `local-gate.sh` GATE PASSED.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-bj3sap | 16e5134 | 2026-11-12 | Story file |
| claude/project-thread-bj3sap | 3b776cb | 2026-11-12 | Evidence side panel, source crop, decision trail, tests |

## Issues Encountered

- Cloud container lacked tesseract, ghostscript and qpdf (bootstrap packages); installed with apt for the gate.
