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

- Two kinds of account (SC-11.12):
  - **Break-glass admin** from the environment. Holds every role, never stored in the database, so a lost
    or reset database never locks the firm out. Its password is changed in the environment only.
  - **Named people** in the `user_account` table, added by an admin on **Team & access** (`/admin`). They get
    a one-time password, shown once, and must choose their own (12+ characters) before anything else works.
    On the Render free plan the disk is ephemeral: named people vanish on restart (pilot: persistent disk).
- No admin configured and no named people means nobody can sign in (fail closed).
- Sessions are server-side (`auth_session`). The cookie is HMAC-SHA256-signed and carries the session id,
  username, 12 h expiry and a fingerprint of the password hash. `HttpOnly`, `SameSite=Strict`, `Path=/`.
  A session ends on sign-out (also for a copied cookie), after `PCE_IDLE_TIMEOUT_MIN` (30) minutes without
  activity, when an admin signs the person out everywhere, changes their roles or deactivates them, and when
  the password changes. Rotating `PCE_SECRET_KEY` still signs everyone out.
- Tenant and user come from the session only. `X-Role` picks the role a request acts in, among the roles
  the account holds; a role the account lacks returns 403. `X-Tenant-Id` and `X-User` are ignored.

### Roles and permissions (`pce/permissions.py`)

| Permission | analyst | senior | relationship_manager | viewer | admin |
|---|---|---|---|---|---|
| Read prospects, documents, costs, CRM (`data.read`) | ✓ | ✓ | ✓ | ✓ | |
| Change anything (`data.write`) | ✓ | ✓ | ✓ | | |
| Internal economics (`internal.read`) | | ✓ | ✓ | | |
| Approve a client report (`report.approve`) | | ✓ | | | |
| People and sessions (`users.manage`) | | | | | ✓ |
| Firm activity log (`audit.read`) | | ✓ | | ✓ | ✓ |

The middleware checks this table on every `/api/*` request (path and method decide the permission), on top
of the route checks. Admin alone sees no client data (least privilege). Four-eyes: the person who uploaded
a document or corrected a value of a review cannot approve it (`PCE_FOUR_EYES=0` turns this off for a
one-person demo only).

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

PDF, XLSX and JPEG/PNG photos (a phone scan becomes one PDF, SC-8.28; photos are not kept); at most 20 files and 25 MB each per request. The extension, the leading bytes and
libmagic must agree. XLSX: uncompressed size cap (zip bombs) and no macros. File names are reduced to a
clean base name. Stored by SHA-256, served back with `nosniff` and `no-store`. Client documents never
leave the server (ADR 0004).

## Dependency audit (2026-11-06)

- Python (`pip-audit`, runtime lock): no known vulnerabilities.
- Frontend runtime (`pnpm audit --prod`): 2 moderate in `react-router` 6 (SSR hydration, not used here;
  backslash open redirect in `<Link>`, only static paths used here). Fix needs React Router 7.
- Frontend dev only (`vitest` 2, `vite` pulled in by vitest): critical and high advisories in the test runner,
  not shipped in the image. Fix: a dedicated `deps:` PR bumping vitest.

### Erasure and retention (`pce/erasure.py`, `pce/retention.py`, SC-11.11)

A senior (`data.erase`) erases a cost review from the Cost reviews list: fixed reason, the review's code
typed to confirm. It deletes the prospect, its documents and stored files (a file shared with another
review of the firm stays), facts, reviews, proposals, approvals, document requests and the review's
activity-log entries; the linked CRM contact is deleted with its notes and stages, or only unlinked. One
`prospect.erased` entry stays, with the reason, counts and the ids of the removed log entries, so the
tamper check counts those gaps as made by the application. `python -m pce.retention --days 90 [--dry-run]`
erases reviews with no activity for that long, except those whose contact reached "won". Backups keep the
data until they expire.

### Two-step sign-in (TOTP, SC-11.7)

A named person turns it on from the account menu ("Turn on two-step sign-in"): the server proposes a key
(bound to the person by an HMAC proof), and stores it in `user_mfa` only after a valid code. From then on
sign-in needs password and code (RFC 6238, SHA-1, 30 s, one step of clock drift, each code accepted once).
A missing or wrong code counts as a failed sign-in for the throttle, so "code required" does not confirm a
password for free. `PCE_REQUIRE_MFA=1` (pilot and production) keeps an account without a key on the setup
page. The env admin's key is `PCE_ADMIN_TOTP_SECRET` (`python -c "import pce.auth as a;
print(a.new_totp_secret())"`). An admin's password reset also removes the person's key (lost phone).
Turning it on ends the person's other sessions. Logged: `auth.mfa_enabled`, `auth.mfa_failed`.

### Activity log (`pce/audit.py`, SC-11.8)

Every `audit_event` row gets an HMAC seal in `audit_seal`, written by a mapper hook in the same
transaction, so no writer can skip it. Logged: sign-in, failed sign-in (known usernames only), sign-out,
password change, opening a document or a spreadsheet, downloading a client report, approvals, value
checks, admin actions, CRM changes, and reading the log itself. Rows hold ids and actions, never document
text. `GET /api/audit` (page "Activity log") returns the firm's events and a tamper check: an edited row,
a row inserted by hand (no seal) or a deleted row (a gap in the ids) is reported. Key: `PCE_AUDIT_KEY`,
else `PCE_SECRET_KEY`; without a stable key, seals written before a restart are counted as "other key",
not as tampering. Rows written before sealing began are "unsealed history". Limits: someone with write
access to the database and the key can forge seals; deleting the newest rows together with their seals leaves no gap. A copy to
write-once storage (backups) closes both.

## Known limits

- No single sign-on (Microsoft 365) yet: accounts are local, with optional or required TOTP.
- No QR code on the setup page: on a phone the "add FeeLens to the app" link opens the authenticator; on a
  computer the key is typed in.
- The viewer role is enforced by the server; the interface still shows some buttons that then answer 403.
- `--forwarded-allow-ips '*'` trusts `X-Forwarded-For`; a client can spoof its address to dodge the
  per-client limit, which is why the per-username limit exists.
