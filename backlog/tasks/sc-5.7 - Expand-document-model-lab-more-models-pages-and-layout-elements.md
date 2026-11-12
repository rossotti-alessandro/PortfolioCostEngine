---
id: SC-5.7
title: Expand the document model lab (more models, pages, layout elements)
status: "Done"
assignee: []
owner: "Expand the document model lab"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-rfm5yy"
pr: ""
created_date: "2026-11-11 19:10"
updated_date: "2026-11-12 02:50"
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

- [x] #1 Every model surveyed is either run with real scores or listed with a reason it was not run
- [x] #2 Scores per layout element and per document family, on the same pages for every engine
- [x] #3 No invented metrics; simulated scans stay labelled

## Implementation Notes

Paths touched outside `paths_owned`, agreed with the accuracy-protocol thread: `docs/EVALUATION_PROTOCOL.md`
(ocrbench corpus row and baseline row re-run on the larger gold). `app_run.py` and `app_e2e.py` live in
`data/specimens/ocrbench/` but run in the backend environment because they call the app (`pce.extraction`,
`pce.analysis`, `pce.evaluation`); they change no production code.

- 14 new adapters (8 VLM parsers, 4 layout or table-structure models, EasyOCR, and the app itself as an engine).
- Ground truth: 63 pages (54 real, 9 simulated scans), 813 figures, each tagged table / key-value / text / footnote.
- Scoring: per layout element, per document family, and three fair page sets (23 core, 8 hard, all pages).
- Lab: "App end to end" view runs the SYNTHETIC prospects through the app with every cost line traced to its box.

## Outcome

- **Status**: Done.
- Tables are the weak element: the best pipeline puts about 60 to 68% of table figures on their label's row; key-value
  lists and text are above 90%. Every good reader reads 100% of values on the 8 hard pages and pairs exactly 79%:
  the misses are labels in column or row headings, so the next step is table structure and classification, not a bigger OCR model.
- No new vision model beats PaddleOCR-VL (same 79% on the hard pages, 2 to 6 times slower on CPU).
- The app reads 2 to 3% of fees on real public pages (protocol baseline 3.6% recall on 813 figures).
- SYNTHETIC end to end: original PDFs match every pinned number; scanned copies lose a holdings page and raise alarms.
- Found and handed off: Tesseract OpenMP threads made scanned pages take minutes under load (fixed in SC-5.9).

## Issues Encountered

- VLM timings measured while Tesseract ran were inflated about 5x; LightOnOCR-3 and Xiaomi-OCR were re-run alone.
- Disk filled during model downloads; unreferenced Hugging Face blobs were removed after each triage.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-rfm5yy | fff4b3e | 2026-11-11 | feat(ocrbench): add 14 adapters and round-2 hard pages |
| claude/project-thread-rfm5yy | 37ca8f0 | 2026-11-11 | feat(ocrbench): grow ground truth and score per layout element |
| claude/project-thread-rfm5yy | 56ec242 | 2026-11-11 | fix(ocrbench): add 14 missed figures, list new models |
| claude/project-thread-rfm5yy | 4452318 | 2026-11-12 | feat(ocrbench): run the app on lab pages and synthetic prospects |
| claude/project-thread-rfm5yy | 7d4f93b | 2026-11-12 | docs(ocrbench): record layout-element findings and new baseline |
