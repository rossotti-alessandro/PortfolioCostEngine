---
id: SC-9.12
title: Sideways phone photos: benchmark variant and orientation fix
status: "Done"
assignee: []
owner: "Prove and raise accuracy on realistic portfolios"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-12ht53"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/76"
created_date: "2026-11-25 22:45"
updated_date: "2026-11-26 00:08"
labels:
  - evaluation
  - extraction
dependencies: []
parent_task_id: SC-9
priority: P1
paths_owned:
  - "backend/src/pce/extraction/photo.py"
  - "backend/src/pce/extraction/layout.py"
  - "backend/src/pce/finance/money.py"
  - "backend/tests/test_engine.py"
  - "backend/src/pce/evaluation/realistic/**"
  - "backend/tests/test_photo.py"
  - "docs/research/REALISTIC_BENCHMARK.md"
spec_ref: docs/research/REALISTIC_BENCHMARK.md
rule_refs: [".claude/rules/extraction.md"]
---

> **One-liner**: A statement photographed with the phone held sideways (no EXIF rotation flag) read 0 of 15 holdings; turn such pages so the text runs across, and keep the case in the benchmark.

## Description

### Context
Widening the realistic benchmark (Ale, 2026-11-25: "review and test more and more"). `photo.clean_photo`
applies the EXIF flag only. Many phones and messaging apps strip it, so a landscape shot arrives with the
text running top to bottom. Tested 2026-11-25: 90 and 270 degrees read 0 of 15 holdings; 180 degrees
reads 15 of 15 (the OCR reader rights upside-down lines).

### User Flow Impact
Sideways photos uploaded from the camera flow read like upright ones.

### Performance / Efficiency Impact
One ink profile on an 800 px copy per photo: a few milliseconds.

### Proposed Approach
1. `photo._text_horizontal`: compare the ink profile across rows and across columns; if columns swing
   more, turn the page 90 degrees.
2. Benchmark variant `photo_sideways` (pages alternately 90 and 270 degrees), same gates as `photo`.

### Risks & Follow-ups
A page that is mostly a wide table with few text lines could be misjudged; checked on 288 benchmark photos
(4 turns each): 287 right.

## Acceptance Criteria

- [x] #1 Unit test: a page photographed at 90 and 270 degrees comes out with text running across
- [x] #2 Benchmark `photo_sideways` reads holdings like `photo`; `photo` and `photo_hard` do not drop

## Implementation Notes

## Outcome

- **Status**: completed

Benchmark 2026-11-26 (`--n 18`, report in `docs/research/REALISTIC_BENCHMARK.md`): sideways photos read
100% of holdings and 98.96% of fees (before: 0 holdings on a sideways page); dark photos holdings
63.8 -> 78.3%, fees 51.0 -> 87.5%; phone photos fees 99.0 -> 100%. Wrong values without a review flag: 0 in
every condition (dark photos were 1.2%). Also: RapidOCR line classifier off (it flipped upright lines on
dark photos), RapidOCR switches no longer leak between calls, `parse_amount` rejects non-thousands digit
groups ("7.815.22"). Tests: `test_photo.py` (sideways, upside down, switch leak), `test_engine.py`.
Follow-up: upside-down pages from a scanner (not photos) are not turned.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-12ht53 | 537203a | 2026-11-25 | turn sideways and upside-down photos upright; reject 7.815.22 |
| claude/project-thread-12ht53 | f45c083 | 2026-11-26 | sparse sideways pages; OCR switches no longer leak |
| claude/project-thread-12ht53 | 970a6fe | 2026-11-26 | RapidOCR line classifier off by default |
