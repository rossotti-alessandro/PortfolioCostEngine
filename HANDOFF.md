# FeeLens / PortfolioCostEngine: handoff and status

> **Read this first if you are a new agent, environment or person.** Last updated 2026-11-14.
> Every PR through #53 is on `main` except the open ones listed in section 5 (the protocol, the app, the
> corpus, the OCR benchmark, sign-in, accuracy protocol, readiness gates, the UI redesign so far).
> The protocol lives in [CLAUDE.md](CLAUDE.md) and [AGENTS.md](AGENTS.md); the backlog in
> [backlog/BOARD.md](backlog/BOARD.md). This file holds what those do not: the current situation, known
> drift and the next tasks. Keep it short and current; update it in the same PR as any change it describes.

## 1. Product and people

**FeeLens** (name chosen by Ale on 2026-11-06; repo name stays PortfolioCostEngine; trademark not checked).
An analyst uploads a prospect's bank statements, cost reports, price lists and KIDs; FeeLens extracts
positions and every cost with page + bounding-box evidence, lets the analyst review it, flags what is
missing, and compares the all-in annual cost with an alternative proposal on the same holdings.

- First user: **Safe Capital Management SA, Lugano** (contact: Massimo, who also works for another family
  office). Generic by design.
- Owner and decision maker: **Ale** (GitHub `rossotti-alessandro`). Rule 9 exceptions in `AGENTS.md` need
  Ale's explicit approval per PR.
- The ChatGPT-made kit Ale supplied is input, not truth: `docs/CRITICAL_REVIEW.md`, `docs/app/CRITICAL_REVIEW.md`.

Ale's standing rules (product rules: `CLAUDE.md` § Product rules; protocol: `AGENTS.md`):

- In Ale's words "Ponytails/Cademan" means the `ponytail` and `caveman` skills (`.agents/skills/`).
- Never scrape swissfunddata.ch; UBS, Credit Suisse and BancaStato block bots: do not work around it.
- **Secrets never go in git or chat.** The demo password and session key live only in the Render dashboard.

## 2. What exists on `main`

- **App:** `backend/src/pce` (FastAPI: extraction with bbox, review, reconciliation, cost ledger, tariffs,
  scenarios, report, CRM, sign-in) and `frontend/` (React, EN/IT). `docker compose up --build`, then
  http://localhost:8000 and "Load synthetic demo". Docs: `docs/app/SECURITY.md`, `docs/app/CRITICAL_REVIEW.md`.
- **Synthetic prospects:** P-1042 (CH, AUM CHF 4.3m) and P-2077 (IT bank in EUR + US broker in USD; proposal
  honestly not cheaper). P-1042 numbers are pinned in `backend/tests/test_pipeline.py` and quoted in the
  decks: current known cost CHF 61,449.60 (142.9 bps, incomplete); comparable 60,839.60; proposal same
  holdings 54,319.50; saving at least 6,520.10; payback 2.8 months. Change the spec, update the decks.
- **Specimen corpus:** `data/reference/specimen_corpus.csv`, 399 public PDFs from 289 institutions; PDFs are
  never committed (`data/specimens/tools/fetch.py` downloads them to `var/specimens/`). Results:
  `data/specimens/RESULTS.md`, `COVERAGE.md`; guide `docs/research/CLIENT_DOCUMENTS.md`.
- **OCR benchmark:** `data/specimens/ocrbench/` (README, `SCORES.md`). On the same 23 pages: hybrid +
  PaddleOCR-VL 69% label+value rows (53 s/page), Docling 63%, cheap hybrid route 62% (1.1 s/page),
  pdfplumber 57%. Values are read almost perfectly; the gap is label association. CPU only; run VLMs one at a time.
- **Research:** `docs/research/*` and `data/taxonomy/*.csv`. **Decks:** `slides/`, built by
  `slides/source/build_deck.js` (`DECK_LANG=it|en`) and `build_workflow_deck.js`. Never edit PPTX by hand.

### Running the gate in a fresh cloud container

`./scripts/local-gate.sh` needs the OCR system packages. A fresh container lacks them, and 24 backend tests
then fail with `FileNotFoundError: 'tesseract'`. Run `./scripts/bootstrap.sh` first (or
`apt-get install tesseract-ocr tesseract-ocr-{eng,ita,deu,fra} ocrmypdf ghostscript qpdf poppler-utils unpaper pngquant libmagic1`).
CI (`.github/workflows/ci.yml`) installs them itself.

## 3. Live demo

- **https://feelens-demo.onrender.com** (Render service `feelens-demo`, id `srv-dbn0na3m8hqs73bkailg`,
  Frankfurt, Free plan, Docker). Created via the API, **not Blueprint-synced**: env changes in `render.yaml`
  must be set by hand in the dashboard. Auto-deploy did not fire on push; trigger deploys by API or dashboard.
- Env: `PCE_AUTOSEED=1`, `PCE_ALLOW_EXTERNAL_AI=false`, `PCE_ADMIN_USERNAME=ale`. Sign-in also needs
  `PCE_SECRET_KEY` and `PCE_ADMIN_PASSWORD`, which **Ale sets himself** in Render → feelens-demo → Environment.
- Free plan: sleeps after 15 minutes idle; SQLite on an ephemeral disk, so uploads vanish on restart. Real
  client data needs Postgres or a persistent disk, and compliance sign-off (SC-11.1).
- Deployment state is in section 5 (it changes; check it before relying on it).

## 4. Backlog: known drift

- The demo app was built before story claims existed. Stories SC-1.3, 3.x, 4.x, 5.1, 5.2, 5.4, 6.1,
  7.1 to 7.5, 8.1 to 8.7, 9.1 to 9.3 and 10.2 still say To Do although `main` covers part of each.
  **Before claiming any of them, read the existing code and tests first**, then record what is already
  done in the story (evidence: test names) and scope the story to the real gap. SC-3.1 and SC-8.1 show as
  "ready to claim" on the board for this reason only.
- SC-2.3 stays In Progress: the corpus is in, but per-specimen page maps (AC #2) are not.
- Claim branches `claims/sc-5.6` and `claims/sc-9.4` are released (both stories Done). `claims/sc-2.3` stays claimed while SC-2.3 is In Progress.
  `claims/sc-0.0` (protocol race test) and the merged `claude/project-thread-*` branches can be deleted by
  Ale; cloud sessions cannot delete refs.

## 5. Current situation and next tasks

State on 2026-11-14:

- Open PRs: #40 (SC-7.6 firm tariff), #44 (15 specimens from a client-file gap audit), #48 (accounts with
  MFA, erasure, audit, pilot kit; claims SC-11.6 to 11.11). Check `node scripts/claims-status.mjs` and the
  PR list before touching their paths.
- Readiness verdict (`docs/READINESS.md`): not ready for real client data; close to a supervised pilot.
- Render still deploys branch `claude/project-thread-steqtm` at `fa2b77b`, which has **no sign-in**. To
  switch: Ale sets `PCE_SECRET_KEY` and `PCE_ADMIN_PASSWORD` in the dashboard, the service branch is changed
  to `main`, and a deploy is triggered. Then check that `/` asks for a login.
- Board drift: SC-9.6 was delivered by PR #34 but its story still says To Do, so the board offers it as
  ready. Read the story and the PR before claiming it.

Next tasks, in priority order:

1. **Deploy sign-in** (above).
2. **Reconcile the demo-covered stories** (section 4), story by story (SC-1.5).
3. **Extraction accuracy:** current numbers and the remaining miss causes are in `docs/READINESS.md` §3 and
   `docs/EVALUATION_PROTOCOL.md`; every change follows the accuracy rule in `.claude/rules/extraction.md`.
4. Dependencies PR: vitest 2 (critical dev-only advisories) and React Router 7 (2 moderate).
5. Postgres and multi-user/SSO (SC-11.2) before any real client data; real-data pilot with compliance
   sign-off (SC-11.1).
6. FinSA request letter: in CH, cost and retrocession disclosure is largely on request, so the tool should
   generate a letter to the bank asking for costs and retrocessions.
7. Protocol tooling (SC-1.4): board "ready" list that skips claimed stories, board refresh in CI.

Open questions for Ale or Massimo:

- Safe Capital's FINMA authorisation and supervisory organisation: unconfirmed; check the FINMA register first.
- Brand: the kit sometimes says "3MC"; confirm with Massimo. Trademark check for "FeeLens".
- The UBS price list must be downloaded by hand.
- Raiffeisen Locarno URLs pass robots.txt by the letter, not by intent: keep them in the corpus or not?

## 6. Where things live outside Git

- Shared Claude project folder `/mnt/project-files/`: deck PDFs/PPTX, screenshots, corpus report, OCR model
  list (copies; the sources are in the repo).
- Claude artifacts (private to Ale): live deck, deck explorer, specimen report, OCR lab. Links are in the
  Claude project memory.
- Render dashboard: environment secrets.
