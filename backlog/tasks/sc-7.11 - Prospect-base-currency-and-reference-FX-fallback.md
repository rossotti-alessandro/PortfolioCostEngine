---
id: SC-7.11
title: Prospect base currency and reference FX fallback
status: "In Progress"
assignee: []
owner: "Compute every portfolio cost end to end"
model: "claude-opus-5-5"
progress: 5
branch: "wip-sc-7.11"
pr: ""
created_date: "2026-11-25 20:50"
updated_date: "2026-11-26 09:57"
labels:
  - finance
dependencies: []
parent_task_id: SC-7
priority: P1
paths_owned:
  - "backend/src/pce/analysis.py"
  - "backend/src/pce/finance/fx.py"
  - "backend/tests/test_fx_fallback.py"
spec_ref: docs/research/COST_PROTOCOL.md
rule_refs:
  - ".claude/rules/finance.md"
  - ".claude/rules/privacy.md"
---

> **One-liner**: Value foreign positions even when the statement prints no rate, and honour the prospect's own base currency.

## Description

### Context

analysis.py:32 fixes BASE_CCY to CHF while Prospect.base_ccy exists. analysis.py:261 accepts only rates printed on the client's documents; a USD position without a printed USD/CHF rate gets no CHF value and leaves the asset base and the cost basis.

### User Flow Impact

Fewer unvalued positions; the source of every rate is shown (printed on statement vs ECB/SNB reference).

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Read base currency from the prospect.
2. Fallback to the ECB (or SNB) reference rate on the valuation date, cached locally, status estimated, source URL as evidence.
3. Printed rates still win; difference over 1% becomes a review point.

### Risks & Follow-ups

Fetching reference rates is an external call (no client data). Needs Ale's per-PR approval.

## Acceptance Criteria

- [ ] #1 USD position without printed rate gets a CHF value with the reference rate cited
- [ ] #2 Printed rate wins when both exist
- [ ] #3 EUR base prospect totals in EUR

## Implementation Notes

## Outcome

## Issues Encountered
