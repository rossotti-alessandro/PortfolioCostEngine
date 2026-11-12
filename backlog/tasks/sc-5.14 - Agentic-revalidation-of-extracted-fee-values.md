---
id: SC-5.14
title: Agentic revalidation of extracted fee values
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-12 18:05"
updated_date: "2026-11-12 18:05"
labels:
  - extraction
dependencies:
  - SC-5.8
parent_task_id: SC-5
priority: P1
paths_owned:
  - "backend/src/pce/extraction/revalidate.py"
  - "backend/tests/test_revalidate.py"
  - "data/specimens/arena/**"
  - "docs/research/REVALIDATION_PROTOCOL.md"
spec_ref: docs/research/REVALIDATION_PROTOCOL.md
rule_refs: [".claude/rules/extraction.md", ".claude/rules/privacy.md", ".claude/rules/finance.md"]
---

> **One-liner**: After the reader has extracted a page, a supervisor sends each doubtful value to
> specialists (more readers, arithmetic reconciliation, a local language-model critic) that may only
> confirm or flag it, so fewer values need an analyst and no wrong value is accepted silently.

## Description

### Context
SC-5.8 (PR #15) gives finder + verify: 90% of fees found on the 63 hand-checked pages, 5.9% of accepted
values wrong, 18% sent to review. The workflow arena (SC-5.10, PR #22) showed two things: a single LLM
step that may drop figures loses 175 real fees, and two independent readers that must agree accept no
wrong value but send 62% of figures to review because the second reader (PaddleOCR-VL) is weak. Ale asked
for the full agentic revalidation workflow and for the proper protocol (order, parallelism, validation).

### User Flow Impact
None by default. The analyst sees the same review queue; with revalidation on, each flagged value carries
the specialist that flagged or confirmed it, and fewer values wait for review.

### Performance / Efficiency Impact
Deterministic specialists add milliseconds per page. The language-model critic is optional (lab venv,
local Qwen3-4B, about 40 s per page on 4 CPU cores) and runs only on the candidates the supervisor routes
to it. Off on Render free (0.15 CPU).

### Proposed Approach
1. `docs/research/REVALIDATION_PROTOCOL.md`: the end-to-end protocol (steps, what runs in parallel,
   validation layers, how it is scored).
2. `backend/src/pce/extraction/revalidate.py`: a small explicit graph (state, nodes, routing) with a
   supervisor, pluggable specialists and a decision node. Specialists return confirm / flag / abstain,
   never a value. Pure Python, no new dependency.
3. Deterministic specialists in the backend: arithmetic reconciliation (components sum to a total, KID
   percentage matches its amount on the stated investment).
4. Lab specialists in `data/specimens/arena/`: more readers from stored lab outputs (RapidOCR, docTR,
   PaddleOCR-VL table rows) and the local language-model critic (flag only).
5. Score the graph and its ablations in the arena next to finder + verify, with intervals and held-out pages.

### Risks & Follow-ups
- Readers that share a rendering can make the same mistake: "independent" means a different engine family.
- Cross-document checks (the same ISIN's fee in KID, factsheet and statement) need prospect-level state:
  follow-up story.

## Acceptance Criteria

- [ ] #1 The graph never changes a value, label or box: every output value is a reader's value at its box (tested).
- [ ] #2 A specialist can confirm or flag but never drop a figure; an unconfirmed value stays in review (tested).
- [ ] #3 Arena scores the revalidation workflow and its ablations against finder + verify on the same pages, with 95% intervals and held-out pages.
- [ ] #4 Off by default; finder + verify output is unchanged when revalidation is off (regression guard).

## Implementation Notes

## Outcome

- **Status**: 

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
