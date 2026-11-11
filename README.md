# PortfolioCostEngine

Upload a prospect's bank and product documents; get the all-in annual cost of their portfolio, every
figure traced to its source, the gaps listed, and a fair comparison with an alternative proposal.
Built first for Safe Capital (Lugano), generic for any wealth manager or family office.

> **No source, no verified figure. Missing is never zero. No comparable service, no savings claim.**

Status: foundation in place (protocol, toolchain, backlog). The app is being built story by story:
see [backlog/BOARD.md](backlog/BOARD.md). All demo data is synthetic.

## Start here

| You are | Read |
|---|---|
| A person | this README, [docs/adr/](docs/adr/README.md), [backlog/BOARD.md](backlog/BOARD.md) |
| An AI agent (Claude Code, Codex, Cursor) | [CLAUDE.md](CLAUDE.md), [AGENTS.md](AGENTS.md), [docs/WORKFLOW.md](docs/WORKFLOW.md) |
| Setting up a machine | [docs/SETUP.md](docs/SETUP.md) |

```bash
./scripts/bootstrap.sh                                     # OCR packages, Python env, git hooks
cd backend && uv run python -m pce.extraction.toolchain    # which engines this machine has
./scripts/local-gate.sh                                    # lint + tests + build + secret scan
node scripts/backlog-board.mjs --ready                     # what can be worked on next
```

## Layout

| Path | What |
|---|---|
| `backend/` | Python 3.12 package `pce`: intake, extraction, instruments, finance, scenarios, API (FastAPI) |
| `frontend/` | Vite + React + TypeScript analyst workspace and client report |
| `data/taxonomy/` | fee and document taxonomies (researched, sourced) |
| `data/synthetic/` | synthetic demo and test data only |
| `docs/adr/` | architecture decisions · `docs/research/` sourced research · `docs/design/` design system |
| `backlog/` | epics and stories (`tasks/`), template, generated board |
| `scripts/` | claim, backlog, gate and setup scripts |
| `slides/` | executive deck |

## Principles

- Local-first: client documents never leave the machine by default ([ADR 0004](docs/adr/0004-privacy-local-first.md)).
- Exact money: `Decimal`, evidence on every figure, explicit unknowns ([.claude/rules/finance.md](.claude/rules/finance.md)).
- Open, commercially safe licences only ([ADR 0003](docs/adr/0003-document-extraction-and-ocr.md)).
