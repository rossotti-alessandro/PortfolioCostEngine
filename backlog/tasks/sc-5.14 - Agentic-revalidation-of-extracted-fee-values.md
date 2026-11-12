---
id: SC-5.14
title: Agentic revalidation of extracted fee values
status: "Done"
assignee: []
owner: "Add agentic revalidation of extracted values"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-wc8huq"
pr: ""
created_date: "2026-11-12 17:50"
updated_date: "2026-11-12 19:17"
labels:
  - extraction
dependencies:
  - SC-5.8
parent_task_id: SC-5
priority: P1
paths_owned:
  - "backend/src/pce/extraction/revalidate.py"
  - "backend/src/pce/extraction/parsers.py"
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

- [x] #1 The graph never changes a value, label or box: every output value is a reader's value at its box (tested).
- [x] #2 A specialist can confirm or flag but never drop a figure; an unconfirmed value stays in review (tested).
- [x] #3 Arena scores the revalidation workflow and its ablations against finder + verify on the same pages, with 95% intervals and held-out pages.
- [x] #4 Off by default; finder + verify output is unchanged when revalidation is off (regression guard).

## Implementation Notes

- Stacked on PR #15 (SC-5.8, finder + verify), merged with main for the arena (SC-5.10). Merge #15 first.
- `revalidate.py`: plain-Python graph (state `Case`, nodes triage / readers / reconcile / critic / decide).
  Specialists return confirm / flag / abstain, never a number; the critic may only flag; only readers and
  arithmetic clear reading doubts; low OCR confidence is never cleared.
- App: `parsers._cross_check` runs the deterministic page checks when `PCE_REVALIDATE=1` (off by default).
- Lab: `data/specimens/arena/revalidate_lab.py` plugs in RapidOCR, docTR, PaddleOCR-VL rows (stored lab
  outputs) and replays the Qwen3-4B critic from `agent.py`'s log; `run.py` scores five variants.
- `run.py` / `agent.py` use this checkout's finder harness when present (no separate `var/arena/wt`).

## Outcome

- **Status**: completed
- 63 pages, 899 fees, all variants keep 90% of fees. Wrong accepted / review: finder + verify 5.9% / 18%;
  arithmetic only 5.8% / 17% (9 doubtful values confirmed, all right); readers + arithmetic 6.3% / 14%;
  full graph with critic 4.6% / 34% (29% if the critic ignores zeros), about 40 s/page CPU.
- `python -m pce.evaluation` (SYNTHETIC, digital + scan): identical with revalidation on and off, gates pass.
- Recommendation in `docs/research/REVALIDATION_PROTOCOL.md`: turn arithmetic on in the app; keep the
  critic optional for local installs; next levers Jev review ranking and a stronger second reader.

## Issues Encountered

- Extra readers confirm digits, not meaning: they accepted a footnote marker glued to a figure and a
  scan value under a misread label. Letting them clear low OCR confidence made it worse, so it is excluded.
- The critic run competes for the same 4 cores as the harness: 63 pages took about an hour.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-wc8huq | 32fa791 | 2026-11-12 | feat(extraction): revalidation graph that confirms or flags values |
| claude/project-thread-wc8huq | 0fba860 | 2026-11-12 | feat(arena): score the revalidation graph and its ablations |
| claude/project-thread-wc8huq | 80bb44a | 2026-11-12 | docs(research): extraction and revalidation protocol with arena scores |
