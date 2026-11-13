---
id: SC-5.22
title: Read scanned pages with RapidOCR when installed
status: "Done"
assignee: []
owner: "Raise fee detection toward 100%"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-o8nuus"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/52"
created_date: "2026-11-13 17:58"
updated_date: "2026-11-13 18:09"
labels:
  - extraction
dependencies: []
parent_task_id: SC-5
priority: P1
paths_owned:
  - backend/src/pce/extraction/layout.py
  - backend/src/pce/extraction/finder.py
  - backend/src/pce/extraction/toolchain.py
  - backend/src/pce/extraction/parsers.py
  - backend/src/pce/pipeline_view.py
  - backend/pyproject.toml
  - backend/uv.lock
  - backend/tests/test_fee_detection_leaks.py
  - backend/tests/test_pipeline.py
  - backend/tests/test_parallel_read.py
  - frontend/src/lib/trail.ts
  - frontend/src/pages/Review.tsx
  - frontend/src/pages/Documents.tsx
  - frontend/src/pages/Pipeline.tsx
  - docs/adr/0003-document-extraction-and-ocr.md
spec_ref: docs/research/EXTRACTION_STRATEGY.md
rule_refs: [".claude/rules/extraction.md", ".claude/rules/privacy.md"]
---

> **One-liner**: Read pages without a text layer with RapidOCR (local ONNX models, Apache-2.0) when the optional extra is installed, falling back to Tesseract, to find more of the fees printed on scans.

## Description

### Context
After SC-5.21 the app finds 90.2% of the fees on digital benchmark pages but only 53.5% on the same
pages as simulated scans: Tesseract misreads small table digits and splits rows. A measurement on 2026-11-13
(thread "Raise fee detection toward 100%", 11 scan pages of the ocrbench gold) gave RapidOCR 3.10.0
(PP-OCRv6 small, ONNX, models bundled in the wheel, runs on CPU, no network) 69.7% found with 3 wrong
values, against Tesseract 52.8% with 10 wrong, at 4.1 s/page against 6.8 s/page.

### User Flow Impact
An analyst who uploads a scanned bank tariff or KID sees more of its fees as clickable figures, with fewer
misread values to correct.

### Performance / Efficiency Impact
Faster than Tesseract per page on CPU (4.1 s against 6.8 s measured). Adds about 60 MB of wheels
(onnxruntime, opencv-python-headless) when the extra is installed; nothing changes without it.

### Proposed Approach
1. Optional extra `rapidocr` in `backend/pyproject.toml` (rapidocr, onnxruntime), with a licence line.
2. `layout._ocr_lines` uses RapidOCR when importable, else Tesseract; engine name `rapidocr` on the lines,
   and every place that recognises an OCR page accepts both engines.
3. Finder: a section titled as performance scenarios vetoes its rows even when the title names costs
   (found while measuring scans).
4. ADR 0003 amendment; toolchain lists the engine.

### Risks & Follow-ups
New dependencies need Ale's per-PR approval (AGENTS.md rule 9, licences). Table structure (tier tables)
stays a follow-up.

## Acceptance Criteria

- [x] #1 With the extra installed, production `extract()` finds more gold fees on the simulated scan pages than Tesseract (52.8% on 11 pages), with no more wrong values.
- [x] #2 Without the extra, behaviour is unchanged (Tesseract); digital pages unchanged; synthetic `pce.evaluation` stays 100%/0 wrong.
- [x] #3 Unit tests cover the reader selection and the scenario-title veto with SYNTHETIC data.

## Implementation Notes

Shared contract touched: `backend/pyproject.toml` and `uv.lock` (new optional extra). Pages and evidence
now carry `rapidocr` or `tesseract-ocr` as the engine; `layout.OCR_ENGINES` (backend) and `isOcrEngine`
(frontend) replace the checks for the literal `tesseract-ocr`. The Dockerfile is not changed, so the
Render demo keeps Tesseract until the extra is added to the image.

## Outcome

- **Status**: completed (merge needs Ale's approval: new dependency licences, AGENTS.md rule 9)
- Production `extract()` on the 11 scan pages of the ocrbench gold (89 fees), strategies scorer:
  Tesseract 52.8% found, 10 wrong, 1 accepted wrong, 6.9 s/page -> RapidOCR 69.7% found, 3 wrong,
  1 accepted wrong (an insurance DIP minimum premium), 4.3 s/page.
- Digital pages do not use OCR: finder 95.6% -> 95.8% (scenario-title veto), wrong 130 -> 129.
- `pce.evaluation` synthetic P-1042 and P-2077: recall 100%, wrong 0; sabotaged controls still fail.
- The synthetic scanned statement gives the same debits with both readers (`test_pipeline.py`).
- No network: RapidOCR initialised and read a page with sockets disabled; models ship in the wheel.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-o8nuus | 4703deb | 2026-11-13 | Add SC-5.22 |
| claude/project-thread-o8nuus | f0663c8 | 2026-11-13 | Scenario section titles veto their rows |
| claude/project-thread-o8nuus | 14d6b8f | 2026-11-13 | Read scans with RapidOCR when installed |
