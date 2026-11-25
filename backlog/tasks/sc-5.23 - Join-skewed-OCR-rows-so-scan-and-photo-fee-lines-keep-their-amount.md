---
id: SC-5.23
title: Join skewed OCR rows so scan and photo fee lines keep their amount
status: "In Progress"
assignee: []
owner: "Prove and raise accuracy on realistic portfolios"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-12ht53"
pr: ""
created_date: "2026-11-25 21:40"
updated_date: "2026-11-25 22:07"
labels:
  - extraction
  - ocr
dependencies: []
parent_task_id: SC-5
priority: P0
paths_owned:
  - "backend/src/pce/extraction/layout.py"
  - "backend/src/pce/extraction/vocab.py"
  - "backend/src/pce/extraction/parsers.py"
  - "backend/tests/test_ocr_rows.py"
spec_ref: docs/research/REALISTIC_BENCHMARK.md
rule_refs: [".claude/rules/extraction.md"]
---

> **One-liner**: On slightly skewed scans and phone photos the fee amount lands on its own OCR line and the fee is lost; join it back to its label so scan and photo fee recall rises toward 95%.

## Description

### Context
The realistic benchmark (SC-9.8, 2026-11-25) reads 100% of fees on digital statements but 87.5% on office
scans and 91.7% on phone photos. Of the 30 misses on scan, photo and annotated variants, 13 are a label line
with no amount next to an amount-only line: RapidOCR boxes each text run and `layout._group` joins runs by
vertical centre within 4 pt, while skew drops the right-hand amount 4-5 pt. Six more are a whole fee table on
one photo lost because OCR read "Commissioní" for the section header. The rest are labels covered by pen
marks or garbled words.

### User Flow Impact
Fewer fees left for the analyst to add by hand on scanned and photographed statements.

### Performance / Efficiency Impact
No measurable impact (one overlap check per OCR text run).

### Proposed Approach
1. `layout._same_row`: on RapidOCR pages also join a run that overlaps the row by at least 60% of its height
   and sits beside, not under, the row's cells. Digital pages keep the centre rule.
2. `vocab.ocr_clean`: map í/ì/ï to i before fee label and fee section matching (no fee word needs them).
3. Re-run the realistic benchmark and the ocrbench fee pages; no regression allowed.

### Risks & Follow-ups
Tight tables with rows closer than 40% of a text height could join two rows; the "beside" rule and the 60%
threshold guard against it, and the benchmarks measure it.

## Acceptance Criteria

- [ ] #1 Unit tests: a dropped or raised amount joins its label; stacked cells in one column stay apart; digital grouping unchanged
- [ ] #2 Realistic benchmark fee recall on scan and photo goes up, wrong-unflagged stays ≤ 1%
- [ ] #3 ocrbench fee pages: no drop in recall, no rise in wrong values

## Implementation Notes

## Outcome

- **Status**: partial

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
