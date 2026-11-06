# PortfolioCostEngine — Claude Code instructions

Multi-agent protocol: @AGENTS.md
Step-by-step workflow (claim, change loop, PR, merge train): [docs/WORKFLOW.md](docs/WORKFLOW.md).
Where each topic is decided: [docs/SOURCES_OF_TRUTH.md](docs/SOURCES_OF_TRUTH.md). It wins over every other doc.

## What this is

A tool for a Swiss wealth manager or family office. An analyst uploads a prospect's bank and product
documents; the system extracts positions and every cost with its evidence, validates and merges them,
classifies them into cost layers, flags what is missing, and shows the all-in annual cost next to an
alternative proposal. Generic by design (any bank, any manager); first user is Safe Capital, Lugano.

**Product principle: no source, no verified figure. Missing is never zero. No comparable service, no
savings claim.**

## Stack (ADR 0001)

- `backend/`: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (SQLite now, PostgreSQL later), `uv`, Ruff, pytest.
  Package `pce` (`backend/src/pce`). Money in `Decimal` only.
- `frontend/`: Vite + React + TypeScript (strict) + React Router + Tailwind v4 + shadcn/ui + Recharts + PDF.js. `pnpm`, Biome, Vitest, Playwright.
- Extraction: pdfplumber, pypdfium2, Docling (extra), OCRmyPDF + Tesseract (eng/ita/deu/fra), openpyxl. No PyMuPDF (AGPL). ADR 0003.
- Local-first, no client data to external AI by default. ADR 0004.

## Commands

```bash
./scripts/bootstrap.sh [--docling]          # one-time: OCR packages, Python env, git hooks
cd backend && uv run python -m pce.extraction.toolchain   # what can this machine extract?
cd backend && uv run pytest                  # backend tests
./scripts/local-gate.sh                      # THE gate before every PR (CI runs the same script)
node scripts/backlog-board.mjs --ready       # what can I claim?
node scripts/claims-status.mjs               # who is on what (remote evidence)
```

## Ground truth to read before a task

| Task touches | Read first |
|---|---|
| Costs, fees, scenarios | `.claude/rules/finance.md`, `docs/research/FEE_TAXONOMY.md`, `data/taxonomy/fee_taxonomy.csv` |
| Documents, OCR, parsing | `.claude/rules/extraction.md`, ADR 0003, `docs/research/DOCUMENT_TAXONOMY.md` |
| Uploads, logs, any external call | `.claude/rules/privacy.md`, ADR 0004 |
| UI | `.claude/rules/frontend.md`, `docs/design/DESIGN_SYSTEM.md`, `docs/research/UX_RECOMMENDATIONS.md` |
| Backlog files | `.claude/rules/task-lifecycle.md`, `backlog/TEMPLATE.md` |

The ChatGPT handoff kit is **input, not truth**: `docs/CRITICAL_REVIEW.md` lists what was wrong in it.

## Critical invariants (regret if forgotten)

- `Decimal` for money and rates, built from strings. No floats in `finance/`. No LLM arithmetic.
- Every fee atom: status (`observed|contractual|estimated|illustrative|unknown|not_applicable`) + evidence
  (page + bbox, or sheet + cell, or URL). Unknown amount is `None`, not `0`.
- Inclusion graph: AMF inside OCF counts once (1.08%, not 1.83%). Wrap fees replace, not add.
- Tariffs apply only to their booking jurisdiction and dates. Product costs match exact ISIN + share class.
- Internal margin never appears in a client-facing payload (tested).
- Never `import ocrmypdf` in-process (it patches pdfminer); call the CLI. Never add PyMuPDF.
- No real client data in git, fixtures, logs, screenshots or prompts. Synthetic data says SYNTHETIC.

## Agent working style

- **Replies to people: caveman lite** (skill `caveman`, level `lite`): answer first, short full sentences,
  no filler. Drop it for security warnings and irreversible-step confirmations. Never caveman in code,
  comments, commit messages, PR bodies, docs, ADRs or stories: those stay complete and professional.
- **Code: ponytail** (skill `ponytail`, level `full`): the smallest change that fully solves the task;
  reuse before adding; no speculative options. This repo's invariants, tests and evidence rules are
  requirements, not boilerplate, and always win.
- **Review: `ponytail-review`** (is every line needed, is risky logic tested) plus the finance and privacy rules.
- Skills live in `.agents/skills/` (read by Codex) and are symlinked into `.claude/skills/`. Versions: `skills-lock.json`.

## Coding standards

- Python: type hints everywhere, Pydantic models at every boundary, module docstring on every file,
  one responsibility per function. Domain errors subclass `pce.errors.PceError`.
- TypeScript: strict, no `any`, no `@ts-ignore`. API types generated from the FastAPI OpenAPI schema.
- TODOs name a story: `# TODO(SC-7.3): …`.
- Comments explain why, not what.

## Git

- Story branches `claude/sc-<id>-<slug>` (other agents: `codex/…`, `cursor/…`), from fresh `origin/main`.
- Conventional commits (`feat(finance): …`), enforced by `.githooks/commit-msg`. Push after every commit.
- One story = one branch = one PR into `main`. Never bundle stories. Never `git stash`. Never force-push a shared branch.
- Hooks: `./scripts/setup-hooks.sh` once per clone.
