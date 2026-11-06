---
id: SC-3.2
title: Storage: SQLAlchemy models, Alembic migrations, tenant scoping
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-06 15:05"
updated_date: "2026-11-06 15:05"
labels:
  - data
dependencies:
  - SC-3.1
parent_task_id: SC-3
priority: P0
paths_owned:
  - "backend/src/pce/db/**"
  - "backend/alembic/**"
  - "backend/tests/unit/db/**"
spec_ref: docs/adr/0001-stack.md
rule_refs:
  - ".claude/rules/privacy.md"
---

> **One-liner**: Persist facts, evidence, reviews and scenario snapshots with every row scoped to organisation and prospect.

## Description

### Context

No persistence.

### User Flow Impact

Reviews and approvals survive reload.

### Performance / Efficiency Impact

SQLite file; indexes on prospect_id and document sha.

### Proposed Approach

1. Tables mirroring 3.1
2. Immutable originals; review events append-only
3. Scoped session helper that requires org_id

### Risks & Follow-ups

See `docs/adr/0001-stack.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Migration up/down on empty SQLite and PostgreSQL
- [ ] #2 Query helper without org scope raises
- [ ] #3 Approval persisted and reloaded identical

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
