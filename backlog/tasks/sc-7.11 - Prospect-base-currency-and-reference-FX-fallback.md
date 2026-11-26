---
id: SC-7.11
title: Reference FX fallback for amounts without a printed rate
status: Done
assignee: []
owner: "Compute every portfolio cost end to end"
model: "claude-opus-5-5"
progress: 100
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
  - "backend/src/pce/api.py"
  - "backend/tests/conftest.py"
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

- [x] #1 USD position without printed rate gets a CHF value with the reference rate cited
- [x] #2 Printed rate wins when both exist
- [ ] #3 EUR base prospect totals in EUR (moved to SC-7.22)

## Implementation Notes

- Split (2026-11-26): the prospect base currency (AC #3) moved to SC-7.22. Every label, report and the
  frontend say CHF; changing the base is its own story. This one is the reference-rate fallback only.
- `finance/fx.py`: ECB euro reference rate on or before the valuation date (7-day lookback for weekends and
  holidays), crossed through EUR, cached on disk (`data_dir()/reference_fx.json`), off with
  `PCE_REFERENCE_FX=0` (conftest sets it). Request carries currency codes and dates only.
- `api.compute` asks rates for every foreign currency on every statement date and passes them to
  `analyse()` as `prospect["reference_fx"]`, so the analysis stays pure and offline-testable.
- Printed rates win; printed vs reference more than 1% apart is a `fx_gap` warn check (a misread digit).
  A reference conversion is named in the formula and in an `fx_ref` info check with the ECB URL. Evidence
  ids stay fact ids (contract checks cast them to int).

## Outcome

On the real public holdings statements in the corpus (project files, 01-holdings-statements), positions
valued in CHF went from 0 of 126 to 91 of 126: AJ Bell 52/52 (GBP, 2019-04-05), Fidelity UK 39/39 (GBP,
2023-03-21). Fidelity US (35 positions) stays unvalued: its statement date is not read, so no rate date
exists (extraction gap, not this story). Synthetic tests: `tests/test_fx_fallback.py` (8). Full suite green.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-p3z1fq | 2cb422a | 2026-11-26 | ECB reference FX fallback, review point on printed-vs-reference gap |

## Issues Encountered
