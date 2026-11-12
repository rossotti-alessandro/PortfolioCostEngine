---
id: SC-5.11
title: Read scanned pages in parallel and keep the server responsive
status: Done
assignee: []
owner: "Read document pages in parallel"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-ch9r5h"
pr: ""
created_date: "2026-11-12 14:30"
updated_date: "2026-11-12 14:35"
labels:
  - extraction
  - performance
dependencies: [] # SC-5.9 (PR #17) is not on main yet; see Risks
parent_task_id: SC-5
priority: P1
paths_owned:
  - "backend/src/pce/extraction/layout.py"
  - "backend/tests/test_parallel_read.py"
  - "backend/src/pce/api.py" # upload route only: async def -> def
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs:
  - ".claude/rules/extraction.md"
---

> **One-liner**: A 50-page scan is read on every available core instead of one page at a time, and one upload no longer freezes the app for everyone else.

## Description

### Context
`layout.read_pdf` reads pages one after another. Measured on this machine (4 cores, SYNTHETIC 50-page
documents built from the demo generator, `OMP_THREAD_LIMIT=1`): born-digital 1.0 s for 50 pages, scanned
84 s for 50 pages (about 1.7 s per page, almost all of it Tesseract). Digital reading is not worth
parallelising; OCR is.

Second gap: the upload route is `async def` but calls the synchronous `ingest` (reading, OCR, parsing).
That blocks the event loop, so while one scan is read every other request, from every user, waits.

### User Flow Impact
Scanned statements finish several times faster on a multi-core machine. Other pages and other users stay
responsive during an upload. Extracted values, boxes and review flags are unchanged.

### Performance / Efficiency Impact
OCR pages run on N worker threads. Each thread renders its page under a lock (pdfium is not thread
safe) and then runs Tesseract as a subprocess, which releases the GIL. At most N page images are in
memory at once (about 26 MB per A4 page at 300 dpi), so memory stays bounded.
N comes from the CPU quota the process really has (cgroup `cpu.max`, then CPU affinity), capped at 4 and
overridable with `PCE_OCR_WORKERS`. On Render free (0.15 CPU, 512 MB, measured 2026-11-12) N is 1:
same behaviour and memory as today.

### Proposed Approach
1. `layout.ocr_workers()`: `PCE_OCR_WORKERS`, else cgroup quota, else affinity; min 1, max 4.
2. `read_pdf`: route pages as today (text-layer characters); read digital pages inline; send OCR pages to
   a `ThreadPoolExecutor(ocr_workers())`; keep page order.
3. `api.upload`: plain `def` (FastAPI runs it in its thread pool), file read via `UploadFile.file`.
4. Test: parallel output equals sequential output on the SYNTHETIC scan; worker count parsing.

### Risks & Follow-ups
- Parallel Tesseract without `OMP_THREAD_LIMIT=1` oversubscribes the CPU: depends on SC-5.9 (PR #17); the
  Dockerfile already sets it.
- Several documents at once (document-level parallelism) is a separate step: SQLite writes and the
  sequential upload UI (SC-8.10) would need a job queue first. Not done here.
- `verify.second_reading` (SC-5.8, PR #15) also runs Tesseract once per page; it can reuse `ocr_workers()`
  after both merge.

## Acceptance Criteria

- [x] #1 `read_pdf` output (pages, lines, cells, boxes, engines, confidences) is identical with 1 and 4 workers on the SYNTHETIC scan
- [x] #2 A 50-page SYNTHETIC scan reads at least 2x faster on 4 cores; the number is recorded here
- [x] #3 Worker count respects `PCE_OCR_WORKERS` and a fractional cgroup quota (Render free: 1)
- [x] #4 `python -m pce.evaluation` is unchanged versus main (all gates pass, same scores)
- [x] #5 The upload route no longer blocks the event loop

## Implementation Notes

- Owned paths as declared. `api.py`: only the upload route signature and its file read changed.
- Branch merges PR #17's branch (SC-5.9): without `OMP_THREAD_LIMIT=1`, four parallel Tesseracts
  busy-waited each other and four pages had not finished after 5 minutes.
- Digital pages are read inline: 50 pages take 1.0 s, not worth a pool. Routing (text-layer characters per
  page) is unchanged.

## Outcome

- **Status**: completed
- Measured on 4 cores, SYNTHETIC 50-page scan built from the demo generator: 1 worker 83.7 s, 2 workers
  42.3 s, 4 workers 21.7 s (3.9x). Output hash identical in all three. Python peak memory 177 MB with 1
  worker, 399 MB with 4.
- `python -m pce.evaluation --strategy baseline --variant digital,scan`: identical to main (results.json
  equal once timings are removed; all gates pass).
- Render free (0.15 CPU, 512 MB) gets 1 worker: same speed and memory as before, but other requests are
  no longer frozen during an upload.
- Tests: `backend/tests/test_parallel_read.py` (parallel equals sequential, worker sizing incl. fractional
  quota, upload route is not a coroutine).

## Issues Encountered

- Parallel OCR depends on SC-5.9 (PR #17), merged into this branch. Merge #17 first.
