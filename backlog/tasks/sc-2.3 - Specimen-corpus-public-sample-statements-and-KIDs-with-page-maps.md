---
id: SC-2.3
title: Specimen corpus: public sample statements and KIDs with page maps
status: "In Progress"
assignee: []
owner: "Build 50+ real PDF test corpus"
model: "claude-opus-5-5"
progress: 90
branch: "claude/project-thread-coe0g4"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/7"
created_date: "2026-11-06 15:05"
updated_date: "2026-11-06 16:34"
labels:
  - research
dependencies:
  - SC-2.1
parent_task_id: SC-2
priority: P1
paths_owned:
  - "data/specimens/**"
  - "docs/research/SPECIMENS.md"
spec_ref: docs/research/DOCUMENT_TAXONOMY.md
rule_refs:
  - ".claude/rules/privacy.md"
---

> **One-liner**: Collect lawfully usable public specimens so extraction is built against real layouts, not guesses.

## Description

### Context

Kit could not download any PDFs; layouts are known only from descriptions.

### User Flow Impact

Extraction adapters match how real Swiss bank and fund documents look.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Download only documents whose terms allow it; record SHA-256 and licence
2. Page map per specimen: which page has positions, fees, totals
3. Where redistribution is not allowed, keep link + page map only

### Risks & Follow-ups

See `docs/research/DOCUMENT_TAXONOMY.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [x] #1 Each stored file has source URL, fetch date, SHA-256 and licence note
- [ ] #2 At least 2 ETF KIDs, 2 active fund KIDs, 1 bank tariff sheet mapped

## Implementation Notes

Owned paths used: `data/specimens/**`, `docs/research/SPECIMENS.md`, and `data/reference/specimen_corpus.csv`
(the manifest; `data/reference/` is where the pre-commit hook allows CSVs, next to the demo thread's
`public_corpus.csv`, whose first 11 columns it shares). PDFs are never committed: `fetch.py` downloads them
into `var/specimens/`. Branch is stacked on `claude/project-thread-steqtm` (demo thread, PR #5) because the
evaluator imports its parser.

## Outcome

399 real public PDFs from 289 institutions (152 de, 91 it, 90 fr, 66 en) across 14 categories: fund, ETF,
Swiss, structured and insurance KIDs, factsheets, prospectuses and annual reports, CH/IT/EU bank tariffs,
FinSA/MiFID ex-ante cost disclosures, termsheets, 17 filled client-document specimens and 12 statement guides/specs/forms. Each row has
URL, retrieval date, SHA-256, licence and robots note. Every file ran through `extract()` (parser 0972cc3):
0 crashes, 8 intake refusals, 315/391 typed right, 713 facts all with in-page bbox. Bugs sent to the demo
thread after each run. See `docs/research/SPECIMENS.md`, `docs/research/CLIENT_DOCUMENTS.md`,
`data/specimens/COVERAGE.md` and `data/specimens/RESULTS.md`.

AC #2 is partly met: far more than 2 ETF KIDs, 2 active KIDs and 1 tariff are in, and every fact records its
page, but there is no hand-written page map per specimen yet. Status stays In Progress for that.

## Issues Encountered

- 2026-11-06 15:55: re-download from a clean folder got 70/72; UniCredit answers 403 to the script's user agent and ING-DiBa closes the connection.
- 2026-11-06 15:55: Raiffeisen Locarno URLs pass raiffeisen.ch robots.txt by the letter, not clearly by intent. Flagged for Ale.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-coe0g4 | 82e2948 | 2026-11-06 15:56 | Specimen corpus manifest, fetch, evaluation and results |
| claude/project-thread-coe0g4 | 56fd4e1 | 2026-11-06 16:34 | Grow corpus to 395 PDFs, client document guide, coverage, re-run |
| claude/project-thread-coe0g4 | c9bd736 | 2026-11-06 16:55 | Filled specimens, relabel, re-run on 0972cc3 |
