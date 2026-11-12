---
id: SC-5.9
title: Single-thread Tesseract so scans stay fast on a busy CPU
status: Done
assignee: []
owner: "Fix slow reading of scanned pages"
model: "claude-opus"
progress: 100
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

Through the app's own OCR path (`layout._ocr_lines`, an oversized synthetic page), 4 busy loops:
`OMP_THREAD_LIMIT=4` did not finish in 170 s, `OMP_THREAD_LIMIT=1` took 19.6 s. Idle: 14.9 s vs 15.3 s.

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

- [x] #1 Importing `pce.extraction` sets `OMP_THREAD_LIMIT=1` when unset (tested)
- [x] #2 An explicit `OMP_THREAD_LIMIT` is kept (tested)
- [x] #3 Gate green

## Implementation Notes

- Owned paths as declared. No overlap with PR #15 (edits `layout.py`, adds `verify.py`) or PR #16: both
  call Tesseract through modules inside `pce.extraction`, so both get the limit without edits.
- `node scripts/backlog-new-id.mjs --help` has no help flag and reserved top-level id SC-12 by mistake
  (branch `backlog-ids/sc-12`, unused). The proxy refuses ref deletion; the coordinator can reuse it.

## Outcome

- **Status**: completed
- Every Tesseract call made from the backend now runs single-threaded unless `OMP_THREAD_LIMIT` is
  set explicitly. The Docker image (Render) already set it, so the live demo does not change.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-gb52v5 | 16c227f | 2026-11-12 | fix(extraction): run Tesseract single-threaded by default |

## Issues Encountered

- The gate's toolchain test needs `gs` and `qpdf` installed (bootstrap.sh does it); a bare cloud
  container without them fails `test_required_components_present`, unrelated to this change.
