# FeeLens security

Scope: the single-container deployment (`Dockerfile`, `render.yaml`), the pilot kit (`deployment/local/`,
[PILOT_INSTALL.md](PILOT_INSTALL.md)) and local development. Stories SC-9.4, SC-11.6, SC-11.7, SC-11.8, SC-11.11.
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

| `PCE_ADMIN_TOTP_SECRET` | Authenticator secret for the env admin (`python -m pce.users new-totp-secret`). Without it, with `PCE_REQUIRE_MFA=1`, the env admin cannot finish setup. |
| `PCE_REQUIRE_MFA` | `1` (pilot kit): every account must link an authenticator app before it reaches anything but account setup. |

- **Named accounts (SC-11.7)** live in the database (`user_account`): one per person, roles, admin flag,
  scrypt password hash, TOTP secret, `session_version`. Created by an admin (Users page or
  `python -m pce.users create`) with a one-time password; the first sign-in forces a new password and, with
  `PCE_REQUIRE_MFA=1`, an authenticator (RFC 6238, 30 s, ±1 step, a code is accepted once). Admins manage
  only their own firm's accounts and cannot reset or disable themselves.
- The env admin is break-glass only (and the Render demo's login, whose free disk is ephemeral). Leave it
  empty in the pilot once two personal admins exist. No admin configured and no stored account means
  nobody can sign in (fail closed).
- **Audit (SC-11.8)**: sign-ins, failed codes, prospect opened, document viewed, every write, exports and
  deletions, with ids only. `audit_event` rows cannot be updated (SQLite trigger).
- **Erasure (SC-11.11)**: `DELETE /api/prospects/{id}`, admins only, typed prospect code, reason from a
  fixed list; leaves one `prospect.erased` entry with counts. Retention (SC-11.6): `python -m pce.retention`.
- Sessions are stateless: an HMAC-SHA256-signed cookie with username, expiry (12 h) and a fingerprint of
  the password hash, TOTP secret and `session_version` (bumped by reset, disable and "sign out everywhere"). `HttpOnly`, `SameSite=Strict`, `Path=/`. They survive restarts and the free plan's sleep.
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

- Single sign-on (OIDC) and Postgres: SC-11.2.
- Sessions are revoked per account (`session_version`), not per device.
- `--forwarded-allow-ips '*'` trusts `X-Forwarded-For`; a client can spoof its address to dodge the
  per-client limit, which is why the per-username limit exists.
