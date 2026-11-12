---
id: SC-5.15
title: Background job queue for many documents at once
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-12 21:05"
updated_date: "2026-11-12 21:05"
labels:
  - extraction
  - backend
dependencies: [] # after SC-5.11 (PR #21) merges
parent_task_id: SC-5
priority: P1
paths_owned:
  - "backend/src/pce/jobs.py"
  - "backend/tests/test_jobs.py"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs: [".claude/rules/extraction.md"]
---

> **One-liner**: Uploading a full prospect pack (10 to 30 PDFs) queues each document, survives a restart,
> and shows progress, instead of extracting inside the upload request.

## Description

### Context

A real prospect brings several statements, a cost report, a price list and many KIDs. Extraction runs per
request today; PR #21 (SC-5.11) moves it off the event loop and parallelises OCR inside one document, but
there is no queue, no retry, and a restart loses work in progress.

### User Flow Impact

The analyst drops the whole pack, sees each document queued, running or done, and can leave the page.

### Performance / Efficiency Impact

Bounded workers (one per core minus one); total time for a pack dominated by OCR of scans.

### Proposed Approach

1. A small SQLite/Postgres-backed job table (no new broker for the local pilot) with status per document.
2. N worker threads or processes pull jobs; restart re-queues `running` jobs.
3. Upload returns at once; the existing progress view reads the job table.

### Risks & Follow-ups

Touches the schema (shared contract). Coordinate with SC-11.2 (Postgres).

## Acceptance Criteria

- [ ] #1 A 20-document synthetic pack completes with every document done, and a restart mid-run loses no document
- [ ] #2 Single-document upload behaves as before (existing pipeline tests pass)

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
