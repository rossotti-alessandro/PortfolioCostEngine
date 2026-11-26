---
id: SC-7.18
title: Transaction table and transaction-list parser
status: "In Progress"
assignee: []
owner: "Compute every portfolio cost end to end"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-p3z1fq"
pr: ""
created_date: "2026-11-26 01:10"
updated_date: "2026-11-26 13:25"
labels:
  - finance
  - extraction
  - db
dependencies:
  - SC-7.12
parent_task_id: SC-7
priority: P1
paths_owned:
  - "backend/src/pce/db.py"
  - "backend/src/pce/book_of_record.py"
  - "backend/src/pce/extraction/parsers.py"
  - "backend/tests/test_transactions.py"
spec_ref: docs/research/COST_PROTOCOL.md
rule_refs:
  - ".claude/rules/finance.md"
  - ".claude/rules/extraction.md"
  - ".claude/rules/privacy.md"
---

> **One-liner**: Read transaction lists and trade confirmations into a Transaction table, so trading costs can be estimated and checked against the tariff.

## Description

### Context

SC-7.12 stores accounts, instruments and dated positions. It left transactions out: no parser produces trade facts yet, so a table would have stayed empty. Brokerage, stamp duty, FTT and FX margin (gaps 4 and 7 of COST_PROTOCOL.md) all scale with turnover.

### User Flow Impact

Analysts can upload a transaction list; trading costs move from "not estimated" to estimated or checked.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Parser for transaction lists (date, kind buy/sell/fx/income/fee, ISIN, quantity, gross amount, currency, charges) with page + bbox evidence.
2. Transaction table (tenant- and prospect-scoped, fact_id unique per tenant) filled by book_of_record.sync.
3. Erasure deletes it with the prospect.

### Risks & Follow-ups

Layouts vary a lot by bank; start with the synthetic corpus and one real public sample.

## Acceptance Criteria

- [ ] #1 A synthetic transaction list gives one row per trade with evidence
- [ ] #2 Re-import is idempotent; another firm cannot read the rows; erasure deletes them

## Implementation Notes

## Outcome

## Issues Encountered
