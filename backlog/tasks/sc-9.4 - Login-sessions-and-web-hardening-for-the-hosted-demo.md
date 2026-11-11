---
id: SC-9.4
title: Login, sessions and web hardening for the hosted demo
status: Done
assignee: []
owner: "Secure FeeLens with login and hardening"
model: "claude"
progress: 100
branch: "claude/project-thread-9vg77k"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/9"
created_date: "2026-11-06 17:40"
updated_date: "2026-11-06 17:48"
labels:
  - security
dependencies: []
parent_task_id: SC-9
priority: P0
paths_owned:
  - "backend/src/pce/auth.py"
  - "backend/src/pce/security.py"
  - "backend/src/pce/api.py"
  - "backend/src/pce/serve.py"
  - "backend/src/pce/crm/router.py"
  - "backend/tests/**"
  - "frontend/src/lib/api.ts"
  - "frontend/src/pages/crm/api.ts"
  - "frontend/src/pages/Login.tsx"
  - "frontend/src/main.tsx"
  - "frontend/src/components/Shell.tsx"
  - "frontend/src/lib/it.ts"
  - "frontend/tests/e2e/**"
  - "Dockerfile"
  - "render.yaml"
  - ".env.example"
  - "docs/app/SECURITY.md"
spec_ref: docs/adr/0004-privacy-local-first.md
rule_refs:
  - ".claude/rules/privacy.md"
---

> **One-liner**: The public Render demo is open to anyone with the URL; put it behind a real login and harden the web surface.

## Description

### Context

`pce.api.ctx` trusts `X-Tenant-Id`, `X-User` and `X-Role` headers sent by the browser, so anyone who
finds https://feelens-demo.onrender.com can read and change everything and pick the senior role. No
security headers, no CSP, OpenAPI docs are public.

### User Flow Impact

A sign-in page before the app. Sign out in the header. The demo role switch stays, limited to the
roles the signed-in account may use.

### Performance / Efficiency Impact

One scrypt hash per login attempt (about 50 ms). No measurable impact elsewhere.

### Proposed Approach

1. `pce/auth.py`: env-seeded accounts (Render free disk is ephemeral), scrypt hashes, HMAC-signed
   stateless session cookie, CSRF token bound to the session, login throttling.
2. `pce/security.py`: auth gate for `/api/*`, Origin check, security headers and CSP, request size cap.
3. `ctx` derives tenant, user and role from the session, never from client headers.
4. Upload: file count, filename sanitising, libmagic sniff. Report filename sanitised.
5. Frontend: login page, CSRF header, sign-out. Render blueprint: generated secret key and password.

### Risks & Follow-ups

Stateless sessions cannot be revoked one by one: rotating `PCE_SECRET_KEY` or the password signs
everyone out. Multi-user accounts and SSO belong to SC-11.2.

## Acceptance Criteria

- [x] #1 Every `/api/*` route except health and login returns 401 without a valid session (tested)
- [x] #2 Mutations without the CSRF token or from a foreign Origin return 403 (tested)
- [x] #3 The sixth wrong password in a row from one client returns 429 (tested)
- [x] #4 Client headers cannot change tenant or user, nor raise the role above the account's (tested)
- [x] #5 Responses carry CSP, HSTS, nosniff, frame-ancestors none; the built UI loads with no CSP violation
- [x] #6 Regression: the existing API, CRM and E2E suites pass signed in

## Implementation Notes

Owned paths as listed, plus `.env.example`, `frontend/playwright.config.ts` and
`frontend/tests/e2e/global-setup.ts`. No new dependency: scrypt and HMAC are stdlib, libmagic was
already a dependency. Security design and operator steps: `docs/app/SECURITY.md`.

## Outcome

- **Status**: completed

Backend suite green (new `tests/test_security.py`: 12 tests), Playwright E2E 15/15 signed in,
built UI exercised through sign-in, review (PDF.js), costs and compare with zero CSP violations.
pip-audit clean; frontend audit findings recorded in SECURITY.md for a separate `deps:` PR.

## Issues Encountered

- The sign-in page rendered `<Link>` outside the router and crashed; E2E missed it because tests start
  signed in. Fixed (`Brand link={false}`) and checked in a real browser.
- Two sign-ins in the same second produced the same token; a random nonce now makes each unique.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-9vg77k | dd58310 | 2026-11-06 | backend: login, sessions, CSRF, throttling, headers, upload guards |
| claude/project-thread-9vg77k | 6568889 | 2026-11-06 | frontend sign-in, Render secrets, SECURITY.md |
