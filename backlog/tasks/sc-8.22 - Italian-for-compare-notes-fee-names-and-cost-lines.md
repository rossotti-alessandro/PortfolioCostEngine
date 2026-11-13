---
id: SC-8.22
title: Italian for Compare notes, fee names and cost lines
status: "Done"
assignee: []
owner: "Validate accuracy and speed up processing"
model: "claude-opus-5-5"
progress: 100
branch: "claude/sc-8.22-italian-notes"
pr: ""
created_date: "2026-11-13 13:32"
updated_date: "2026-11-13 13:37"
labels:
  - ui
  - i18n
dependencies: []
parent_task_id: SC-8
priority: P1
paths_owned:
  - "frontend/src/lib/it.ts"
  - "frontend/src/lib/i18n.ts"
  - "frontend/src/lib/i18n.test.ts"
  - "frontend/src/pages/Compare.tsx"
  - "frontend/src/pages/Costs.tsx"
  - "frontend/src/pages/Report.tsx"
  - "frontend/src/pages/Review.tsx"
  - "frontend/src/components/Trace.tsx"
  - "frontend/src/components/ReviewPoints.tsx"
spec_ref: docs/research/UX_RECOMMENDATIONS.md
rule_refs: [".claude/rules/frontend.md"]
---

> **One-liner**: The Italian UI no longer shows English in the Compare notes ("why the saving is a bound"),
> fee names, proposal lines, review points and the report's open items.

## Description

### Context
A crawl of every analyst page in Italian (Playwright, both SYNTHETIC prospects) found English text from
the server: the saving caveats, the stamp-duty exclusion reason, the fee taxonomy names
(`fee_label`), proposal lines ("· product costs", "· management fee (EAM)", "Swiss VAT 8.1% on …") and
cost lines inside review points and the report.

### User Flow Impact
Those texts show in Italian. Labels printed on the client's own documents stay as printed.

### Performance / Efficiency Impact
No measurable impact (string lookups).

### Proposed Approach
1. `it.ts`: every `label_en` of `data/taxonomy/fee_taxonomy.csv` with its `label_it`, the caveats and the
   stamp-duty reason, and patterns for the server-built lines ("X · Y" split and translated per part).
2. Pages pass those server strings through `tm()`. `translate()` prefers a whole known sentence.
3. Test: every taxonomy label has Italian (reads the CSV), every new pattern has a sample.

### Risks & Follow-ups
- The document catalogue table (Catalogue page) is reference data in English; not in scope.

## Acceptance Criteria

- [x] #1 The Italian crawl shows no server English on Compare, Costs, Report and review points (only document-printed labels)
- [x] #2 Vitest i18n tests pass, including the taxonomy coverage test; English UI unchanged

## Implementation Notes

## Outcome

- **Status**: Done.
- `it.ts` now covers every `label_en` in `data/taxonomy/fee_taxonomy.csv` (51 new entries), the saving
  caveats, the stamp-duty reason and the server-built proposal lines ("X · Y", VAT, "(maximum)").
- `translate()` prefers a whole known sentence before patterns.
- Compare, Costs, Report, Review, Trace and ReviewPoints pass server strings through `tm()`.
- Italian Playwright crawl of both SYNTHETIC prospects: remaining English lines are labels printed on
  the documents or typed as proposal inputs. The Catalogue reference table stays English (out of scope).
- Vitest: new taxonomy coverage test and pattern samples pass; English UI unchanged (`tm()` returns the
  input when the language is English).

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/sc-8.22-italian-notes | f50d12e | 2026-11-13 | Italian for Compare notes, fee names and cost lines |
