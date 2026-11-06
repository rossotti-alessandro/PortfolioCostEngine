---
id: SC-1.3
title: One-command local run: Docker Compose, seed and runbook
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
  - infra
dependencies:
  - SC-3.2
  - SC-8.1
parent_task_id: SC-1
priority: P0
paths_owned:
  - "deployment/**"
  - "docker-compose.yml"
  - "Makefile"
  - "docs/RUNBOOK.md"
spec_ref: docs/adr/0001-stack.md
rule_refs: []
---

> **One-liner**: Let Safe Capital start the whole app offline with one command on a laptop.

## Description

### Context

Backend and frontend run separately in dev; nothing packages them for a non-developer.

### User Flow Impact

Analyst runs `docker compose up` (or `make demo`) and opens the app with the synthetic prospect loaded.

### Performance / Efficiency Impact

Image size matters: core image without PyTorch; Docling image optional.

### Proposed Approach

1. Backend image with Tesseract langs
2. Frontend static build served by the API container
3. Seed command for synthetic prospect
4. Runbook: start, stop, reset, where data lives, how to delete it

### Risks & Follow-ups

See `docs/adr/0001-stack.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Fresh machine with Docker: `docker compose up` serves the app with seeded data in under 5 minutes
- [ ] #2 No network access needed after images are built (verified with network disabled)
- [ ] #3 Data directory is outside the image and deletable

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
