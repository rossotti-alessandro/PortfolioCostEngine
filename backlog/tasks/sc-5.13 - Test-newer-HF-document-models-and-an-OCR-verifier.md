---
id: SC-5.13
title: Test newer Hugging Face document models and an OCR verifier in the lab
status: "In Progress"
assignee: []
owner: "Compare complete extraction workflows"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-rfm5yy"
pr: ""
created_date: "2026-11-12 15:25"
updated_date: "2026-11-12 15:18"
labels:
  - extraction
  - qa
dependencies:
  - SC-5.7
  - SC-5.10
parent_task_id: SC-5
priority: P2
paths_owned:
  - "data/specimens/ocrbench/**"
  - "data/specimens/arena/**"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs:
  - ".claude/rules/extraction.md"
  - ".claude/rules/privacy.md"
---

> **One-liner**: Measure three newer local models (Falcon-OCR, Nemotron-3.5-Parse, MiniCPM-OCR-Jev) on the lab pages, so the reader and verifier choice rests on our own numbers.

## Description

### Context

Ale asked (2026-11-12) whether the lab uses the most capable page-reading models. A Hugging Face search found three
untested candidates: tiiuae/Falcon-OCR (0.27B, Apache-2.0), nvidia/Nemotron-3.5-Parse (0.63B, OpenMDW-1.1, returns
boxes and classes) and openbmb/MiniCPM-OCR-Jev (2B, Apache-2.0), a model that scores whether an OCR result for a region
is correct. SC-5.10 showed that a second independent reader removes wrongly accepted figures but sends many to review
because the current vision reader (PaddleOCR-VL) is slow and finds only 64% of fees.

### User Flow Impact

None directly. It decides which local reader and verifier the extraction pipeline adopts next.

### Performance / Efficiency Impact

Lab only. Models run on CPU in the separate lab venv, one at a time, with `OMP_THREAD_LIMIT=1` for Tesseract.

### Proposed Approach

1. Review the custom model code (`trust_remote_code`) of Falcon-OCR and Nemotron-3.5-Parse before running it.
2. Add adapters for both as page readers; run them on the 23-page core set; score with the existing scorer.
3. Use MiniCPM-OCR-Jev as a verifier: score each finder+verify figure's region and measure whether its score separates
   right from wrong figures (AUROC, wrong-accepted at a review budget).
4. Add the new readers to the two-reader ensemble in the workflow arena; update the lab.

### Risks & Follow-ups

- Custom code may need GPU-only kernels (FlexAttention, CUDA); then the model is recorded as not runnable on CPU.
- Jev expects a rendered image of the candidate text; without the vendor renderer, results may understate it.

## Acceptance Criteria

- [ ] #1 Custom code of every `trust_remote_code` model reviewed before it runs (no network calls, no file writes outside the cache).
- [ ] #2 Each runnable model scored on the core pages with the existing scorer; non-runnable ones recorded with the reason in `models.json`.
- [ ] #3 Verifier measured: how well its score separates right from wrong figures, and the wrong-accepted rate at the arena's review budget.
- [ ] #4 Lab and RESULTS updated; no third-party page images committed.

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits
