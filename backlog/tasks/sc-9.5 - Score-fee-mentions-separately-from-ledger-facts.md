---
id: SC-9.5
title: Score fee mentions separately from ledger facts
status: "Done"
assignee: []
owner: "Build end-to-end accuracy protocol"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-uk1c1t"
pr: ""
created_date: "2026-11-11 22:20"
updated_date: "2026-11-11 22:17"
labels:
  - qa
dependencies: []
parent_task_id: SC-9
priority: P2
paths_owned:
  - "backend/src/pce/evaluation/**"
  - "backend/tests/evaluation/**"
  - "docs/EVALUATION_PROTOCOL.md"
spec_ref: docs/EVALUATION_PROTOCOL.md
rule_refs:
  - ".claude/rules/testing.md"
---

> **One-liner**: A `fee_mention` (a fee the finder saw but the ledger does not use yet) must not count against precision, and its recall should be visible on its own.

## Description

### Context

The extraction-strategy work (SC-5.8, PR #15) adds facts of kind `fee_mention`. The SC-9.1 scorer counts
every fact kind on the synthetic corpora, so mentions lower precision there, while on ocrbench only
ledger kinds are scored, so the finder's recall is invisible. PR #15 carries a workaround in
`parsers._cross_check` that costs mention recall only to protect synthetic precision.

### User Flow Impact

None in the app. The evaluation report gains a `mention recall` column.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. `runner.evaluate`: leave `fee_mention` out of the scored facts, provenance and portfolio input.
2. Score mentions on their own with `score(..., exhaustive=False)` and report `mention_recall`.
3. One column in the report, one line in the protocol doc, one test.

### Risks & Follow-ups

After merge, SC-5.8 may drop its finder-only workaround.

## Acceptance Criteria

- [x] #1 Adding fee_mention facts never changes precision, wrong values or portfolio results (tested)
- [x] #2 The report shows mention recall per corpus

## Implementation Notes

## Outcome

- **Status**: completed

`runner.evaluate` scores `fee_mention` facts apart (`mention_recall`) and keeps them out of precision,
provenance and the portfolio input. Test `test_fee_mentions_never_change_ledger_scores` failed first
(the analysis raised on mention facts) and passes now.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-uk1c1t | 322782e | 2026-11-11 | score fee mentions apart, mention_recall |
