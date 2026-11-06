# FeeLens security (hosted demo)

Scope: the single-container deployment (`Dockerfile`, `render.yaml`) and local development. Story SC-9.4.
Privacy policy for client content is ADR 0004 and `.claude/rules/privacy.md`; this page covers access and
the web surface. Engineering notes, not a certification.

## Accounts and sign-in

| Setting | Meaning |
|---|---|
| `PCE_ADMIN_USERNAME` | Admin username (case-insensitive). Holds every role, tenant `PCE_ADMIN_TENANT` (default `demo-firm`). |
| `PCE_ADMIN_PASSWORD` | Admin password, 12+ characters. Hashed with scrypt in memory at start, never stored or logged. |
| `PCE_ADMIN_PASSWORD_HASH` | Alternative to the plain password: output of `cd backend && uv run python -m pce.auth hash`. Wins if both are set. |
| `PCE_SECRET_KEY` | 32+ random characters. Signs session cookies and CSRF tokens. Must stay the same across restarts. |
| `PCE_COOKIE_SECURE` | `1` (default): `__Host-` cookie, `Secure`, HSTS. `0` only for plain-HTTP local development and tests. |

- Accounts live in the environment, not the database, because the Render free plan has an ephemeral disk.
  No admin configured means nobody can sign in (fail closed).
- Sessions are stateless: an HMAC-SHA256-signed cookie with username, expiry (12 h) and a fingerprint of
  the password hash. `HttpOnly`, `SameSite=Strict`, `Path=/`. They survive restarts and the free plan's sleep.
- Sign everyone out: change `PCE_SECRET_KEY`. Changing the password also ends that account's sessions.
- Tenant and user come from the session only. `X-Role` picks among the roles the account holds (the demo
  role switch); a role the account lacks returns 403. `X-Tenant-Id` and `X-User` are ignored.

### On Render

`render.yaml` declares `PCE_ADMIN_USERNAME=ale` and generated `PCE_SECRET_KEY` / `PCE_ADMIN_PASSWORD`,
but generation only happens for Blueprint-synced services. `feelens-demo` was created through the API, so
set the two secrets by hand: Render dashboard → `feelens-demo` → Environment → add `PCE_SECRET_KEY`
(32+ random characters) and `PCE_ADMIN_PASSWORD` (12+ characters), save, redeploy. Change the password the
same way. Never paste it in chat, git, issues or screenshots.

## Request pipeline (`pce/security.py`)

1. Body larger than `PCE_MAX_REQUEST_MB` (100) → 413 before parsing.
2. `/api/*`, `/docs`, `/openapi.json`: writes from a foreign `Origin`/`Referer` → 403.
3. Everything except `/api/health` and `/api/auth/*` needs a valid session → 401.
4. Writes (POST, PUT, PATCH, DELETE) need `X-CSRF-Token` matching the session → 403. The token comes from
   `/api/auth/login` or `/api/auth/me` and is held in page memory only.
5. Every response: CSP (`script-src 'self'`, `frame-ancestors 'none'`, `object-src 'none'`), HSTS,
   `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, COOP/CORP same-origin,
   `Permissions-Policy`; `/api/*` also `Cache-Control: no-store`.

Login throttling: 5 failures per client address per 15 minutes, 20 per username (backstop when an attacker
rotates addresses), then 429 with `Retry-After`. Unknown usernames take the same time as wrong passwords.
Counters are in memory and reset on restart.

## Uploads

PDF and XLSX only; at most 20 files and 25 MB each per request. The extension, the leading bytes and
libmagic must agree. XLSX: uncompressed size cap (zip bombs) and no macros. File names are reduced to a
clean base name. Stored by SHA-256, served back with `nosniff` and `no-store`. Client documents never
leave the server (ADR 0004).

## Dependency audit (2026-11-06)

- Python (`pip-audit`, runtime lock): no known vulnerabilities.
- Frontend runtime (`pnpm audit --prod`): 2 moderate in `react-router` 6 (SSR hydration, not used here;
  backslash open redirect in `<Link>`, only static paths used here). Fix needs React Router 7.
- Frontend dev only (`vitest` 2, `vite` pulled in by vitest): critical and high advisories in the test runner,
  not shipped in the image. Fix: a dedicated `deps:` PR bumping vitest.

## Known limits

- One admin account. More users or SSO: SC-11.2.
- Stateless sessions cannot be revoked one by one (rotate the key instead).
- `--forwarded-allow-ips '*'` trusts `X-Forwarded-For`; a client can spoof its address to dodge the
  per-client limit, which is why the per-username limit exists.
