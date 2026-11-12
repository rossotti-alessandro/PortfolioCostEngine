---
id: SC-2.2
title: Safe Capital profile and market context for the pitch
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
priority: P1
paths_owned:
  - "docs/research/SAFE_CAPITAL_PROFILE.md"
spec_ref: docs/research/SAFE_CAPITAL_PROFILE.md
rule_refs: []
---

> **One-liner**: Know exactly who Safe Capital is, what it is licensed for and how it is paid, so the comparison is fair.

## Description

### Context

Brand and licence status were unverified in the kit.

### User Flow Impact

Deck and report wording match Safe Capital's real authorisations and pricing model.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Registry and FINMA/SO checks
2. Services, fee model, custodians used
3. What claims the report may and may not make

### Risks & Follow-ups

See `docs/research/SAFE_CAPITAL_PROFILE.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [x] #1 Every factual statement cites a public source with date
- [x] #2 Open questions for Massimo listed separately

## Implementation Notes

Sources: safecapital.ch and Moneyhouse (SOGC data), checked on 2026-11-06.

## Outcome

Merged in PR #1. docs/research/SAFE_CAPITAL_PROFILE.md covers the entity (UID CHE-381.156.096, Lugano, registered 2012), the group, the business, the website's claim of FINMA licence and OSIF supervision, product implications and questions for Massimo. The FINMA licence is NOT independently confirmed: the FINMA list was unreadable from S onwards and still needs a manual check.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-8cmfmc | 71cec49 | 2026-11-06 | Critical review, source register, fee and document taxonomies, research notes (merged via PR #1, 2c11cf4) |
