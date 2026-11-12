---
id: SC-5.10
title: Workflow arena - compare complete extraction workflows end to end
status: "Done"
assignee: []
owner: "Compare complete extraction workflows"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-rfm5yy"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/22"
created_date: "2026-11-12 13:10"
updated_date: "2026-11-12 15:08"
labels:
  - extraction
  - qa
dependencies:
  - SC-5.7
parent_task_id: SC-5
priority: P1
paths_owned:
  - "data/specimens/ocrbench/**"
  - "data/specimens/arena/**"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs:
  - ".claude/rules/extraction.md"
  - ".claude/rules/privacy.md"
  - ".claude/rules/finance.md"
---

> **One-liner**: Run several complete extraction workflows, including an agentic one, on the same pages and SYNTHETIC prospects, and score them side by side with the accuracy protocol.

## Description

### Context

The model lab (SC-5.7) compares single models page by page. Ale asked whether we test complete workflows,
agentic or not, against each other. Today only the app's own workflow is scored end to end
(`pce.evaluation`), and the finder + verify workflow (SC-5.8, PR #15) is scored by a separate script.

### User Flow Impact

None directly. It decides which workflow the upload pipeline runs and how much reaches the analyst's review queue.

### Performance / Efficiency Impact

Benchmark only, run offline on CPU. Production code is unchanged.

### Proposed Approach

1. One runner that feeds every workflow the same inputs (54 real ocrbench pages, SYNTHETIC P-1042 and P-2077,
   digital and scanned) and scores them with `pce.evaluation` plus per-page fee recall/precision.
2. Workflows: (1) app today; (2) finder + verify; (3) finder + table structure from a layout model;
   (4) finder + a local vision model as second reader on scans and tables; (5) agentic: a local language
   model chooses tools, compares readers and flags doubts, but never writes or computes a number
   (every value must come from a tool with page and box).
3. Lab tab "Workflows": scores side by side, per-page differences, cost and speed, failure examples.

### Risks & Follow-ups

CPU only: the vision and agentic workflows run on a page subset. A local language model can still invent text;
the runner rejects any value not present in a tool output at the cited box.

## Acceptance Criteria

- [x] #1 At least five complete workflows scored on the same inputs with the same scorer
- [x] #2 The agentic workflow never emits a number that no tool read at its cited box (tested)
- [x] #3 Lab shows the comparison with per-page drill-down; synthetic data labelled

## Implementation Notes

- `data/specimens/arena/run.py` scores every workflow with the SC-5.8 strategy scorer
  (`data/specimens/strategies/score.py`), read-only from a checkout of PR #15 at `var/arena/wt`
  (the harness dumps each workflow's predictions there). Whole-prospect rows come from
  `python -m pce.evaluation` results.json files passed with `--portfolio`.
- `data/specimens/arena/agent.py`: Qwen3-4B-Instruct-2507 (Apache-2.0, bf16, CPU, local weights only)
  reviews the finder + verify candidates by id, with two deterministic tools over stored lab outputs
  (RapidOCR re-read of the value box; PaddleOCR-VL table row). `apply_decisions` builds the output from the
  candidates, so the model can drop or flag a figure but never write or change one (AC #2,
  `test_agent.py`, 4 tests). `flag_only` replays a run with "not a fee" turned into "send to review".
- Workflow 4 is the vision reader on its own (PaddleOCR-VL rows anchored to text-layer boxes) on the 23-page
  core set; the vision model as second reader is in the model lab (`hybrid_vlm`).
- Lab: new "Workflows" tab (scores, SYNTHETIC whole-portfolio table, per-page drill-down with boxes).
- Qwen3-1.7B (fp32) was tried first and dropped true fees erratically; its results were discarded.

## Outcome

- **Status**: Done. 10 workflows on 63 pages (899 hand-checked fees); see `data/specimens/arena/RESULTS.md`.
- Finder + verify stays the best trade-off: P 82%, R 90%, 5.9% wrong values accepted, 1.5 s/page.
- Agentic review (drop mode): P 90%, R 71%. It removes false figures but also 175 real fees, a third of
  them zero charges. Flag-only mode keeps recall at 90% and lowers wrong accepted values to 4.5%, but sends
  39% of figures to review (18% without the agent) and costs about 40 s/page on CPU.
- Ensembles (`ensembles.py`): when finder + verify and the independent vision reader must agree on value and
  spot, 0 wrong values were accepted on the 23 pages both ran (finder + verify alone: 3.1%), recall 91%; adding
  vision-only figures for review lifts recall to 94%. Cost: 62-65% of figures go to review, because the vision
  reader finds only 64% of fees. A faster, stronger second reader (table structure) is the next lever.
- Validation in RESULTS.md: 95% bootstrap intervals over pages, held-out scores without the 3 pages used to
  tune the agent prompt (agent recall 70% vs 71% overall), and recall by document type.
- Recommendation: do not put the agent in the app now. If used, only in flag mode, after zero-charge
  handling is fixed in the prompt or by rule.
- Whole-portfolio results (SYNTHETIC P-1042, P-2077) are identical before and after SC-5.8, because finder
  figures are `fee_mention` and do not enter totals.

## Issues Encountered

- CPU contention made early timings unreliable; heavy jobs were run one at a time with `OMP_THREAD_LIMIT=1`.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-rfm5yy | 21b4199 | 2026-11-12 | Agent, tests, arena scorer, lab tab (WIP) |
