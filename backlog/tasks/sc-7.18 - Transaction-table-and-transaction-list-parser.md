---
id: SC-7.18
title: Transaction table and transaction-list parser
status: "Done"
assignee: []
owner: "Compute every portfolio cost end to end"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-p3z1fq"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/88"
created_date: "2026-11-26 01:10"
updated_date: "2026-11-26 13:40"
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
  - "backend/src/pce/analysis.py"
  - "backend/src/pce/erasure.py"
  - "backend/src/pce/extraction/models.py"
  - "backend/src/pce/pipeline_view.py"
  - "frontend/src/pages/review/shared.ts"
  - "frontend/src/lib/it.ts"
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

- [x] #1 A synthetic transaction list gives one row per trade with evidence
- [x] #2 Re-import is idempotent; another firm cannot read the rows; erasure deletes them

## Implementation Notes

- `parsers._trade_fact`: a dated line with a side word (buy/acquisto/kauf/achat, sell/vendita/verkauf/vente)
  and a valid ISIN, or an FX conversion (spot, conversion, cambio valuta, a currency pair), becomes a
  `transaction` fact: side, ISIN, gross amount (last number), currency (a code on the line, else the
  statement's), page + bbox. A line naming a fee (commission, fee, courtage, bollo, stamp...) stays a fee debit.
- Quantity is kept only when quantity × price (shares) or nominal × price / 100 (bonds) is within 1% of the
  gross amount; otherwise it is `None`, never guessed.
- `analysis._transactions` dedups across documents of one bank (a second copy of a list adds nothing), but
  keeps two identical fills printed in one list. Output key `transactions`; costs unchanged.
- `Transaction` table (tenant, prospect, account, fact_id unique per tenant), rebuilt by `book_of_record.sync`;
  a bank seen only on a transaction list gets an account. Erasure deletes the rows.

## Outcome

Synthetic transaction lists give one trade per line with evidence; re-import is idempotent, another firm
reads nothing, erasure deletes the rows. Fix on the way: an FX conversion line ("FX spot USD/CHF 10'000")
on a cash statement used to be read as an FX *commission* debit of the whole amount; it is now a trade. On
the public corpus no real sample has a full-date + ISIN trade list: the Fidelity US layout (year-less dates,
tickers, charges column) is SC-7.24.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-p3z1fq | 8f61a70 | 2026-11-26 | Transaction lists into a trade table |

## Issues Encountered

- Real trade tables sit inside statements with tickers and year-less dates: SC-7.24.
