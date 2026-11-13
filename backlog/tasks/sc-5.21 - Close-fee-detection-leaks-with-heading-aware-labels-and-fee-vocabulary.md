---
id: SC-5.21
title: Close fee detection leaks with heading-aware labels and fee vocabulary
status: Done
assignee: []
owner: "Raise fee detection toward 100%"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-o8nuus"
pr: ""
created_date: "2026-11-13 16:55"
updated_date: "2026-11-13 17:37"
labels:
  - extraction
dependencies: []
parent_task_id: SC-5
priority: P1
paths_owned:
  - backend/src/pce/extraction/finder.py
  - backend/src/pce/extraction/parsers.py
  - backend/src/pce/extraction/vocab.py
  - backend/src/pce/extraction/verify.py
  - backend/tests/test_fee_detection_leaks.py
  - data/specimens/strategies/**
spec_ref: docs/research/EXTRACTION_STRATEGY.md
rule_refs: [".claude/rules/extraction.md", ".claude/rules/finance.md"]
---

> **One-liner**: Find more of the fees printed on a page, and name each one with its heading, by fixing the measured causes of misses in the finder and cross-check, without adding wrong values.

## Description

### Context
An error analysis on 2026-11-13 (thread "Raise fee detection toward 100%", report
https://claude.ai/artifact/PbhEJ9Jb2etjCK3fPP9Gmw) split the 120 fees the app misses on the 53 digital
benchmark pages (813 fees, 85.2% found): 15 total rows dropped by the `TOTAL_WORDS` rule in
`parsers._cross_check`; 16 other values dropped; 33 right value in the right box whose label lacks its
section or column heading; 25 numbers not recognised as fees (vocabulary such as "fremde Spesen",
"Ausgabeaufschlag", bracketed amounts); 14 put under the wrong row; 3 unreadable; 14 are scorer effects.

### User Flow Impact
The analyst sees more of the printed fees as clickable figures, each labelled with its full context
(for example "Transaction fees › Equities group 1 › Minimum" instead of "Minimum").

### Performance / Efficiency Impact
Rule and geometry changes only; no new model. Target: no measurable change in seconds per page.

### Proposed Approach
1. Keep finder total rows as `fee_mention` (not in totals, so no double count) instead of dropping them.
2. Find and fix the other drops (KID tables inside prospectuses, structured-product KIDs).
3. Heading-aware labels: carry the section heading and column header into the finder label (parent-child context).
4. Fee vocabulary per language (EN, DE, FR, IT) for the missed terms; read bracketed amounts as magnitudes.
5. Score with `data/specimens/strategies/run.py` and `python -m pce.evaluation` before and after.

### Risks & Follow-ups
New vocabulary can pull in non-fee numbers: the wrong-value share must not rise. Table structure
(wrong row in tier tables) and scans are follow-ups (second reader, option B).

## Acceptance Criteria

- [x] #1 Production extract() finds more gold fees on the 53 digital pages than 85.2%, measured with the strategies scorer, and on the 19 held-out round-2 pages.
- [x] #2 Wrong values (all, and "verified") do not rise on the same pages; synthetic corpora stay 100%/100% in `pce.evaluation`.
- [x] #3 Unit tests cover each new rule with SYNTHETIC lines.

## Implementation Notes

Owned paths used: `backend/src/pce/extraction/finder.py`, `backend/src/pce/extraction/parsers.py`,
`backend/tests/test_fee_detection_leaks.py`. The label swap (finder label over the parser label when both
agree) was tried and reverted: parser labels feed the ledger, the client report and the Italian fee names.
The finder's label with section and column stays in `extra["finder_label"]`; showing it in the review UI
is a frontend follow-up.

## Outcome

- **Status**: completed
- Production `extract()` on the ocrbench gold, strategies scorer, before -> after:
  - 54 digital pages (813 fees): found 85.2% -> 90.2%; "verified" wrong 7.4% -> 7.4%.
  - 19 round-2 pages never used for tuning: 86.1% -> 91.0%.
  - all 63 pages incl. 9 simulated scans: 82.2% -> 86.7%. Scans unchanged at 53.5% (OCR is the limit).
  - Finder alone: 92.0% -> 95.6%; wrong values 129 -> 130.
- The scorer counts 3 more "wrong" values on the app; each new one was checked on the page: all are correct
  values (a repeated printed value matched greedily to another gold line, or "FUNDS" vs "Money market funds").
- `pce.evaluation` synthetic P-1042 and P-2077: recall 100%, wrong 0 (sabotaged controls still fail).
- Statements (`data/specimens/statements/score.py`): unchanged; Fidelity US 34/34, no silent AUM error.
- Speed: median 0.62 s/page, unchanged.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-o8nuus | 05e134d | 2026-11-13 | Add SC-5.21 |
| claude/project-thread-o8nuus | d6d3dfd | 2026-11-13 | Keep finder totals, find fees by heading |
| claude/project-thread-o8nuus | a7bec77 | 2026-11-13 | Returns quoted around costs are not fees |
| claude/project-thread-o8nuus | c69bfb5 | 2026-11-13 | Margin and debit interest paid is a cost |

## Issues Encountered

- `tests/test_revalidate.py` selects facts by exact label; the label swap broke it, which is how the
  ledger-label dependency surfaced.
