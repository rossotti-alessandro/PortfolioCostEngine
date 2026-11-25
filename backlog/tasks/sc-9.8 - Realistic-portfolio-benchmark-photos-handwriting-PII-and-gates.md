---
id: SC-9.8
title: Realistic portfolio benchmark: photos, handwriting, PII and gates
status: "In Progress"
assignee: []
owner: "Prove accuracy on realistic portfolios"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-12ht53"
pr: ""
created_date: "2026-11-25 19:45"
updated_date: "2026-11-25 19:35"
labels:
  - evaluation
  - extraction
dependencies: []
parent_task_id: SC-9
priority: P0
paths_owned:
  - "backend/src/pce/evaluation/realistic/**"
  - "backend/src/pce/extraction/photo.py"
  - "backend/tests/test_realistic*.py"
  - "backend/tests/test_photo*.py"
  - "docs/research/REALISTIC_BENCHMARK.md"
  - "docs/research/INSTRUMENT_DATA_SOURCES.md"
spec_ref: docs/EVALUATION_PROTOCOL.md
rule_refs: [".claude/rules/extraction.md", ".claude/rules/privacy.md", ".claude/rules/finance.md"]
---

> **One-liner**: Measure the whole pipeline on many realistic portfolio statements (real public ISINs, Swiss and Italian layouts, scans, phone photos, handwriting, planted personal data) against explicit per-category gates, and produce a full-portfolio cost estimate end to end.

## Description

### Context
Accuracy is known on 63 public tariff/KID pages (fees) and 4 public statements (holdings). Banks publish no
Swiss or Italian client statements, real ones are client data, and phone photos and handwriting were never
tested. The PII detector (SC-11.3) was never measured against extraction on the same documents.

### User Flow Impact
None directly. Ale and Massimo get a dated, reproducible accuracy table per document condition and one
full-portfolio cost report built from a realistic statement.

### Performance / Efficiency Impact
Benchmark only; adds a photo normaliser (deskew, perspective, contrast) that runs only on image uploads.

### Proposed Approach
1. Generator: SYNTHETIC statements in several bank layout archetypes (CH/IT, IT/DE/FR/EN, CHF/EUR/USD),
   holdings drawn from real public ISINs (ETFs, funds, stocks, bonds), fee lines, and planted fake personal data.
2. Degradations: digital, 300 dpi scan, 150 dpi noisy scan, phone photo (perspective, blur, shadow, low light,
   JPEG), handwritten annotations and handwritten figures.
3. Scorer: holdings (ISIN, value), AUM, fees, PII recall and figures destroyed by masking; per-category gates.
4. End-to-end: one prospect through extract + analyse + report.

### Risks & Follow-ups
Synthetic layouts are look-alikes; they do not replace the supervised pilot on real statements (READINESS G2).

## Acceptance Criteria

- [ ] #1 Benchmark runs with one command and writes a dated report with per-category gates.
- [ ] #2 Every generated file says SYNTHETIC; no real person's data.
- [ ] #3 Existing synthetic baseline (pce.evaluation) unchanged.

## Implementation Notes

## Outcome

- **Status**: partial

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
