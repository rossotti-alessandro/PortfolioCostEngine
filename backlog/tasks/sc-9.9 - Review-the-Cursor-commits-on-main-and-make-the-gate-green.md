---
id: SC-9.9
title: Review the Cursor commits on main and make the gate green
status: "In Progress"
assignee: []
owner: "Rebuild CRM for mobile and browser"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-m6dkdk"
pr: ""
created_date: "2026-11-25 19:45"
updated_date: "2026-11-25 19:37"
labels:
  - quality
dependencies: []
parent_task_id: SC-9
priority: P0
paths_owned:
  - "backend/src/pce/analysis.py"
  - "backend/src/pce/api.py"
  - "backend/src/pce/report.py"
  - "backend/src/pce/extraction/parsers.py"
  - "backend/tests/test_extraction_correctness.py"
  - "backend/tests/test_parallel_read.py"
  - "frontend/src/pages/Compare.tsx"
  - "frontend/src/pages/Costs.tsx"
  - "frontend/src/pages/Report.tsx"
spec_ref: AGENTS.md
rule_refs:
  - ".claude/rules/finance.md"
  - ".claude/rules/testing.md"
---

> **One-liner**: Three commits made with Cursor landed on main without a story or PR and left the gate red; review them, keep what is right, and make `local-gate.sh` pass again.

## Description

### Context

On 2026-11-25 at 19:25 UTC three commits were pushed straight to `main`, co-authored by Cursor:

| Hash | Subject |
| ---- | ------- |
| 18c1e38 | fix(extraction): keep real fees, run OCR on macOS |
| 3825346 | feat(cost): treat a missing KID as unknown, not zero |
| 30c1764 | feat(ui): give the document the Check values pane |

No claim, no story file, no PR, no gate run. `./scripts/local-gate.sh` on main fails on ruff check
(3 errors), ruff format (5 files) and biome format (Compare, Costs, Report). pytest is green once the
OCR system packages are installed (tesseract with ita/deu/fra, ghostscript, qpdf, libmagic1).

### User Flow Impact

None from this story: formatting and line-length fixes only.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Review each commit against CLAUDE.md invariants, the finance rules and the tests.
2. `ruff check --fix`, `ruff format`, `biome check --write`; wrap the one over-long Italian string by hand.
3. Run the full gate and the Playwright suite.

### Risks & Follow-ups

Two semantic changes in 3825346 touch rule-9 areas and need Ale's explicit OK (see Outcome).

## Acceptance Criteria

- [ ] #1 `./scripts/local-gate.sh` prints GATE PASSED on the branch
- [ ] #2 No behaviour change: pytest, vitest and Playwright results equal those of main before the fix

## Implementation Notes

Review verdict per commit:

- **18c1e38 (extraction)**: keep. `os.sched_getaffinity` guarded for macOS with a test; OCR amounts
  without thousands separators stay debits; footers, invested examples, rate ranges and FX/order labels
  no longer become custody or advisory fees. Covered by tests.
- **3825346 (cost)**: keep. In line with "missing is never zero": a fund/ETF without a KID becomes an
  explicit UNKNOWN atom; unvalued books show no CHF 0 and claim no saving. It also closes a real gap:
  before it, an analyst could read and overwrite the firm's internal economics through
  `GET/PUT /api/prospects/{id}/proposal` (only `/internal` was gated). New test
  `test_analyst_cannot_read_or_rewrite_internal_economics`.
  Needs Ale's rule-9 OK, not fixed here:
  1. `finance/scenarios.py` gains `Comparison.saving_claimed` (shared finance contract changed without a story).
  2. `_product_gap` now treats a directly held bond with a valid ISIN as a product with an UNKNOWN
     ongoing charge. A plain bond has no ongoing charge, so a portfolio with bonds can never be
     "complete". Suggest: bonds -> not applicable unless the name says fund/ETF.
- **30c1764 (UI)**: keep. Review page split into `review/DocumentStage`, `DocumentSwitcher`,
  `ValueRail`; desktop sidebar collapses; unknown shown instead of CHF 0. Only biome formatting was off.

Process: work done in Cursor must follow the same protocol (claim, branch, PR, gate). AGENTS.md
already says so; no rule change needed.

## Outcome

- **Status**: partial

## Issues Encountered

A fresh cloud container needs `apt-get install tesseract-ocr tesseract-ocr-ita tesseract-ocr-deu
tesseract-ocr-fra ghostscript qpdf libmagic1` or six tests fail for environment reasons.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
