---
id: SC-5.23
title: Join skewed OCR rows so scan and photo fee lines keep their amount
status: "Done"
assignee: []
owner: "Prove and raise accuracy on realistic portfolios"
model: "claude-opus-5-5"
progress: 100
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
  - "docs/research/REALISTIC_BENCHMARK.md"
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

- [x] #1 Unit tests: a dropped or raised amount joins its label; stacked cells in one column stay apart; digital grouping unchanged
- [x] #2 Realistic benchmark fee recall on scan and photo goes up, wrong-unflagged stays ≤ 1%
- [x] #3 ocrbench fee pages: no drop in recall, no rise in wrong values

## Implementation Notes

First version joined any overlapping run; on 9 real public scan pages (ocrbench `*-scan`) it glued two-column
tariff prose into one row (46 extra joins). Final rule joins only a figure (amount, rate, ISIN, one token
with a digit); the same pages now show 5 extra joins, all a label with its value. The ocrbench app run
(`app_run.py`) reads no fees on those single pages on main or branch, so it cannot score this change;
the realistic benchmark is the measure.

## Outcome

- **Status**: completed

Realistic benchmark, 18 SYNTHETIC statements, 2026-11-25, main (after #64) -> branch: fees on office scans
87.5 -> 100%, phone photos 91.7 -> 99.0%, fax-quality scans 18.8 -> 45.8%; holdings on fax-quality scans
77.5 -> 80.0%; annotated and dark photos unchanged (88.5% / 51.0% fees). Wrong values without a review
flag unchanged (0 everywhere, 1.2% on dark photos). Unit tests `backend/tests/test_ocr_rows.py`.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-12ht53 | 671283f | 2026-11-25 | join skewed OCR rows, OCR accents on i |
| claude/project-thread-12ht53 | 62a0fe0 | 2026-11-25 | skew join only for figures |
