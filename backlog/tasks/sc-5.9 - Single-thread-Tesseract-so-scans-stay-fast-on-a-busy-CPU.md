---
id: SC-5.9
title: Single-thread Tesseract so scans stay fast on a busy CPU
status: "In Progress"
assignee: []
owner: "Fix slow reading of scanned pages"
model: "claude-opus"
progress: 5
branch: "claude/project-thread-gb52v5"
pr: ""
created_date: "2026-11-12 00:40"
updated_date: "2026-11-12 00:36"
labels:
  - extraction
  - performance
dependencies: []
parent_task_id: SC-5
priority: P1
paths_owned:
  - "backend/src/pce/extraction/__init__.py"
  - "backend/tests/test_ocr_threads.py"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs:
  - ".claude/rules/extraction.md"
---

> **One-liner**: Stop one scanned page from taking minutes to OCR whenever anything else uses the CPU.

## Description

### Context

Tesseract 5 uses OpenMP threads by default, and those threads busy-wait. When other work shares the
CPU (pytest, a benchmark, a second upload, a small cloud instance), one 300 dpi page can take minutes
instead of seconds. The model lab thread measured 14 to 85 minutes for one page under load and 1.9 s
with `OMP_THREAD_LIMIT=1`. The Docker image already sets `OMP_THREAD_LIMIT=1` (Dockerfile), so the
Render demo is covered; every other way of running the backend (`uv run`, pytest, lab and benchmark
scripts that import `pce.extraction`) is not.

Reproduced on a 4-core cloud container, synthetic 300 dpi A4 page (60 text lines), `tesseract --psm 6`:

| CPU | default threads | `OMP_THREAD_LIMIT=1` |
|---|---|---|
| idle | 1.96 s | 2.03 s |
| 4 busy loops | 86.6 s | 2.41 s |

### User Flow Impact

An analyst uploading a scanned statement on a machine doing anything else waits seconds, not minutes.

### Performance / Efficiency Impact

Under load: about 35x faster per page. Idle: same speed (OCR already runs one page at a time).

### Proposed Approach

1. In `pce/extraction/__init__.py`, `os.environ.setdefault("OMP_THREAD_LIMIT", "1")`. Every Tesseract
   call (`layout._ocr_lines` and the second reader in `verify.py`) goes through `pytesseract`, a
   subprocess that inherits the environment, and every module importing them imports the package
   first. `setdefault` keeps an explicit operator override.
2. Test: importing `pce.extraction` leaves `OMP_THREAD_LIMIT` set to `1` in the environment that
   subprocesses inherit, and an explicit value is not overwritten.

### Risks & Follow-ups

- A process-wide env change also limits any other OpenMP library the backend loads in the same process
  (none today in the default install). An operator can set `OMP_THREAD_LIMIT` explicitly to override.

## Acceptance Criteria

- [ ] #1 Importing `pce.extraction` sets `OMP_THREAD_LIMIT=1` when unset (tested)
- [ ] #2 An explicit `OMP_THREAD_LIMIT` is kept (tested)
- [ ] #3 Gate green

## Implementation Notes

## Outcome

- **Status**: <!-- completed | partial | blocked -->

## Issues Encountered
