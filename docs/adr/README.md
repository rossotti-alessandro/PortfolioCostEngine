# Architecture decision records

One file per decision: context, decision, consequences, alternatives rejected. A decision changes only
through a new ADR that supersedes the old one (mark the old one "Superseded by 00NN").

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-stack.md) | Stack: FastAPI + Python backend, Vite + React SPA frontend, SQLite → PostgreSQL | Accepted 2026-11-06 |
| [0002](0002-design-system.md) | Design system: Tailwind v4 tokens + shadcn/ui, sober private-bank look, evidence-first components | Accepted 2026-11-06 |
| [0003](0003-document-extraction-and-ocr.md) | Extraction: pdfplumber + pypdfium2 + Docling + OCRmyPDF/Tesseract; no PyMuPDF | Accepted 2026-11-06 |
| [0004](0004-privacy-local-first.md) | Local-first; no client content to external AI by default | Accepted 2026-11-06 |
| [0005](0005-multi-agent-protocol.md) | Multi-agent delivery: backlog as markdown stories, branch-based atomic claims | Accepted 2026-11-06 |
