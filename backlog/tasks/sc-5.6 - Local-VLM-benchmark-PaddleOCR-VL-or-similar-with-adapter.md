---
id: SC-5.6
title: Local VLM benchmark (PaddleOCR-VL or similar) with adapter
status: "Done"
assignee: []
owner: "Benchmark local OCR and layout models"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-rfm5yy"
pr: ""
created_date: "2026-11-06 15:05"
updated_date: "2026-11-07 00:50"
labels:
  - extraction
  - qa
dependencies:
  - SC-9.1
parent_task_id: SC-5
priority: P2
paths_owned:
  - "data/specimens/ocrbench/**"
  - "backend/src/pce/extraction/vlm/**"
  - "backend/tests/evaluation/vlm/**"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs:
  - ".claude/rules/extraction.md"
  - ".claude/rules/privacy.md"
---

> **One-liner**: Measure whether a local vision model beats OCR on hard scans before relying on one.

## Description

### Context

No VLM.

### User Flow Impact

None until it proves better on the corpus.

### Performance / Efficiency Impact

Heavy: GPU or long CPU runs; record hardware.

### Proposed Approach

1. Pluggable adapter
2. Run on the golden corpus; record model, version, hardware, metrics

### Risks & Follow-ups

See `docs/adr/0003-document-extraction-and-ocr.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [x] #1 Benchmark report with real numbers or an explicit 'not run: reason'
- [x] #2 No invented metrics

## Implementation Notes

- Owned paths used: `data/specimens/ocrbench/**` only. The harness has its own venv (`var/ocrbench/.venv`) so heavy ML
  packages never touch `backend/pyproject.toml`. No production adapter in `backend/src/pce/extraction/vlm/**` yet: the
  numbers say where it should go first (see Outcome).
- 508 Hugging Face models surveyed, 17 run, 14 rejected with a reason (`models.json`): GPU-only, AGPL/GPL/non-commercial,
  or no licence stated.
- 44 pages (38 real incl. 2 true scans, 6 simulated scans) from the public specimen corpus; 514 fee figures hand-checked
  against the rendered page (`groundtruth.txt`). Vision models ran on the 23-page core set.
- Machine: 4-core Xeon with AMX, 15 GB RAM, no GPU. Speeds are medians after model load, one job at a time.

## Outcome

Results in `data/specimens/ocrbench/SCORES.md`; interactive lab built by `lab.py` (not committed: third-party page images).
Same 23 pages, label and value on the same row:

| Engine | Row accuracy | s/page |
| ------ | ------------ | ------ |
| Hybrid + PaddleOCR-VL on scans and table pages | 69% | 53.5 |
| PaddleOCR-VL 1.6 | 67% | 52.3 |
| Docling 2 | 63% | 4.9 |
| Hybrid: text layer or RapidOCR + Heron tables | 62% | 1.1 |
| RapidOCR | 62% | 4.5 |
| granite-docling-258M | 60% | 43.6 |
| pdfplumber (current) | 57% | 0.1 |

- Reading numbers is solved (text layer or RapidOCR read 100% of figures). Pairing a figure with a label held in a column
  or row heading is the gap; no engine passes about 70%.
- Layout: PP-DocLayoutV3 finds 98% of fee tables (1 s/page), Heron 92-94%. DocLayout-YOLO is AGPL: measured only.
- A vision model is worth it on scans (row accuracy 54% to 66%), not on born-digital pages.
- Fee classification is the weakest step: the table-aware extractor finds 63-66% of fees at 43-49% precision.
- Not recommended: direct fee extraction with Qwen3-VL-2B (45%), LayoutLM QA (3%), GOT-OCR and Florence-2 (they drop text).
- Follow-ups to reserve: (1) production pipeline = text layer + layout table rows + RapidOCR on scans, PaddleOCR-VL as a
  background second reader; (2) header-aware fee classifier per document type; (3) rerun the VLMs on a GPU over the whole corpus.

## Issues Encountered

- LightOnOCR-2's config says `mistral3`; the Auto class silently left its vision tower random. Load `LightOnOcrForConditionalGeneration`.
- granite-docling's DocTags are special tokens; decoding with `skip_special_tokens=True` returns an empty page.
- Some generation configs ship `use_cache=false` (about 10x slower on CPU); the harness forces the cache on.
- Two heavy jobs at once (or the backend test suite) made the vision models 10-30x slower; the backend suite also
  timed out once under that load and passed when run alone.
- The first pair metric let block-level engines pair any label with any number on a long line; fixed with a context window.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-rfm5yy | 78cb2df | 2026-11-06 | Benchmark harness, pages, ground truth, scores, lab |
| claude/project-thread-rfm5yy | dc5a320 | 2026-11-06 | 8-page VLM set and per-call time cap |
| claude/project-thread-rfm5yy | bd75980 | 2026-11-06 | Fix LightOnOCR-2 loading and granite DocTags |
| claude/project-thread-rfm5yy | 5326843 | 2026-11-07 | Same-page scores and lab pipeline tab |
