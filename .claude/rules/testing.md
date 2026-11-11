---
description: Testing tiers and the change loop.
paths:
  - "backend/**"
  - "frontend/**"
---

# Testing

## Change loop (every bug fix and feature)

PINPOINT (reproduce, exact file + line) → TEST FIRST (it must fail) → FIX (minimal) → RETEST (passes) →
REGRESSION (module suite green) → COMMIT (conventional, "why" in the body) → update the story.

## Tiers

| Tier | Where | Runs | Rule |
|---|---|---|---|
| Unit | `backend/tests/unit`, `frontend/src/**/*.test.ts` | every commit (pre-push fast gate) | pure logic, no network, no disk outside `tmp_path` |
| Integration | `backend/tests/integration` | `local-gate.sh` | real parsers on synthetic fixtures; mark `@pytest.mark.ocr` / `docling` when they need those engines |
| Evaluation | `backend/tests/evaluation` | on demand + before release | golden corpus, per-field exact match, bbox correctness, abstention; writes `artifacts/eval/<ISO-ts>/report.md` |
| E2E | `frontend/tests/e2e` (Playwright) | `local-gate.sh` (full) | upload → review → costs → report on the seeded synthetic prospect |

- Fixtures are synthetic, generated in code where possible (see `backend/tests/conftest.py`), and marked SYNTHETIC.
- Property tests (Hypothesis) for invariants: totals reconcile, no double counting, re-import is idempotent,
  missing never becomes zero.
- Never skip or delete a failing test to get green. File a story with the failure instead.
