# ADR 0001 — Application stack

Status: Accepted, 2026-11-06. Deciders: Ale (owner), coordinator.

## Context

The product reads PDFs and spreadsheets, runs OCR, computes costs exactly, and shows evidence next to
every number. It must run on a single office laptop or a small Swiss server for the pilot (ADR 0004),
be buildable by several AI agents in parallel, and stay generic (any bank, any wealth manager).

The best document tooling (pdfplumber, Docling, OCRmyPDF, Tesseract bindings, openpyxl) is Python.
Exact money arithmetic needs a decimal type end to end. The UI is an internal analyst workspace plus a
printable client report: interactive, no SEO, no public pages.

## Decision

| Layer | Choice | Version policy |
|---|---|---|
| Backend language | Python 3.12 | `requires-python >=3.12,<3.14` |
| API | FastAPI + Pydantic v2 (OpenAPI is the contract) | exact pins in `backend/pyproject.toml` |
| Storage | SQLAlchemy 2 + Alembic; SQLite for the local demo, PostgreSQL 16+ for multi-user | same models, migrations from day one |
| Files | local encrypted directory (`PCE_DATA_DIR`) now; S3-compatible store with Swiss region later | content-addressed by SHA-256 |
| Jobs | in-process background tasks for the demo; a DB-backed queue when multi-user | no Redis until needed |
| Money | `decimal.Decimal` from strings; serialised as strings in JSON | no floats |
| Frontend | Vite + React 19 + TypeScript strict + React Router | `pnpm`, lockfile committed |
| UI kit | Tailwind CSS v4 + shadcn/ui (Radix primitives) + lucide icons | ADR 0002 |
| Charts | Recharts | every chart has a table twin |
| PDF viewer | PDF.js (`pdfjs-dist`) with an overlay layer for bbox highlights | Apache-2.0 |
| API client | generated from FastAPI's OpenAPI (`openapi-typescript`) | regenerated in the same PR as an API change |
| Quality | Ruff + pytest + Hypothesis (backend); Biome + Vitest + Playwright (frontend) | run by `scripts/local-gate.sh` |
| Packaging | `uv` (Python), `pnpm` (JS); Docker Compose for a one-command demo | SC-1.3 |

Layout: `backend/` (package `pce`: `domain`, `db`, `intake`, `extraction`, `instruments`, `finance`,
`scenarios`, `validation`, `api`), `frontend/`, `data/` (`taxonomy/`, `synthetic/`), `docs/`, `backlog/`, `slides/`.

## Consequences

- One language for extraction and calculation keeps provenance objects in one type system (Pydantic) from
  parser to ledger to API.
- The SPA is static files served by FastAPI or any web server, so the pilot is one process on one machine.
- Two toolchains (uv, pnpm) to install; `scripts/bootstrap.sh` handles it.

## Alternatives rejected

- **Next.js** (proposed first in this thread): server rendering and routing conventions bring a second
  server runtime for no user benefit in a local, authenticated analyst tool. Revisit if a public client
  portal is built (backlog R32).
- **All-TypeScript backend** (like FoodAppTracker): PDF table and OCR libraries in Node are much weaker,
  and JS has no native decimal.
- **LangGraph/agent framework at the core**: the core pipeline is deterministic. Agents are allowed only
  for bounded, reviewable steps (unknown document interpretation, public document lookup), added by ADR if needed.
