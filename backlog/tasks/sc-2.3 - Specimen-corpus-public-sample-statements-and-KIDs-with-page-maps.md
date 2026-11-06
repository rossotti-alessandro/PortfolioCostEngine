---
id: SC-2.3
title: Specimen corpus: public sample statements and KIDs with page maps
status: "In Progress"
assignee: []
owner: "Build 50+ real PDF test corpus"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-coe0g4"
pr: ""
created_date: "2026-11-06 15:05"
updated_date: "2026-11-06 15:36"
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

- [ ] #1 Each stored file has source URL, fetch date, SHA-256 and licence note
- [ ] #2 At least 2 ETF KIDs, 2 active fund KIDs, 1 bank tariff sheet mapped

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
