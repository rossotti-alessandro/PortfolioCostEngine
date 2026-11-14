# Sources of truth

One canonical place per topic. When another document, branch or old code disagrees, the file here wins;
fix or delete the other one in the same PR.

| Topic | Canonical source | Owner (story / thread) |
|---|---|---|
| Agent protocol, PM loop, claims, merge rules, rule-9 approvals | [AGENTS.md](../AGENTS.md) | SC-1.1, SC-1.7 |
| Product rules from Ale, coding standards, invariants | [CLAUDE.md](../CLAUDE.md), `.claude/rules/*.md` | SC-1.1, SC-1.7 |
| Current situation, open PRs, drift, next tasks | [HANDOFF.md](../HANDOFF.md) | every PR that changes them |
| Fee evidence statuses (measurements) | `Measurement` in `backend/src/pce/finance/ledger.py`, mirrored in `.claude/rules/finance.md` | rule 9 |
| Accuracy protocol, gates and baselines | [docs/EVALUATION_PROTOCOL.md](EVALUATION_PROTOCOL.md) | SC-9.1 |
| Commands and change loop | [docs/WORKFLOW.md](WORKFLOW.md) | SC-1.1 |
| Architecture and technology decisions | [docs/adr/](adr/README.md) | coordinator |
| Backlog: epics, stories, owners, progress | `backlog/tasks/*.md` (board is generated: `backlog/BOARD.md`) | coordinator |
| Fee categories and cost methodology | `docs/research/FEE_TAXONOMY.md`, `data/taxonomy/fee_taxonomy.csv` | research (SC-2) |
| Document types and what each contains | `docs/research/DOCUMENT_TAXONOMY.md`, `data/taxonomy/document_types.csv` | research (SC-2) |
| Public sources, licences, fetch status | `docs/research/SOURCE_REGISTER.md` | research (SC-2) |
| Go-live gates, pilot, analyst review and incident protocols | [docs/READINESS.md](READINESS.md) | SC-11.10 |
| Privacy and hosting options | `docs/research/DATA_PRIVACY_AND_HOSTING.md` + [ADR 0004](adr/0004-privacy-local-first.md) | research + coordinator |
| What was wrong in the ChatGPT handoff | `docs/CRITICAL_REVIEW.md` | research (SC-2) |
| Extraction engines and versions | [ADR 0003](adr/0003-document-extraction-and-ocr.md), `backend/pyproject.toml`, `backend/uv.lock` | SC-1.2 |
| Design tokens and components | [docs/design/DESIGN_SYSTEM.md](design/DESIGN_SYSTEM.md) | SC-8.1 |
| UX flow and screens | `docs/research/UX_RECOMMENDATIONS.md`, then `docs/app/` once the app exists | demo (SC-8) |
| Decks: generators, figures, claims | `slides/source/*.js`, [slides/README.md](../slides/README.md), `.claude/rules/deck.md` | deck (SC-10) |

The ChatGPT handoff kit (`SafeCapital_ClaudeCode_Kit`, uploaded 2026-11-06) is **input, not truth**. Its
useful parts were re-verified into the files above; its own backlog is superseded by `backlog/tasks/`.
