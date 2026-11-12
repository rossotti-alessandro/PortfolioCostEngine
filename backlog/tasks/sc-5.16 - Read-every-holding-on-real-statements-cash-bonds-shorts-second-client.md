---
id: SC-5.16
title: "Read every holding on real statements: cash, bonds, shorts, second client"
status: "Done"
assignee: []
owner: "Audit production readiness and close gaps"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-sdc7fx"
pr: ""
created_date: "2026-11-12 21:55"
updated_date: "2026-11-12 23:26"
labels:
  - extraction
dependencies: []
parent_task_id: SC-5
priority: P1
paths_owned:
  - "backend/src/pce/extraction/parsers.py"
  - "backend/tests/test_real_documents.py"
spec_ref: data/specimens/statements/RESULTS.md
rule_refs:
  - ".claude/rules/extraction.md"
---

> **One-liner**: Close the holdings gaps SC-9.6 measured on real statements, so AUM is right instead of
> only flagged.

## Description

### Context

`data/specimens/statements/RESULTS.md` (2026-11-12): Fidelity US sample 17 of 34 holdings read (bonds with a
maturity column, a short position with a negative value, "Other" holdings, the second row of a fund table);
AJ Bell demo report misses cash and off-panel policy lines on the overview and merges a second client's
GIA into the first client; Edward Jones annotated sample is classified as a cash statement with no
holdings. Alarms now fire on the first two, so the errors are visible, not silent.

### User Flow Impact

Fewer alarms to resolve by hand; AUM right on more statements.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Bond rows: "Description | Maturity | Quantity | Price | Market value": accept qty x price / 100 = value.
2. Negative values (short positions) keep their sign.
3. Overview cash and policy lines ("SIPP cash", off-panel) become cash / other holdings when no table covers them.
4. Two client names on overview pages: warn "this file holds more than one client" and stop the merge.
5. Re-run `data/specimens/statements/score.py`; no regression on Fidelity UK or the synthetic prospects.

### Risks & Follow-ups

Every rule must be checked against the synthetic prospects and the arena pages to avoid false holdings.

## Acceptance Criteria

- [x] #1 Fidelity US sample: 30 of 34 holdings or better; AJ Bell: first client's AUM within 1% or a two-client warning
- [x] #2 Synthetic prospects and Fidelity UK unchanged (`pce.evaluation` gates pass, score.py row identical)

## Implementation Notes

Owned paths also include `backend/src/pce/analysis.py` (the `second_person:*` check) and
`data/specimens/statements/RESULTS.md`. Proposed approach steps 1, 2 and 4 done; step 3 (reading the AJ Bell
overview's cash and off-panel policy lines) not done: the two alarms tell the analyst, and a rule that turns
overview lines into holdings risks double counting on statements whose tables already include them.

## Outcome

- Fidelity US sample: 34 of 34 holdings (was 17), AUM 278,922.20 exact (was 35% short), reconciliation
  passes. Rows now read: bonds priced per 100 of face value, short positions, prices with a footnote
  letter, three-decimal quantities settled by quantity x price = value. Section subtotals and
  transaction-table totals are no longer added up as the statement total.
- AJ Bell demo report: new failing check `second_person:*` when a page header names a different person
  (the check shows the page, never the name). AUM still 20% short, now with two alarms.
- Fidelity UK and the synthetic prospects unchanged (`pce.evaluation`: P-1042 and P-2077 digital 100%,
  scans 85.5% and 96.2%, wrong 0). Silent AUM errors on the four statements: 0.
- Edward Jones (classified as a cash statement) left open.

## Issues Encountered

The first synthetic test passed against the old code by coincidence (each section had its own header row),
so it was rewritten to mirror the real layout: two sections under one header.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-sdc7fx | 906aa46 | 2026-11-12 | fix(extraction): read bonds, shorts and subtotals on US statements |
| claude/project-thread-sdc7fx | 8ac5009 | 2026-11-12 | feat(analysis): alarm when one file holds two clients' statements |
