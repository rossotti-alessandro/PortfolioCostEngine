---
id: SC-5.17
title: "Read overview cash and policies, and annotated statement samples"
status: "Done"
assignee: []
owner: "Audit production readiness and close gaps"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-sdc7fx"
pr: ""
created_date: "2026-11-12 23:50"
updated_date: "2026-11-12 23:56"
labels:
  - extraction
dependencies: []
parent_task_id: SC-5
priority: P1
paths_owned:
  - "backend/src/pce/extraction/parsers.py"
  - "backend/tests/test_real_documents.py"
  - "data/specimens/statements/**"
spec_ref: data/specimens/statements/RESULTS.md
rule_refs:
  - ".claude/rules/extraction.md"
---

> **One-liner**: Close the two statement gaps SC-5.16 left open: cash and off-panel policies listed only on
> an overview page, and a statement read as a cash statement with no holdings.

## Description

### Context

`data/specimens/statements/RESULTS.md` after SC-5.16: the AJ Bell demo report's overview breakdown ("SIPP |
Cash | Assets | Total") lists account cash and two off-panel Prudential policies (68,093.85 + 76,029.56 GBP)
that no holdings table contains, so AUM is 20% short (alarmed). The Edward Jones annotated sample is
classified as a cash statement and no holdings are read.

### User Flow Impact

Fewer figures the analyst must type by hand; AUM right on more statements.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Overview breakdown tables "<account> | Cash | Assets | Total": each row's cash becomes a cash holding; its
   assets become a holding only when no holdings table closes with the same amount (no double counting).
   The rows' totals become the statement total.
2. Edward Jones: find why it is classified as a cash statement and read its holdings if the layout allows.
3. Re-run `score.py` and `pce.evaluation`; no regression.

### Risks & Follow-ups

A breakdown asset amount equal to a holdings-table total by coincidence would be dropped; the
reconciliation check would then fail, so the error is visible.

## Acceptance Criteria

- [x] #1 AJ Bell: the first client's cash and policies are read; the file's AUM equals the sum of its account totals, and the two-person alarm stays
- [x] #2 Edward Jones: holdings read, or the reason it cannot be documented in RESULTS.md
- [x] #3 Synthetic prospects, Fidelity US and Fidelity UK unchanged

## Implementation Notes

Owned paths also include `docs/READINESS.md` (G2 row). `parsers._account_breakdown` runs after the holdings
tables so it can tell assets already read from assets only the overview lists.

## Outcome

- AJ Bell demo report: 8 more holdings (5 account cash lines, 2 off-panel Prudential policies, the second
  client's cash). The file's AUM, 660,273.45 GBP, equals the sum of its account totals: the first client's
  618,520.40 plus the second client's 41,753.05. Reconciliation passes; the two-person alarm remains, and the
  analyst removes the second client's pages.
- Edward Jones: not fixed, by decision. The reasons are in RESULTS.md finding 4. With no holdings, the app
  already asks for a holdings statement, so the gap is visible.
- Fidelity US (34/34, exact), Fidelity UK and the synthetic prospects unchanged.

## Issues Encountered

None.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-sdc7fx | 9b39f76 | 2026-11-12 | feat(extraction): read cash and policies from account breakdowns |
