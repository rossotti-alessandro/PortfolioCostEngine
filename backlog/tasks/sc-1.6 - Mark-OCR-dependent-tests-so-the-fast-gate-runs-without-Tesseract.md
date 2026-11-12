---
id: SC-1.6
title: Mark OCR-dependent tests so the fast gate runs without Tesseract
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
  - process
  - testing
dependencies: []
parent_task_id: SC-1
priority: P3
paths_owned:
  - "backend/tests/test_crm.py"
  - "backend/tests/test_api.py"
  - "backend/tests/conftest.py"
spec_ref: docs/WORKFLOW.md
rule_refs: [".claude/rules/testing.md"]
---

> **One-liner**: `local-gate.sh --fast` fails in a fresh container because three unmarked tests call
> Tesseract; mark them so fast runs skip them and full runs still require the OCR packages.

## Description

### Context

Seen 2026-11-12 on main 87f02a4 in a fresh cloud container: `--fast` (`-m 'not ocr and not docling'`)
gave 3 failed, 100 passed, all `FileNotFoundError: tesseract`, starting with
`test_crm.py::test_seed_is_idempotent_synthetic_and_funnel_is_consistent` (seeding runs extraction).

### User Flow Impact

None; agents get a correct fast signal.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Mark the tests that seed or extract scanned pages with `@pytest.mark.ocr`, or skip in conftest when
   `shutil.which("tesseract")` is None and the run is `--fast`.
2. Keep the full gate failing loudly when Tesseract is missing.

### Risks & Follow-ups

None.

## Acceptance Criteria

- [ ] #1 `./scripts/local-gate.sh --fast` passes on a container without Tesseract
- [ ] #2 The full gate still fails without Tesseract and passes with it

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
