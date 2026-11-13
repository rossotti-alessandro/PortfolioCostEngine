"""Personal accounts in the database: create, list, reset, disable, sign out everywhere (SC-11.7).

One account per person, so the audit log says who did what. An admin creates an account with a one-time
password; at first sign-in the person chooses their own password and, with ``PCE_REQUIRE_MFA=1``, links an
authenticator app (``pce.security`` account setup). Admins only manage accounts of their own firm (tenant).

Command line, for the first admin and for machines without a browser session:

    python -m pce.users create <username> --tenant <firm> --role analyst --role senior [--admin]
    python -m pce.users list --tenant <firm>
    python -m pce.users reset <username>       # new one-time password, second factor cleared
    python -m pce.users disable <username>     # also ends every session
    python -m pce.users enable <username>
    python -m pce.users new-totp-secret        # for PCE_ADMIN_TOTP_SECRET on the break-glass admin

One-time passwords are printed once to the terminal and never stored or logged in clear.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from . import auth
from .db import AuditEvent, UserAccount, make_session_factory
from .errors import PceError


class UserError(PceError, ValueError):
    """An account operation that is not allowed (unknown user, duplicate, bad role, other firm)."""


_factory: sessionmaker[Session] | None = None


def _db() -> Session:
    global _factory
    if _factory is None:
        _factory = make_session_factory()
    return _factory()


def _to_account(u: UserAccount) -> auth.Account:
    return auth.Account(
        username=u.username,
        password_hash=u.password_hash,
        tenant=u.tenant_id,
        roles=tuple(u.roles),
        admin=u.admin,
        totp_secret=u.totp_secret,
        session_version=u.session_version,
        must_change_password=u.must_change_password,
        stored=True,
    )


def load(username: str) -> auth.Account | None:
    """The active account with this username, or None (unknown and disabled look the same)."""
    with _db() as db:
        u = db.scalar(select(UserAccount).where(UserAccount.username == username, UserAccount.active))
        return _to_account(u) if u else None


def one_time_password() -> str:
    return secrets.token_urlsafe(12)  # 16 characters, above auth.MIN_PASSWORD_LEN


def _check_roles(roles: list[str]) -> list[str]:
    if not roles or not set(roles) <= set(auth.ROLES):
        raise UserError(f"roles must be a non-empty subset of {', '.join(auth.ROLES)}")
    return sorted(set(roles))


def create(username: str, tenant: str, roles: list[str], admin: bool = False, by: str = "cli") -> str:
    """Create an account and return its one-time password (shown once, must be changed at first sign-in)."""
    name = username.strip().lower()
    if not name or len(name) > 100 or not name.replace(".", "").replace("-", "").replace("_", "").isalnum():
        raise UserError("username: letters, digits, dot, dash or underscore, at most 100 characters")
    pw = one_time_password()
    with _db() as db:
        if auth.get_account(name) or db.scalar(select(UserAccount.id).where(UserAccount.username == name)):
            raise UserError("username already taken")
        db.add(
            UserAccount(
                username=name,
                tenant_id=tenant,
                password_hash=auth.hash_password(pw),
                roles=_check_roles(roles),
                admin=admin,
                must_change_password=True,
                created_by=by,
            )
        )
        db.commit()
    return pw


def _update(username: str, tenant: str | None, **changes: Any) -> UserAccount:
    with _db() as db:
        u = db.scalar(select(UserAccount).where(UserAccount.username == username.strip().lower()))
        if not u or (tenant is not None and u.tenant_id != tenant):
            raise UserError("no such user")  # same answer for another firm's users: no existence leak
        for k, v in changes.items():
            setattr(u, k, v)
        u.session_version += 1  # every change to an account ends its open sessions
        db.commit()
        return u


def reset(username: str, tenant: str | None = None) -> str:
    """New one-time password, second factor cleared: the person sets both again at next sign-in."""
    pw = one_time_password()
    _update(
        username, tenant, password_hash=auth.hash_password(pw), totp_secret=None, must_change_password=True
    )
    return pw


def set_active(username: str, active: bool, tenant: str | None = None) -> None:
    _update(username, tenant, active=active)


def sign_out_everywhere(username: str, tenant: str | None = None) -> None:
    _update(username, tenant)


def finish_setup(username: str, new_password: str | None, totp_secret: str | None) -> None:
    """Called by account setup after the person proved the password and, if given, the new code."""
    changes: dict[str, Any] = {}
    if new_password is not None:
        if len(new_password) < auth.MIN_PASSWORD_LEN:
            raise UserError(f"password must be at least {auth.MIN_PASSWORD_LEN} characters")
        changes.update(password_hash=auth.hash_password(new_password), must_change_password=False)
    if totp_secret is not None:
        changes["totp_secret"] = totp_secret
    _update(username, None, **changes)


def record(tenant: str, user: str, action: str, **detail: Any) -> None:
    """Audit an account event (sign-in, setup, admin change). Usernames and counts only, never secrets."""
    with _db() as db:
        db.add(AuditEvent(tenant_id=tenant, prospect_id=None, user=user, action=action, detail=detail))
        db.commit()


def list_users(tenant: str) -> list[dict[str, Any]]:
    with _db() as db:
        rows = db.scalars(
            select(UserAccount).where(UserAccount.tenant_id == tenant).order_by(UserAccount.username)
        )
        return [
            {
                "username": u.username,
                "roles": u.roles,
                "admin": u.admin,
                "active": u.active,
                "mfa": bool(u.totp_secret),
                "must_change_password": u.must_change_password,
                "created_at": u.created_at,
                "created_by": u.created_by,
            }
            for u in rows
        ]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m pce.users", description="Manage FeeLens accounts.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create")
    c.add_argument("username")
    c.add_argument("--tenant", required=True)
    c.add_argument("--role", action="append", required=True, choices=auth.ROLES)
    c.add_argument("--admin", action="store_true")
    ls = sub.add_parser("list")
    ls.add_argument("--tenant", required=True)
    for name in ("reset", "disable", "enable"):
        sub.add_parser(name).add_argument("username")
    sub.add_parser("new-totp-secret")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "create":
            pw = create(a.username, a.tenant, a.role, a.admin)
            print(f"Created {a.username.lower()}. One-time password (shown once): {pw}")
        elif a.cmd == "list":
            for u in list_users(a.tenant):
                print(u)
        elif a.cmd == "reset":
            print(f"One-time password (shown once): {reset(a.username)}")
        elif a.cmd in ("disable", "enable"):
            set_active(a.username, a.cmd == "enable")
            print(f"{a.username}: {a.cmd}d")
        else:
            print(auth.new_totp_secret())
    except UserError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
