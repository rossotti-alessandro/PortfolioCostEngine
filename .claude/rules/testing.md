---
description: Testing tiers, the change loop and the evidence a PR must carry.
paths:
  - "backend/**"
  - "frontend/**"
---

# Testing

## Change loop (every bug fix and feature)

PINPOINT (reproduce, exact file + line) → TEST FIRST (it must fail) → FIX (minimal) → RETEST (passes) →
REGRESSION (module suite green) → COMMIT (conventional, "why" in the body) → update the story.

## Tiers (as they exist on `main`)

| Tier | Where | Runs | Rule |
|---|---|---|---|
| Backend | `backend/tests/test_*.py` (one file per area) | `local-gate.sh` (and `--fast` without `ocr`/`docling`) | no network; disk only under `tmp_path`; real parsers on synthetic fixtures; mark `@pytest.mark.ocr` / `@pytest.mark.docling` when a test needs that engine |
| Frontend unit | `frontend/src/**/*.test.ts` | `local-gate.sh` (vitest) | pure logic: formatting, i18n, trail |
| Accuracy | `backend/tests/evaluation/` + `python -m pce.evaluation` | synthetic protocol in the gate; full corpora on demand and for every extraction change | `docs/EVALUATION_PROTOCOL.md`; results to `artifacts/eval/<ISO-ts>/` |
| E2E | `frontend/tests/e2e/*.spec.ts` (Playwright) | on demand: `cd frontend && pnpm e2e` (not in the gate yet) | upload → review → costs → compare → report on a SYNTHETIC prospect, EN and IT |

Run the module you touch while iterating (`uv run pytest tests/test_<area>.py -q`, `pnpm test --run`),
the full gate before the PR. UI stories run the E2E flow they change and attach the screenshots.

## Rules

- Fixtures are synthetic, generated in code where possible (see `backend/tests/conftest.py`), and marked
  SYNTHETIC. Real public specimens are fetched to `var/`, never committed.
- Invariants get property or table tests: totals reconcile, no double counting, re-import is idempotent,
  missing never becomes zero.
- A test that needs Tesseract and is not marked `ocr` is a bug (SC-1.6): mark it, do not skip it.
- Never skip, weaken or delete a failing test to get green, and never update an expected number just to
  pass. If the expected number was wrong, say why in the commit body. Otherwise file a story.
- Flaky test: reproduce it (run it in a loop), fix the cause or file a story. No retries-until-green.
