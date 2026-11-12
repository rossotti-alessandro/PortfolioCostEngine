---
id: SC-5.16
title: "Read every holding on real statements: cash, bonds, shorts, second client"
status: "In Progress"
assignee: []
owner: "Audit production readiness and close gaps"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-sdc7fx"
pr: ""
created_date: "2026-11-12 21:55"
updated_date: "2026-11-12 22:57"
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

- [ ] #1 Fidelity US sample: 30 of 34 holdings or better; AJ Bell: first client's AUM within 1% or a two-client warning
- [ ] #2 Synthetic prospects and Fidelity UK unchanged (`pce.evaluation` gates pass, score.py row identical)

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
