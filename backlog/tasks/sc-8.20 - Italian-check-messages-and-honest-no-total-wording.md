---
id: SC-8.20
title: Italian check messages and honest "no total" wording
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-13 12:30"
updated_date: "2026-11-13 12:30"
labels:
  - ui
  - i18n
dependencies: []
parent_task_id: SC-8
priority: P1
paths_owned:
  - frontend/src/lib/i18n.ts
  - frontend/src/lib/it.ts
  - frontend/src/components/ReadSummary.tsx
  - frontend/src/components/ReviewPoints.tsx
  - frontend/src/pages/Costs.tsx
  - frontend/src/pages/Compare.tsx
  - frontend/src/pages/Report.tsx
  - frontend/src/pages/Pipeline.tsx
  - frontend/src/lib/*.test.ts
  - frontend/tests/e2e/**
spec_ref: docs/research/UX_RECOMMENDATIONS.md
rule_refs: [".claude/rules/frontend.md"]
---

> **One-liner**: Check and review messages written by the backend show in Italian in the Italian UI, and the empty Costs page no longer says "none of the documents is a statement of assets" when a statement is there but could not be valued in CHF.

## Description

### Context
The checks list (Costs, Pipeline) and the generic review points show backend text in English even in the Italian UI, for example "GBP 660,273.45 could not be converted and is left out of every total". Seen while taking the Italian screenshots for the proposal deck. On a real AJ Bell statement in GBP with no GBP/CHF rate, the Costs page said "None of the 4 documents is a statement of assets", which is false: the statement was uploaded and classified, only its holdings could not be valued in CHF.

### User Flow Impact
An Italian analyst reads every check in Italian. The empty Costs, Compare and Report pages say why no total is shown: no statement yet, or a statement whose positions could not be valued in CHF, with a pointer to the failing checks.

### Performance / Efficiency Impact
No measurable impact: a short list of regular expressions is tried on each message only in the Italian UI.

### Proposed Approach
1. `i18n.ts`: `tm(text)` translates a backend message by trying the message templates in `it.ts` (`IT_MESSAGES`, regex to Italian with `$1` groups); unknown text stays English.
2. `it.ts`: one template for every `Check` title and detail in `pce/analysis.py`, the ledger warnings in `pce/finance/ledger.py`, the tariff rejection reasons in `pce/finance/tariff.py` and the second-person label in `pce/extraction/parsers.py`.
3. Use `tm` where check and fallback review point text is shown (Costs, Pipeline, ReviewPoints).
4. `ReadSummary.NotStarted`: when a statement of assets is among the documents, say its positions could not be valued in CHF and point to the checks; otherwise keep the current text.

### Risks & Follow-ups
Templates follow the backend wording: a changed backend sentence silently falls back to English. A unit test runs every template against a sample message. Longer term the backend could send a message code plus parameters (follow-up if the list grows). The PDF report text from `pce/report.py` is out of scope.

## Acceptance Criteria

- [ ] #1 In the Italian UI every check title and detail produced by `pce/analysis.py` shows in Italian (unit test with one sample per template)
- [ ] #2 The AJ Bell-style case (statement uploaded, holdings not valued in CHF) no longer says that no document is a statement of assets (unit or E2E test)
- [ ] #3 English UI unchanged; existing E2E suite passes

## Implementation Notes

## Outcome

- **Status**: 

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
