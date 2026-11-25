---
id: SC-9.8
title: Realistic portfolio benchmark: photos, handwriting, PII and gates
status: "Done"
assignee: []
owner: "Prove accuracy on realistic portfolios"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-12ht53"
pr: ""
created_date: "2026-11-25 19:45"
updated_date: "2026-11-25 23:30"
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

- [x] #1 Benchmark runs with one command and writes a dated report with per-category gates.
- [x] #2 Every generated file says SYNTHETIC; no real person's data.
- [x] #3 Existing synthetic baseline (pce.evaluation) unchanged.

## Implementation Notes

Paths touched beyond `paths_owned`, each a defect the benchmark exposed (needs Ale's per-PR approval, rule 9:
product-cost logic and PII masking):
`backend/src/pce/extraction/parsers.py` (broker ISIN-under-name rows, French headers, KID performance fee,
`reconcile_positions`), `backend/src/pce/extraction/vocab.py` (fee words), `backend/src/pce/pii.py`
(dossier titoli), `backend/src/pce/analysis.py` (a KID for the held ISIN makes it a fund), tests
`test_kid_join.py`, `test_pii.py`.

## Outcome

- **Status**: completed

`uv run python -m pce.evaluation.realistic --n 18` builds 18 SYNTHETIC statements (6 layouts, 137 real
public ISINs, planted fake PII) in 7 conditions and writes `report.md` with per-condition gates. Branch vs
main: holdings 85.4 -> 100% on digital, scan and photo; fees 87.5 -> 100% digital; wrong-but-unflagged
values 15% -> 0 on poor scans, 14.9% -> 1.2% on hard photos. Handwritten figures 87%. Masking destroys no
ISIN or fee figure; names and addresses are not masked (SC-11.9). E2E from a phone photo: all 15 holdings,
total and 6 bank fees exact, all-in CHF 20,947.72 (1.24%). Synthetic baseline unchanged (100%, wrong 0).
Full results: `docs/research/REALISTIC_BENCHMARK.md`.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-12ht53 | 9b48169 | 2026-11-25 | generator, degradations, scorer, photo cleanup |
| claude/project-thread-12ht53 | f865908 | 2026-11-25 | e2e report, instrument data sources |
| claude/project-thread-12ht53 | fb80033 | 2026-11-25 | KID for held ISIN makes it a fund |
| claude/project-thread-12ht53 | 454e906 | 2026-11-25 | broker rows, French headers, fee words, PII |
| claude/project-thread-12ht53 | c3b62f7 | 2026-11-25 | KID performance fee, unreconciled OCR holdings |
| claude/project-thread-12ht53 | 92f6785 | 2026-11-25 | KID performance fee from its own row |
| claude/project-thread-12ht53 | a7b6545 | 2026-11-25 | benchmark doc, e2e via app |
