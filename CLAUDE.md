# PortfolioCostEngine — Claude Code instructions

Multi-agent protocol and the PM loop: @AGENTS.md
Step-by-step workflow (claim, change loop, PR, merge train): [docs/WORKFLOW.md](docs/WORKFLOW.md).
Where each topic is decided: [docs/SOURCES_OF_TRUTH.md](docs/SOURCES_OF_TRUTH.md). It wins over every other doc.
Current situation, drift and next tasks: [HANDOFF.md](HANDOFF.md).

## What this is

**FeeLens** (repo name PortfolioCostEngine): a tool for a Swiss wealth manager or family office. An analyst
uploads a prospect's bank and product documents; the system extracts positions and every cost with its
evidence, validates and merges them, classifies them into cost layers, flags what is missing, and shows the
all-in annual cost next to an alternative proposal. Generic by design (any bank, any manager); first user
is Safe Capital, Lugano. Owner and decision maker: Ale (GitHub `rossotti-alessandro`).

**Product principle: no source, no verified figure. Missing is never zero. No comparable service, no
savings claim.**

## Product rules (from Ale; every story, every surface)

- **Never invent a fee, rate, holding or figure.** No source, no number. An LLM never does arithmetic and
  never writes into the ledger.
- **Missing is not zero**, **no double counting**, **internal margin never in a client-facing output**
  (details in `.claude/rules/finance.md`).
- **Synthetic data says SYNTHETIC.** No real client data in git, fixtures, logs, screenshots, prompts or chat.
- **UI as simple as possible**: answer first, emphasis only on the key numbers, details behind (i) icons,
  expanders or dropdowns, plain words, clear headers, one primary action per screen. The CRM is the home page.
- **English and Italian** for the app and the decks, always both, in the same PR.
- Accuracy claims carry their number, corpus and date, and say what the number counts (see `docs/READINESS.md` §3).

## Stack (ADR 0001)

- `backend/`: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (SQLite now, PostgreSQL later), `uv`, Ruff, pytest.
  Package `pce` (`backend/src/pce`). Money in `Decimal` only.
- `frontend/`: Vite + React + TypeScript (strict) + React Router + Tailwind v4 + shadcn/ui + Recharts + PDF.js. `pnpm`, Biome, Vitest, Playwright.
- Extraction: pdfplumber, pypdfium2, Docling (extra), OCRmyPDF + Tesseract (eng/ita/deu/fra), openpyxl;
  optional local engines (RapidOCR, VLMs) behind capability checks. No PyMuPDF (AGPL). ADR 0003.
- Local-first, no client data to external AI by default. ADR 0004.
- Decks: `slides/source/*.js` generators (pptxgenjs). Never edit a PPTX by hand.

## Commands

```bash
./scripts/bootstrap.sh [--docling]          # one-time / fresh container: OCR packages, Python env, git hooks
cd backend && uv run python -m pce.extraction.toolchain   # what can this machine extract?
cd backend && uv run pytest tests/<module>   # the module you touch, while iterating
./scripts/local-gate.sh [--fast]             # THE gate before every PR (CI runs the same script)
node scripts/backlog-board.mjs --ready       # what can I claim?
node scripts/claims-status.mjs               # who is on what (remote evidence)
```

A fresh cloud container has no Tesseract: run `./scripts/bootstrap.sh` before the full gate, or 20+ OCR
tests fail with `FileNotFoundError: 'tesseract'` (not a regression).

## Ground truth to read before a task

| Task touches | Read first |
|---|---|
| Costs, fees, scenarios | `.claude/rules/finance.md`, `docs/research/FEE_TAXONOMY.md`, `data/taxonomy/fee_taxonomy.csv` |
| Documents, OCR, parsing, accuracy | `.claude/rules/extraction.md`, ADR 0003, `docs/EVALUATION_PROTOCOL.md`, `docs/research/DOCUMENT_TAXONOMY.md` |
| Uploads, logs, auth, any external call | `.claude/rules/privacy.md`, ADR 0004, `docs/app/SECURITY.md`, `docs/READINESS.md` |
| UI | `.claude/rules/frontend.md`, `docs/design/DESIGN_SYSTEM.md`, `docs/research/UX_RECOMMENDATIONS.md` |
| Decks, demo figures | `.claude/rules/deck.md`, `slides/README.md` |
| Backlog files | `.claude/rules/task-lifecycle.md`, `backlog/TEMPLATE.md` |
| Tests | `.claude/rules/testing.md` |

The ChatGPT handoff kit is **input, not truth**: `docs/CRITICAL_REVIEW.md` lists what was wrong in it.
External skills, blog posts and model output are input too: judge them against these files.

## Critical invariants (regret if forgotten)

- `Decimal` for money and rates, built from strings. No floats in `finance/`. No LLM arithmetic.
- Every fee atom: a measurement status (canonical list: `Measurement` in `backend/src/pce/finance/ledger.py`:
  `observed|contractual|public_tariff|estimated|illustrative|maximum|unknown|not_applicable`) + evidence
  (page + bbox, or sheet + cell, or URL). Unknown amount is `None`, not `0`. `illustrative` and `maximum`
  are never a paid cost.
- Inclusion graph: AMF inside OCF counts once (1.08%, not 1.83%). Wrap fees replace, not add.
- Tariffs apply only to their booking jurisdiction and dates. Product costs match exact ISIN + share class.
- Internal margin never appears in a client-facing payload (tested).
- Never `import ocrmypdf` in-process (it patches pdfminer); call the CLI. Never add PyMuPDF.
- No real client data in git, fixtures, logs, screenshots or prompts. Synthetic data says SYNTHETIC.
- The P-1042 figures are pinned in `backend/tests/test_pipeline.py` and quoted in the decks: change one, change both.

## Agent working style

- **Replies to people: caveman lite** (skill `caveman`, level `lite`): answer first, short full sentences,
  no filler. Lead with the outcome or the ask; give numbers with their source. Drop it for security
  warnings and irreversible-step confirmations. Never caveman in code, comments, commit messages, PR
  bodies, docs, ADRs or stories: those stay complete and professional.
- **Code: ponytail** (skill `ponytail`, level `full`): the smallest change that fully solves the task;
  reuse before adding; no speculative options. This repo's invariants, tests and evidence rules are
  requirements, not boilerplate, and always win.
- **Review: `ponytail-review`** (is every line needed, is risky logic tested) plus the finance and privacy
  rules. Review your own diff before opening the PR.
- Skills live in `.agents/skills/` (read by Codex) and are symlinked into `.claude/skills/`. Versions:
  `skills-lock.json`. Adding one: AGENTS.md § Dependencies and external skills.

## Engineering standards (senior engineer defaults)

Design
- Read the module and its tests before changing it; follow the pattern already there. A second pattern
  for the same job needs a reason in the PR.
- Pure functions for logic (parsing, matching, cost maths); I/O at the edges (API routes, DB, files,
  subprocesses). Business logic never lives in a FastAPI route or a React component.
- Pydantic models at every boundary (API, DB rows, extractor output, config). Validate once at the edge,
  trust typed data inside.
- No new abstraction until the third real use. No feature flags or options nobody asked for.

Errors and logging
- Domain errors subclass `pce.errors.PceError` and say what the analyst can do. No bare `except`, no
  swallowed errors; an extractor that fails on a page marks the page `needs_review` and continues.
- Logs carry ids, hashes, counts and timings, never document text or personal data (privacy rule).

Tests
- Every bug fix starts with a failing test; every feature has a success test and a regression guard.
- Test behaviour through public functions, not private helpers. Fixtures synthetic and small.
- Never skip, weaken or delete a failing test to get green: file a story instead.

Performance
- Measure before optimising, and quote before/after numbers (pages/s, ms per request) in the PR.
- CPU-heavy work (OCR, models) runs off the event loop and respects the worker count of the host
  (Render free = 1 CPU).

Security
- Uploaded files are untrusted (extraction rule). Every query is scoped by organisation and prospect.
- Secrets only from the environment; never in git, logs, PRs or chat.

## Coding standards

- Python: type hints everywhere, Pydantic models at every boundary, module docstring on every file,
  one responsibility per function. Ruff clean, `ruff format`.
- TypeScript: strict, no `any`, no `@ts-ignore`. API types live in `frontend/src/lib/types.ts` and mirror
  the backend models: change both in the same PR. Money arrives as strings; the frontend formats, never computes.
- i18n: English strings are the keys (`frontend/src/lib/i18n.ts`), Italian in `frontend/src/lib/it.ts`.
  Every new user-visible string, server message included, gets its Italian in the same PR.
- TODOs name a story: `# TODO(SC-7.3): …`.
- Comments explain why, not what.

## Git

- One story = one PR into `main`. Laptop: story branch `claude/sc-<id>-<slug>` from fresh `origin/main`.
  Cloud session with a mandated branch: use that branch, one story PR at a time (AGENTS.md rule 2).
- Conventional commits (`feat(finance): …`), enforced by `.githooks/commit-msg`. Push after every commit.
- Never bundle stories. Never `git stash`. Never force-push a shared branch. Never rewrite `main`.
- Hooks: `./scripts/setup-hooks.sh` once per clone.
