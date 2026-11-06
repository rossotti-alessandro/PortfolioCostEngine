---
id: SC-3
title: Canonical data model and API contract
status: To Do
assignee: []
created_date: "2026-11-06 15:05"
updated_date: "2026-11-06 15:05"
labels:
  - epic
  - data
dependencies: []
priority: P0
---

> **One-liner**: Typed facts with provenance, storage, OpenAPI contract shared by backend and frontend.

Status and progress are computed from the stories by `scripts/backlog-board.mjs`.

## Stories

- SC-3.1 Domain model: facts, evidence, fee atoms with status (Pydantic)
- SC-3.2 Storage: SQLAlchemy models, Alembic migrations, tenant scoping
- SC-3.3 OpenAPI contract and generated TypeScript client
