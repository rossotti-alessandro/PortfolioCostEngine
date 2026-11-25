---
id: SC-2.4
title: Complete portfolio cost protocol and FeeLens gap analysis
status: "Done"
assignee: []
owner: "Design complete portfolio cost protocol"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-7crdzy"
pr: ""
created_date: "2026-11-25 20:50"
updated_date: "2026-11-25 20:53"
labels:
  - research
dependencies: []
parent_task_id: SC-2
priority: P1
paths_owned:
  - "docs/research/COST_PROTOCOL.md"
  - "backlog/tasks/**"
  - "docs/SOURCES_OF_TRUTH.md"
spec_ref: docs/research/COST_PROTOCOL.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Write down the state-of-the-art cost protocol (documents, taxonomy, sourcing, scoring) and rank what FeeLens misses against it.

## Description

### Context

FeeLens has a fee taxonomy and an instrument data source survey (SC-9.8 branch, INSTRUMENT_DATA_SOURCES.md) but no end-to-end protocol: which documents per family, which costs must exist per asset class, how sources are ranked and scored, and where the engine falls short.

### User Flow Impact

No product change. The analyst and Ale get one reference for what a complete cost review is, and a ranked backlog.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Review the ledger, analysis pipeline, scenarios, tariffs, schema and taxonomy on main.
2. Write docs/research/COST_PROTOCOL.md: analyst workflow, document set, taxonomy by asset class, source tiers, confidence score, conflict rules, step-by-step protocol, implicit-cost methods, ranked gaps, data-model sketch.
3. Reserve and write one story per actionable gap (SC-2.5, SC-7.7..SC-7.14).

### Risks & Follow-ups

Tax rates and practitioner durations are indicative and marked to verify; they must go through SOURCE_REGISTER.md before client use.

## Acceptance Criteria

- [x] #1 COST_PROTOCOL.md exists with an executive summary and ranked gaps citing file:line on main
- [x] #2 Each gap that needs code has a To Do story with paths_owned and acceptance criteria

## Implementation Notes

Docs and backlog only; no code. Owned paths as listed, plus a row in docs/SOURCES_OF_TRUTH.md.

## Outcome

- **Status**: completed
- `docs/research/COST_PROTOCOL.md`: document set, taxonomy by asset class, source tiers T1-T8, confidence
  score and conflict rules, 13-step protocol, implicit-cost methods, 12 ranked gaps with file:line on main 91181df.
- Gap 3 reproduced with a synthetic cash statement: 4 quarterly custody debits of CHF 500 give CHF 500 observed.
- New To Do stories: SC-2.5, SC-7.7, SC-7.8, SC-7.9, SC-7.10, SC-7.11, SC-7.12, SC-7.13, SC-7.14.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-7crdzy | 4140c5f | 2026-11-25 | Claim |
| claude/project-thread-7crdzy | 1de2ef6 | 2026-11-25 | COST_PROTOCOL.md and gap stories |
