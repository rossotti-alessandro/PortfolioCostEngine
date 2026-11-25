---
id: SC-7.13
title: Cost claims, source tiers and per-figure confidence score
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-25 20:50"
updated_date: "2026-11-25 20:50"
labels:
  - finance
dependencies:
  - SC-7.12
parent_task_id: SC-7
priority: P1
paths_owned:
  - "backend/src/pce/finance/claims.py"
  - "backend/src/pce/finance/ledger.py"
  - "backend/tests/unit/finance/test_claims.py"
spec_ref: docs/research/COST_PROTOCOL.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Let one cost carry several sources, pick the winner by fixed rules, and give every figure a 0-100 confidence score.

## Description

### Context

FeeAtom has one measurement and a flat evidence list. There is no source tier, no record of competing values, and no confidence score, so cross-validation and conflict review cannot be expressed.

### User Flow Impact

Each number shows its score band (Verified, Supported, Indicative) and the sources behind it; conflicts become review points.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. CostClaim model: fee code, value, basis, period, tier T1..T8, as-of, match quality, extraction confidence, evidence.
2. Resolver applying the conflict rules and the score of COST_PROTOCOL.md section 3, deterministic, Decimal only.
3. Figures under 40 excluded from totals and shown as ranges.

### Risks & Follow-ups

Score weights are a proposal; calibrate on the gold set before showing them to clients.

## Acceptance Criteria

- [ ] #1 Same-tier disagreement goes to review, never averaged
- [ ] #2 Observed beats contractual for the same period; contractual kept as cross-check
- [ ] #3 Name-only match capped at 40

## Implementation Notes

## Outcome

## Issues Encountered
