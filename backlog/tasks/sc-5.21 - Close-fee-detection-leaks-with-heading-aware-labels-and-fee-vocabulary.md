---
id: SC-5.21
title: Close fee detection leaks with heading-aware labels and fee vocabulary
status: "In Progress"
assignee: []
owner: "Raise fee detection toward 100%"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-o8nuus"
pr: ""
created_date: "2026-11-13 16:55"
updated_date: "2026-11-13 16:56"
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

- [ ] #1 Production extract() finds more gold fees on the 53 digital pages than 85.2%, measured with the strategies scorer, and on the 19 held-out round-2 pages.
- [ ] #2 Wrong values (all, and "verified") do not rise on the same pages; synthetic corpora stay 100%/100% in `pce.evaluation`.
- [ ] #3 Unit tests cover each new rule with SYNTHETIC lines.

## Implementation Notes

## Outcome

- **Status**: 

## Issues Encountered
