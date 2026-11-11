---
id: SC-5.4
title: Bank statement adapters: positions, cash, fee lines (synthetic first)
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
dependencies:
  - SC-5.1
  - SC-5.3
  - SC-4.2
parent_task_id: SC-5
priority: P0
paths_owned:
  - "backend/src/pce/extraction/adapters/**"
  - "backend/tests/integration/adapters/**"
spec_ref: docs/research/DOCUMENT_TAXONOMY.md
rule_refs:
  - ".claude/rules/extraction.md"
---

> **One-liner**: Map parsed rows into positions, cash movements and fee lines per document type.

## Description

### Context

Parsers give rows; nothing maps them to the domain.

### User Flow Impact

Positions and fees appear in review with their source.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Generic adapter by column semantics
2. Synthetic UBS-like and Julius-Baer-like layouts (clearly SYNTHETIC)
3. Reconcile holdings sum vs statement total within scope

### Risks & Follow-ups

See `docs/research/DOCUMENT_TAXONOMY.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Synthetic statement: positions sum reconciles to stated total
- [ ] #2 Mismatch is shown as a flag with both numbers, never forced

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
