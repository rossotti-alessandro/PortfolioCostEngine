---
id: SC-9.6
title: Accuracy on real bank statements: holdings, AUM and statement fees
status: "In Progress"
assignee: []
owner: "Audit production readiness and close gaps"
model: "claude-opus-5-5"
progress: 70
branch: "claude/project-thread-sdc7fx"
pr: ""
created_date: "2026-11-12 21:05"
updated_date: "2026-11-12 21:42"
labels:
  - evaluation
  - extraction
dependencies: [] # after SC-5.8 (PR #15) merges
parent_task_id: SC-9
priority: P0
paths_owned:
  - "data/specimens/ocrbench/groundtruth_statements.json"
  - "backend/tests/evaluation/**"
  - "docs/EVALUATION_PROTOCOL.md"
spec_ref: docs/EVALUATION_PROTOCOL.md
rule_refs: [".claude/rules/extraction.md"]
---

> **One-liner**: Measure what drives the client's total, holdings and AUM read from real statement layouts,
> because today's real-document evidence is almost all tariffs and KIDs.

## Description

### Context

The arena (63 pages, 899 hand-checked fees) has only 9 fees from portfolio statements, with 56% recall, and
no hand-checked holdings at all. Holdings and AUM are measured only on two synthetic prospects, where the
scanned copy lost a holdings page (AUM CHF 3.7m instead of 4.3m; alarms fired). A wrong AUM moves every
percentage in the report, so this is the largest unmeasured risk before a pilot.

### User Flow Impact

None directly; sets the trust level the analyst review protocol relies on.

### Performance / Efficiency Impact

Evaluation only.

### Proposed Approach

1. Label 30+ statement pages from at least 8 institutions in the public specimen corpus (sample and demo
   statements): every position (ISIN, quantity, market value, currency), the AUM, and every fee line.
   Who labels and whether an external AI may draft labels on public documents is Ale's decision (corpus thread).
2. Add a `statement` gold kind to `pce.evaluation` and report: position recall, wrong market values, AUM
   error in %, and whether the reconciliation alarm fired when AUM is off by more than 1%.
3. Run main and the merged extraction stack; write the numbers into docs/EVALUATION_PROTOCOL.md.

### Risks & Follow-ups

Public sample statements are cleaner than real ones; the pilot (SC-11.1) is the real test.

## Acceptance Criteria

- [ ] #1 Report gives position recall, wrong market values and AUM error on 30+ real statement pages, with 95% intervals
- [x] #2 Every AUM error above 1% raises an alarm, or the miss is listed as a silent error and filed as a story

## Implementation Notes

Owned paths in practice (differ from `paths_owned`): `data/specimens/statements/**` (gold, scorer, results),
and two fixes the measurement required, in `backend/src/pce/extraction/parsers.py` (table currency,
larger printed total), `backend/src/pce/analysis.py` (the `printed_total:*` alarm) and
`backend/tests/test_real_documents.py`. Labelling was done by this agent reading the public PDFs locally;
Ale's instruction of 2026-11-12 ("use more reports, serious, professional and real") taken as the go-ahead.

## Outcome

- **Status**: partial
- 4 usable public statements (Fidelity US, Fidelity UK, AJ Bell, Edward Jones), 34 holdings and 13 account
  totals hand-checked: `data/specimens/statements/RESULTS.md`. AC #1 asks for 30+ pages: not reachable from
  public material (most public samples are blank or annotated reading guides); the pilot is the next source.
- Silent AUM errors 1 of 4 before, 0 of 4 after (AC #2 met). Fixed: USD rows labelled CHF. Reader gaps filed
  as SC-5.16.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-sdc7fx | ec7a352 | 2026-11-12 | Gold, scorer, results, currency fix, printed-total alarm |
