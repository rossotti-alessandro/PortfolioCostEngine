---
id: SC-2.1
title: Source register, document and fee taxonomies, critical review of the kit
status: In Progress
assignee: []
owner: "Research Swiss portfolio cost sources"
model: "claude-opus-5-5"
progress: 80
branch: "claude/project-thread-8cmfmc"
pr: ""
created_date: "2026-11-06 15:05"
updated_date: "2026-11-06 15:05"
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
- [ ] #2 Fee taxonomy CSV loads with no duplicate codes and every inclusion parent exists

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
