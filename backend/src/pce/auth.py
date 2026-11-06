"""Accounts, password hashing, signed session cookies, CSRF tokens and login throttling.

Why this shape (docs/app/SECURITY.md):
- Accounts come from the environment, not the database: the Render free plan has an ephemeral disk,
  so an account stored in SQLite would vanish on every restart. The admin is seeded from
  ``PCE_ADMIN_USERNAME`` plus ``PCE_ADMIN_PASSWORD`` (hashed in memory at start) or
  ``PCE_ADMIN_PASSWORD_HASH`` (made with ``python -m pce.auth hash``).
- Sessions are stateless HMAC-signed cookies, so they survive restarts and the free plan's sleep
  as long as ``PCE_SECRET_KEY`` is stable. Rotating the key or the password signs everyone out.
- Passwords use stdlib scrypt: no new dependency, memory-hard, constant-time comparison.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field

log = logging.getLogger("pce.auth")

ROLES = ("analyst", "senior", "relationship_manager")
SESSION_TTL_S = 12 * 3600
MIN_PASSWORD_LEN = 12
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**15, 8, 1


# ------------------------------------------------------------------ passwords
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(
        password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, maxmem=64 * 1024 * 1024
    )
    b64 = base64.b64encode
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${b64(salt).decode()}${b64(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, dk = stored.split("$")
        if algo != "scrypt":
            return False
        want = base64.b64decode(dk)
        got = hashlib.scrypt(
            password.encode(),
            salt=base64.b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            maxmem=64 * 1024 * 1024,
            dklen=len(want),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(got, want)


# A real hash to burn the same time on unknown usernames (no user enumeration by timing).
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


# ------------------------------------------------------------------ accounts
@dataclass(frozen=True)
class Account:
    username: str
    password_hash: str
    tenant: str
    roles: tuple[str, ...]
    admin: bool = False


_accounts: dict[str, Account] = {}


def add_account(
    username: str, password: str, tenant: str, roles: tuple[str, ...] = ROLES, admin: bool = False
) -> Account:
    """Register an account in memory (env seeding and tests). Enforces a minimum password length."""
    if len(password) < MIN_PASSWORD_LEN:
        raise ValueError(f"password must be at least {MIN_PASSWORD_LEN} characters")
    return _register(username, hash_password(password), tenant, roles, admin)


def _register(username: str, pw_hash: str, tenant: str, roles: tuple[str, ...], admin: bool) -> Account:
    if not set(roles) <= set(ROLES) or not roles:
        raise ValueError("unknown role")
    acc = Account(username.strip().lower(), pw_hash, tenant, tuple(roles), admin)
    _accounts[acc.username] = acc
    return acc


def get_account(username: str) -> Account | None:
    return _accounts.get(username.strip().lower())


def load_env_accounts() -> None:
    """Seed the admin from the environment. Fails closed: no admin configured means nobody can log in."""
    user = os.environ.get("PCE_ADMIN_USERNAME", "").strip()
    pw = os.environ.get("PCE_ADMIN_PASSWORD", "")
    pw_hash = os.environ.get("PCE_ADMIN_PASSWORD_HASH", "").strip()
    tenant = os.environ.get("PCE_ADMIN_TENANT", "demo-firm")
    if not user or not (pw or pw_hash):
        log.warning("auth: no admin account configured (PCE_ADMIN_USERNAME/PASSWORD); login is disabled")
        return
    if pw_hash:
        _register(user, pw_hash, tenant, ROLES, admin=True)
    else:
        try:
            add_account(user, pw, tenant, ROLES, admin=True)
        except ValueError as exc:
            log.error("auth: admin account not created: %s", exc)
            return
    log.info("auth: admin account loaded")  # never log the username's password or hash


# ------------------------------------------------------------------ sessions
def _load_secret() -> bytes:
    key = os.environ.get("PCE_SECRET_KEY", "")
    if key:
        if len(key) < 32:
            raise RuntimeError("PCE_SECRET_KEY must be at least 32 characters")
        return key.encode()
    log.warning("auth: PCE_SECRET_KEY not set; using a random key, sessions end on restart")
    return secrets.token_bytes(32)


_SECRET = _load_secret()


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign(msg: bytes) -> bytes:
    return hmac.new(_SECRET, msg, hashlib.sha256).digest()


def _pw_version(acc: Account) -> str:
    # Changing the password invalidates every session issued before the change.
    return _b64(_sign(b"pv:" + acc.password_hash.encode()))[:16]


def issue_session(acc: Account, now: float | None = None) -> str:
    now = time.time() if now is None else now
    body = json.dumps(
        {
            "u": acc.username,
            "iat": int(now),
            "exp": int(now) + SESSION_TTL_S,
            "pv": _pw_version(acc),
            "n": secrets.token_urlsafe(8),  # unique per sign-in, so is its CSRF token
        },
        separators=(",", ":"),
    ).encode()
    return f"{_b64(body)}.{_b64(_sign(b'session:' + body))}"


def read_session(token: str | None, now: float | None = None) -> Account | None:
    if not token or token.count(".") != 1:
        return None
    body_b64, sig_b64 = token.split(".")
    try:
        body = _unb64(body_b64)
        sig = _unb64(sig_b64)
        if not hmac.compare_digest(sig, _sign(b"session:" + body)):
            return None
        data = json.loads(body)
    except (ValueError, TypeError):
        return None
    now = time.time() if now is None else now
    acc = get_account(str(data.get("u", "")))
    if not acc or int(data.get("exp", 0)) <= now or data.get("pv") != _pw_version(acc):
        return None
    return acc


def csrf_token(session_token: str) -> str:
    """CSRF token bound to the session: a stolen token is useless with another session."""
    return _b64(_sign(b"csrf:" + session_token.encode()))


def check_csrf(session_token: str, sent: str | None) -> bool:
    return bool(sent) and hmac.compare_digest(csrf_token(session_token), sent or "")


# ------------------------------------------------------------------ throttling
@dataclass
class Throttle:
    """Counts failed logins per key in a sliding window. In memory: a restart resets it."""

    limit: int
    window_s: float
    _hits: dict[str, deque[float]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _recent(self, key: str, now: float) -> deque[float]:
        q = self._hits.setdefault(key, deque())
        while q and q[0] <= now - self.window_s:
            q.popleft()
        return q

    def blocked(self, key: str, now: float | None = None) -> float:
        """Seconds until the key may try again, 0 when allowed."""
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._recent(key, now)
            return max(0.0, q[0] + self.window_s - now) if len(q) >= self.limit else 0.0

    def fail(self, key: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        with self._lock:
            self._recent(key, now).append(now)
            if len(self._hits) > 10_000:  # bound memory under a spray of distinct keys
                self._hits = {k: v for k, v in self._hits.items() if v}

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)


# Per client: 5 failures per 15 minutes. Per username: 20, a backstop when clients rotate addresses.
PER_CLIENT = Throttle(limit=5, window_s=15 * 60)
PER_USER = Throttle(limit=20, window_s=15 * 60)


def authenticate(username: str, password: str) -> Account | None:
    acc = get_account(username)
    ok = verify_password(password, acc.password_hash if acc else _DUMMY_HASH)
    return acc if acc and ok else None


load_env_accounts()


if __name__ == "__main__":  # python -m pce.auth hash   -> prompts, prints a hash for PCE_ADMIN_PASSWORD_HASH
    import getpass

    if sys.argv[1:] != ["hash"]:
        sys.exit("usage: python -m pce.auth hash")
    pw = getpass.getpass("Password: ")
    if len(pw) < MIN_PASSWORD_LEN or pw != getpass.getpass("Repeat: "):
        sys.exit(f"passwords differ or shorter than {MIN_PASSWORD_LEN} characters")
    print(hash_password(pw))
