---
id: SC-7.23
title: FX margin, spreads and stamp duty from transaction lists
status: "In Progress"
assignee: []
owner: "Compute every portfolio cost end to end"
model: "claude-opus-5-5"
progress: 90
branch: "claude/project-thread-p3z1fq"
pr: ""
created_date: "2026-11-26 10:45"
updated_date: "2026-11-26 14:40"
labels:
  - finance
dependencies:
  - SC-7.18
  - SC-7.14
parent_task_id: SC-7
priority: P1
paths_owned:
  - "backend/src/pce/finance/implicit.py"
  - "backend/src/pce/finance/checklist.py"
  - "backend/tests/test_implicit.py"
  - "backend/src/pce/analysis.py"
  - "backend/src/pce/api.py"
  - "backend/src/pce/extraction/parsers.py"
  - "backend/src/pce/report.py"
  - "frontend/src/pages/Costs.tsx"
  - "frontend/src/lib/it.ts"
  - "docs/research/SOURCE_REGISTER.md"
spec_ref: docs/research/COST_PROTOCOL.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Measure the FX margin, spreads and stamp duty a portfolio paid from its transaction list, and show them in the hidden-cost range.

## Description

### Context

Split from SC-7.14 (Ale, 2026-11-26: "Cash drag range now, trades next"). These costs depend on trading,
so they need the transactions SC-7.18 reads.

### User Flow Impact

The hidden-cost box fills with measured FX margins and taxes instead of "not estimated".

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. FX margin = (applied rate - ECB reference on the trade date) x amount, signed by direction.
2. Spread = half quoted spread x traded amount when quotes exist; else not estimated.
3. Swiss stamp duty from trade value and security domicile (rates to verify in SOURCE_REGISTER).

### Risks & Follow-ups

Stamp duty rates and split need a verified source. Ale's approval for finance semantics.

## Acceptance Criteria

- [x] #1 FX confirmation at 1.0850 vs reference 1.0800 on 100k gives 500 implicit cost
- [x] #2 No trades: rows stay "not estimated" with the document that would estimate them

## Implementation Notes

- Parser: an FX line with a currency pair keeps the applied rate (the number with 4+ decimals) and the
  amount in the pair's first currency (if two amounts are printed, the one that × rate gives the other).
- `implicit.fx_margin`: |applied − ECB reference (B per CHF / Q per CHF)| × amount, converted to CHF.
  `implicit.stamp_duty`: client's half of the Swiss transfer tax, CH-booked buys/sells with ISIN; 0.075%
  CH/LI ISINs, 0.15% foreign; XS (Eurobond) exempt. Source SRC-CH-STG (secondary, statute to confirm).
- `checklist.hidden_costs` turns them into `range` rows (low = high = the estimate), annualised over the
  span of the bank's transaction lists (`analysis._trade_years`, same 28-day rule as cost reports; shorter
  or unknown = lower bound, said in the method). An evidenced fee (e.g. a stamp duty debit) is never estimated.
- `api._reference_fx` also asks the ECB for each trade date's currencies (codes and dates only).
- Spreads stay "not estimated": a transaction list shows the price paid, not the quote.

## Outcome

FX margin and Swiss stamp duty are estimated from transaction lists and shown in the hidden-cost box,
never in the totals. Synthetic checks: EUR/CHF 1.0850 vs 1.0800 on 100'000 = CHF 500; EUR/USD cross =
CHF 80; CH buy 100'000 + foreign sell 80'000 CHF = CHF 195 stamp duty; half-year list annualised, a
10-day list is a lower bound; no rate or no ISIN = not estimated; a stamp duty debit is not re-estimated.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |

## Issues Encountered

- Swiss statute page (fedlex) is not machine-readable; rates from a secondary source, to confirm by hand.
