---
id: SC-7.12
title: Book of record: accounts, instruments, positions, transactions
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

- [ ] #1 Re-import of the same documents is idempotent
- [ ] #2 Tenant A cannot read tenant B positions (test)
- [ ] #3 Positions add up to the statement total from the tables

## Implementation Notes

## Outcome

## Issues Encountered
