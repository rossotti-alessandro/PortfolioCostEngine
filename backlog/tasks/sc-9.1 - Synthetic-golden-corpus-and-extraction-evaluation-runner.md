---
id: SC-9.1
title: Synthetic golden corpus and extraction evaluation runner
status: "Done"
assignee: []
owner: "Build end-to-end accuracy protocol"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-uk1c1t"
pr: ""
created_date: "2026-11-06 15:05"
updated_date: "2026-11-11 19:09"
labels:
  - qa
dependencies:
  - SC-5.1
parent_task_id: SC-9
priority: P0
paths_owned:
  - "backend/tests/evaluation/**"
  - "data/synthetic/golden/**"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs:
  - ".claude/rules/testing.md"
---

> **One-liner**: Measure extraction accuracy per field so engine choices are made on evidence.

## Description

### Context

No corpus.

### User Flow Impact

No direct change; quality numbers in every extraction PR.

### Performance / Efficiency Impact

Runs in minutes on a laptop.

### Proposed Approach

1. Generated synthetic statements with labels (digital + image-only + hard negatives)
2. Metrics: exact amount, ISIN, date, row association, bbox IoU, abstention
3. Report under artifacts/eval/<ts>/

### Risks & Follow-ups

See `docs/adr/0003-document-extraction-and-ocr.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [x] #1 Runner produces report.md with per-field metrics
- [x] #2 A deliberately wrong extractor scores lower (sanity check)

## Implementation Notes

Owned paths: `backend/src/pce/evaluation/**` (new package: the scorer is imported by other strategies,
so it lives in the app package, not under tests), `backend/tests/evaluation/**`, `docs/EVALUATION_PROTOCOL.md`.
No `data/synthetic/golden/` files: synthetic labels are built in code from the generator inputs
(`demo/spec.py`, `demo/archetypes.py`), so they cannot drift from the documents. Matching rule and
metrics agreed with the "Define document extraction strategy" thread; UI trace E2E belongs to the
"Trace numbers back to source documents" thread (PR #13), referenced from the protocol as stage 9.

## Outcome

- **Status**: completed

`python -m pce.evaluation` scores any strategy on 4 corpora (2 SYNTHETIC prospects, 514 hand-checked
real fee figures, manifest labels) and 2 variants (digital, image-only scan) through 8 stages:
classification, fact matching (precision/recall/wrong value/missing as zero), bbox, provenance against
the file, portfolio totals, invariants, detectability, review load and speed. Gates in
`runner.GATES`. Baseline passes on synthetic; sabotaged fails. Results and findings in
`docs/EVALUATION_PROTOCOL.md` (real-document recall 4.3%, OCR drops a position on scans, tier rates
cite the label box on one price list).

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-uk1c1t | e6bf3a3 | 2026-11-11 | evaluation package, golden labels, runner, tests |
