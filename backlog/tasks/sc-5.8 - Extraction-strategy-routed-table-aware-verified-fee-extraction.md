---
id: SC-5.8
title: Extraction strategy - routed, table-aware, verified fee extraction
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-11 19:15"
updated_date: "2026-11-11 19:15"
labels:
  - extraction
dependencies: []
parent_task_id: SC-5
priority: P0
paths_owned:
  - "backend/src/pce/extraction/**"
  - "backend/tests/unit/extraction/**"
  - "backend/tests/test_extraction_strategy*.py"
  - "data/specimens/strategies/**"
  - "docs/research/EXTRACTION_STRATEGY.md"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs:
  - ".claude/rules/extraction.md"
  - ".claude/rules/finance.md"
  - ".claude/rules/privacy.md"
---

> **One-liner**: Decide, with measured evidence, how FeeLens finds and reads every fee in a client document, and ship the winning strategy with per-number provenance and review flags.

## Description

### Context

The SC-5.6 benchmark found that values are read almost perfectly but no engine links more than 69% of
fees to the right label; the rule parsers in `pce/extraction/parsers.py` are per document type and miss
or mislabel fees on unseen layouts (specimen corpus RESULTS.md). The open questions from Ale: RAG or not,
search over OCR, which layout elements to detect, agent or routing, and how to make every number right.

### User Flow Impact

More fees found with the right label; every value carries the label box, row box and region so the
analyst can click a number and see where it came from; doubtful values are flagged `needs_review` with
a reason instead of entering the totals silently.

### Performance / Efficiency Impact

Strategies are measured in s/page on CPU. The default path must stay near the current ~1 s/page;
slow engines (VLM) only on pages that need them.

### Proposed Approach

1. Strategy scorer on the 44-page hand-checked set (`data/specimens/ocrbench/groundtruth.json`) with the
   accuracy-protocol thread's matching rules, including the wrong-value metric.
2. Strategies behind one interface: current parsers; generic line rule; header-aware table association;
   page routing by doc type; routing + cross-check verification; OCR/VLM on pages without a text layer.
3. Strategy review in `docs/research/EXTRACTION_STRATEGY.md` with the measured table and decisions.
4. Additive provenance fields (`label_bbox`, `row_bbox`, `region`, `review`) agreed with the trace thread.
5. Wire the winner into `extract()` if it beats the current parsers without regressions.

### Risks & Follow-ups

44 pages rank strategies; they do not give a precise production accuracy. Real client statements are
absent from the public corpus (positions, cash), so statement accuracy stays measured on synthetic data.

## Acceptance Criteria

- [ ] #1 Scorer reports precision, recall, F1, wrong-value share, bbox hit, needs_review share and s/page per strategy
- [ ] #2 At least four strategies measured on the same pages, results in the strategy doc
- [ ] #3 Every fact the new path emits has page + bbox, and doubtful facts carry review reasons
- [ ] #4 Existing backend tests stay green; local gate passes

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
