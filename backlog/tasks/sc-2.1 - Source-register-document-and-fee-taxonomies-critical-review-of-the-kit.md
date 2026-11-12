---
id: SC-2.1
title: Source register, document and fee taxonomies, critical review of the kit
status: Done
assignee: []
owner: "Research Swiss portfolio cost sources"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-8cmfmc"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/1"
created_date: "2026-11-06 15:05"
updated_date: "2026-11-11 14:10"
labels:
  - research
dependencies: []
parent_task_id: SC-2
priority: P0
paths_owned:
  - "docs/research/**"
  - "docs/CRITICAL_REVIEW.md"
  - "data/taxonomy/**"
spec_ref: docs/research/SOURCE_REGISTER.md
rule_refs: []
---

> **One-liner**: Replace the ChatGPT kit's unverified claims with sourced taxonomies the engine can rely on.

## Description

### Context

Kit taxonomies and sources were not re-verified and contained errors (e.g. PyMuPDF licence, Luxembourg tariff as generic).

### User Flow Impact

Analysts see categories and document requests grounded in real Swiss bank documents.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Verify each source (URL, date, jurisdiction, licence)
2. Document types with what each contains and why it matters
3. Fee taxonomy with inclusion relations and evidence status
4. Critical review of the kit

### Risks & Follow-ups

See `docs/research/SOURCE_REGISTER.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Every source row has URL, access date, jurisdiction and licence/usage note
- [x] #2 Fee taxonomy CSV loads with no duplicate codes and every inclusion parent exists

## Implementation Notes

Web research ran through fetch tools. Fedlex (Swiss law texts) returned only JavaScript, so the FinSA, FADP, stamp duty and VAT article citations are marked 'to verify'. See the Open verification list in SOURCE_REGISTER.md.

## Outcome

Merged in PR #1. docs/CRITICAL_REVIEW.md has 27 findings on the kit. docs/research/ holds the source register, fee taxonomy (10 layers, 44 unique codes, 7 evidence statuses), document taxonomy (31 types, IT/DE labels), privacy/hosting, extraction tooling and UX notes. data/taxonomy/*.csv are the machine-readable versions. AC #1 is only partly met: the register has one access date for all rows (2026-11-06) and puts jurisdiction and usage limits in the caveat column, not in dedicated columns. Overlap parents in the CSV are free text, not code references.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-8cmfmc | 71cec49 | 2026-11-06 | Critical review, source register, fee and document taxonomies, research notes (merged via PR #1, 2c11cf4) |
