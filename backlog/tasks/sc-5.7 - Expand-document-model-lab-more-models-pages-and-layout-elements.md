---
id: SC-5.7
title: Expand the document model lab (more models, pages, layout elements)
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-11 19:10"
updated_date: "2026-11-11 19:10"
labels:
  - extraction
  - qa
dependencies:
  - SC-5.6
parent_task_id: SC-5
priority: P1
paths_owned:
  - "data/specimens/ocrbench/**"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs:
  - ".claude/rules/extraction.md"
  - ".claude/rules/privacy.md"
---

> **One-liner**: Test every practical local OCR, layout, table and document VLM model in the lab, so the extraction strategy rests on measured results.

## Description

### Context

SC-5.6 benchmarked 17 engines on 44 pages (vision models on 23). Ale asked for an expert-level review: as many Hugging Face
models as practical, validated results, and a decision on which layout elements to detect. The extraction strategy,
accuracy protocol and traceability threads consume these results.

### User Flow Impact

None directly. It decides which engines the extraction pipeline uses and how much the analyst has to review.

### Performance / Efficiency Impact

Benchmark only: long CPU runs in a separate venv. Production code is unchanged.

### Proposed Approach

1. Re-survey Hugging Face for OCR, layout, table-structure and document-VLM models (new since 6 Nov and those skipped).
2. Add adapters for every new model that runs locally on CPU with a commercial-use licence; record the rest with a reason.
3. Grow the ground truth: more pages for hard tables, scans and statements; a second check of existing labels.
4. Score per layout element (table, key-value, text, header, footnote) and per document family; add table-structure
   (cell) accuracy.
5. Update the lab and the recommendation; hand the results to the strategy, protocol and traceability threads.

### Risks & Follow-ups

CPU-only runs limit model size. A GPU run is a follow-up. Ground truth has a single annotator, so each new page is spot-checked on the rendered image.

## Acceptance Criteria

- [ ] #1 Every model surveyed is either run with real scores or listed with a reason it was not run
- [ ] #2 Scores per layout element and per document family, on the same pages for every engine
- [ ] #3 No invented metrics; simulated scans stay labelled

## Implementation Notes

## Outcome

- **Status**:

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
