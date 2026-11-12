---
id: SC-8.10
title: Simple upload-to-report flow, live processing, honest results, report
status: "Done"
assignee: []
owner: "Simplify upload-to-report user flow"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-3ahesb"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/19"
created_date: "2026-11-12 13:30"
updated_date: "2026-11-12 13:22"
labels:
  - ui
  - report
dependencies: []
parent_task_id: SC-8
priority: P1
paths_owned:
  - frontend/src/pages/Documents.tsx
  - frontend/src/pages/Costs.tsx
  - frontend/src/pages/Report.tsx
  - frontend/src/pages/Compare.tsx
  - frontend/src/pages/Prospects.tsx
  - frontend/src/components/Shell.tsx
  - frontend/src/lib/**
  - frontend/tests/e2e/feelens.spec.ts
  - backend/src/pce/report.py
  - backend/src/pce/api.py
  - backend/tests/**
spec_ref: docs/research/UX_RECOMMENDATIONS.md
rule_refs: [".claude/rules/frontend.md", ".claude/rules/finance.md", ".claude/rules/privacy.md"]
---

> **One-liner**: An analyst uploads documents, watches each one being read, sees plainly what was read and what still needs a person, and downloads a correct report in English or Italian.

## Description

### Context
Audit of main on 2026-11-12 (synthetic P-2077 plus three real public PDFs: Julius Baer LU price list,
Raiffeisen Locarno price list, iShares KID):
- Upload is one request for all files; the screen shows only a spinner on the button until every file is done.
  On a slow host (Render free plan, OCR on scans) the analyst sees nothing for minutes.
- A prospect with documents but no statement of assets shows "CHF 0" known cost, a green
  "All cost categories evidenced" badge and "0% observed / All cost categories evidenced": it reads as
  "no costs", which breaks "missing is never zero".
- When the proposal is dearer, the report says "Annual saving: at least CHF -2'588" in the saving colour,
  on screen and in the PDF. A negative saving is not a saving; "at least" makes it worse.
- Nowhere on the results or in the report does it say how many values were read and how many a person
  has checked; on real bank pages the parsers read only part of the fees, so this must be explicit.
- PDF report: KPI labels overlap, the appendix truncates item and file names, statement lines show no
  page, and the report is English only although the first user is in Lugano.

### User Flow Impact
Documents: each file gets its own row that moves from waiting to reading to done (type, values found,
values that need a check), then a clear next step. Costs, report and PDF: an empty prospect says what to
upload instead of CHF 0; a dearer proposal says so in plain words; a "what was read" line states values
read, checked by a person, and open review points. PDF: no overlaps, full names, page per line, EN or IT.

### Performance / Efficiency Impact
Files upload one request each instead of one request for all: same total server work, first result
visible after the first file. No backend extraction change.

### Proposed Approach
1. `Documents.tsx`: upload files sequentially through the existing endpoint, keep a per-file state list,
   show values found per file and a next-step button.
2. `Shell.tsx`, `Costs.tsx`, `Report.tsx`: "no statement yet" state when there are no holdings.
3. Saving wording: shared helper in `lib/format.ts` used by Report, Compare, Prospects; same rule in `report.py`.
4. "What was read" line from `analysis.review` on Costs and Report; same line in the PDF.
5. `report.py`: wrap long cells, page per line, fix KPI header overlap, `lang=en|it` (`/report.pdf?lang=it`).

### Risks & Follow-ups
- No change to `finance/` formulas: the engine still reports `is_complete` for an empty ledger; the UI
  treats "no holdings" as not started. A follow-up could make the engine say so itself (rule-9 approval).
- Live demo still deploys the old PR #5 branch; switching Render to `main` is Ale's dashboard action.

## Acceptance Criteria

- [x] #1 Uploading several files shows one row per file with its own state and the values found, before all files finish.
- [x] #2 A prospect with no statement of assets never shows "CHF 0" as its cost nor a green "all evidenced" badge.
- [x] #3 A proposal dearer than today is never shown as a saving (screen and PDF), tested in pytest and Vitest.
- [x] #4 Costs, report and PDF state values read, values checked by a person, and points open.
- [x] #5 PDF: no truncated names, a page for every sourced line, `?lang=it` gives an Italian report; internal margin still absent (existing test stays green).

## Implementation Notes

- Also edited (declared): `frontend/src/components/ReadSummary.tsx` (new: read-status line and the no-statement state),
  `frontend/src/lib/api.ts` (report `lang`), `frontend/src/lib/it.ts` (Italian strings).
- No `finance/` change: the empty state is decided in the UI and in `report.py` from `holdings`.
- `savingParts` (frontend) and `saving_parts` (report.py) carry the same rule; both are unit-tested.
- E2E fix outside the new flow: test 06 looked up "Cost ledger" by text, which also matches the view menu
  label since PR #13; it now uses the heading role.

## Outcome

- **Status**: completed
- Upload: one request per file, live rows (waiting, reading, type + values read), progress bar, next step.
- Empty prospect: "Costs are not calculated yet" on costs, compare, report and PDF; header says
  "No statement of assets yet". Dearer proposal: "Proposal costs more per year", bound flipped.
- Costs, report and PDF: values read, checked by a person, points open.
- PDF rebuilt on platypus: wrapped names, full source file + page, EN/IT (`?lang=it`).
- Gate: GATE PASSED (pytest 133, vitest 9, Playwright 17).

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-3ahesb | 5b2d300 | 2026-11-12 | Live upload rows, empty state, no negative savings, read status |
| claude/project-thread-3ahesb | c77bca0 | 2026-11-12 | PDF report on platypus, full sources, Italian, tests |

## Issues Encountered
