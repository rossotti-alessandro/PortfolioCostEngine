---
id: SC-7.12
title: Book of record: accounts, instruments, positions, transactions
status: "Done"
assignee: []
owner: "Design complete portfolio cost protocol"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-7crdzy"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/81"
created_date: "2026-11-25 20:50"
updated_date: "2026-11-26 01:00"
labels:
  - finance
  - db
dependencies:
  - SC-2.4
parent_task_id: SC-7
priority: P1
paths_owned:
  - "backend/src/pce/db.py"
  - "backend/src/pce/db/**"
  - "backend/tests/test_book_of_record.py"
spec_ref: docs/research/COST_PROTOCOL.md
rule_refs:
  - ".claude/rules/finance.md"
  - ".claude/rules/privacy.md"
---

> **One-liner**: Store the family's accounts, instruments, dated positions and transactions as tables, so costs attach to real objects and outside data can be cached.

## Description

### Context

db.py holds Prospect, Document, FactRow, Review and AuditEvent only. Each analysis rebuilds holdings as dicts from loose facts; there is no transaction table, so turnover-driven costs (brokerage, stamp duty, FTT, FX volume) can be neither estimated nor checked against the tariff.

### User Flow Impact

Foundation for SC-6.1 catalog, SC-7.13 claims and SC-7.14 implicit costs; no visible change at first.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Tables: Entity, Account, Instrument (public master, not tenant data), Position (dated), Transaction, all tenant- and prospect-scoped except Instrument.
2. Builder from accepted facts, idempotent on re-import.
3. Transaction parser for transaction lists and trade confirmations (separate story if large).

### Risks & Follow-ups

Shared contract (db/**): one story at a time; migration path from current facts needed. Tenant isolation test required.

## Acceptance Criteria

- [x] #1 Re-import of the same documents is idempotent
- [x] #2 Tenant A cannot read tenant B positions (test)
- [x] #3 Positions add up to the statement total from the tables

## Implementation Notes

- Owned paths as listed, plus `backend/src/pce/book_of_record.py` (builder), `backend/src/pce/api.py`
  (`refresh_book` after upload, reclassification, fact review and demo seed) and `backend/src/pce/erasure.py`
  (erasing a prospect deletes its rows). No migration tool exists; `create_all` adds the new tables.
- Tables: `account` (tenant, prospect, institution, jurisdiction), `instrument` (public master keyed by ISIN,
  shared across tenants, no value, quantity or account), `position` (tenant, prospect, account, ISIN or none,
  name, asset class, statement date, currency, value in its currency, CHF value or none, fact id).
- Built from the analysis result, not from raw facts, so duplicate statements, lots, FX and asset-class rules
  are applied once. The prospect's rows are replaced on every rebuild: re-import gives the same rows.
- Entity (family members, companies) left out: no document gives it yet. Transactions moved to SC-7.18,
  because no parser produces trade facts and the table would have stayed empty.
- `position.fact_id` has no foreign key: reclassifying a document replaces its facts before the rebuild.

## Outcome

- **Status**: completed
- `backend/tests/test_book_of_record.py`: 4 tests (statement total, idempotent rebuild, cross-firm isolation,
  erasure). Seeding P-1042 through the API gives 10 positions adding up to CHF 4,300,000.00.
- Rebuilds happen only when documents or facts change, never on a read.

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-7crdzy | 9a347d2 | 2026-11-26 | Account, Instrument, Position tables, builder, tests |
