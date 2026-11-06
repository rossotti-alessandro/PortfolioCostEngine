---
id: SC-5.6
title: Local VLM benchmark (PaddleOCR-VL or similar) with adapter
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-06 15:05"
updated_date: "2026-11-06 15:05"
labels:
  - extraction
  - qa
dependencies:
  - SC-9.1
parent_task_id: SC-5
priority: P2
paths_owned:
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

- [ ] #1 Benchmark report with real numbers or an explicit 'not run: reason'
- [ ] #2 No invented metrics

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
