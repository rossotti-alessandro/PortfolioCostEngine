---
id: SC-7.24
title: Trades printed inside statements with tickers and inline charges
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-26 13:34"
updated_date: "2026-11-26 13:34"
labels:
  - extraction
dependencies:
  - SC-7.18
parent_task_id: SC-7
priority: P2
paths_owned:
  - "backend/src/pce/extraction/parsers.py"
  - "backend/tests/test_transactions.py"
spec_ref: docs/research/COST_PROTOCOL.md
rule_refs:
  - ".claude/rules/extraction.md"
---

> **One-liner**: Read the trade tables that real statements print inside the holdings report (dates without a year, tickers instead of ISINs, a charges column), not only standalone transaction lists.

## Description

### Context

SC-7.18 reads trade lines from transaction lists that carry a full date and an ISIN. On the public corpus
(2026-11-26) no real sample matched: the Fidelity US investment report prints "Securities Bought & Sold"
inside the portfolio statement, with dates like "7/11" (year from the statement period), tickers (JNK,
SBRA) and a per-trade charges column (-7.95); the UOB Kay Hian statement prints "Bought 10,000 TPV
TECHNOLOGY" without ISIN, on a noisy scan.

### User Flow Impact

Trades on ordinary statements reach the transaction table without a separate transaction list.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Run the trade reader on portfolio statements too, inside a section headed like "bought & sold".
2. Year-less dates take the year of the statement period.
3. Without an ISIN, keep the printed name or ticker; never resolve it by name alone.
4. A charges column becomes a brokerage cash debit for that trade.

### Risks & Follow-ups

A ticker is not an ISIN: no product-cost match on it.

## Acceptance Criteria

- [ ] #1 The Fidelity US sample gives its bought and sold lines as trades with the statement year
- [ ] #2 No trade is read from a total line or a card purchase on a cash statement

## Implementation Notes

## Outcome

## Issues Encountered
