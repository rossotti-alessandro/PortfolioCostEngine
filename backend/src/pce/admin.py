"""Team & access: an admin adds people, sets their roles, resets passwords and ends sessions (SC-11.12).

Every route needs the ``users.manage`` permission (checked by the middleware for /api/admin/* and again
here) and touches only the admin's own firm. A one-time password is shown once, in the response, and the
person must replace it at first sign-in. Nothing here can lock the firm out: the env break-glass admin is
not stored in the database and an admin cannot deactivate or demote themselves.
"""

from __future__ import annotations

import re
import secrets
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from . import auth, permissions
from .db import AuditEvent, AuthSession, UserAccount

router = APIRouter(prefix="/api/admin", tags=["admin"])

USERNAME = re.compile(r"^[a-z0-9][a-z0-9._-]{1,62}[a-z0-9]$")


class Admin(BaseModel):
    tenant: str
    user: str


def admin_ctx(request: Request) -> Admin:
    acc: auth.Account | None = getattr(request.state, "account", None)
    role = permissions.active_role(acc.roles, request.headers.get("x-role")) if acc else None
    if acc is None or role is None or not permissions.can(role, "users.manage"):
        raise HTTPException(403, "only an admin can manage people and access")
    return Admin(tenant=acc.tenant, user=acc.username)


A = Annotated[Admin, Depends(admin_ctx)]


def _audit(s, a: Admin, action: str, **detail) -> None:
    s.add(AuditEvent(tenant_id=a.tenant, prospect_id=None, user=a.user, action=action, detail=detail))


def _one_time_password() -> str:
    return secrets.token_urlsafe(12)  # 16 characters, above the 12-character minimum


def _out(u: UserAccount, live: int) -> dict:
    return {
        "username": u.username,
        "display_name": u.display_name,
        "roles": list(u.roles),
        "active": u.active,
        "must_change_password": u.must_change_password,
        "created_at": u.created_at,
        "created_by": u.created_by,
        "live_sessions": live,
    }


def _get(s, a: Admin, username: str) -> UserAccount:
    u = s.scalar(
        select(UserAccount).where(UserAccount.username == username, UserAccount.tenant_id == a.tenant)
    )
    if u is None:
        raise HTTPException(404, "person not found")  # same answer for another firm's people
    return u


@router.get("/users")
def list_users(a: A) -> dict:
    now = time.time()
    with auth.db()() as s:
        users = s.scalars(
            select(UserAccount).where(UserAccount.tenant_id == a.tenant).order_by(UserAccount.username)
        ).all()
        live = dict(
            s.execute(
                select(AuthSession.username, func.count())
                .where(
                    AuthSession.revoked.is_(False),
                    AuthSession.expires_at > now,
                    AuthSession.last_seen > now - auth.IDLE_TIMEOUT_S,
                )
                .group_by(AuthSession.username)
            ).all()
        )
        return {"users": [_out(u, live.get(u.username, 0)) for u in users], "roles": list(permissions.ROLES)}


class NewUser(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    display_name: str = Field(default="", max_length=200)
    roles: list[str] = Field(min_length=1)


@router.post("/users", status_code=201)
def create_user(body: NewUser, a: A) -> dict:
    name = body.username.strip().lower()
    if not USERNAME.match(name):
        raise HTTPException(422, "username: 3-64 lower-case letters, digits, dot, dash or underscore")
    try:
        roles = auth.check_roles(body.roles)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if name in auth._accounts:
        raise HTTPException(409, "this username is taken")
    pw = _one_time_password()
    with auth.db()() as s:
        if s.scalar(select(UserAccount.id).where(UserAccount.username == name)):
            raise HTTPException(409, "this username is taken")  # across firms too: sign-in has no firm field
        u = UserAccount(
            tenant_id=a.tenant,
            username=name,
            display_name=body.display_name.strip(),
            password_hash=auth.hash_password(pw),
            roles=list(roles),
            created_by=a.user,
        )
        s.add(u)
        _audit(s, a, "user.created", username=name, roles=list(roles))
        s.commit()
        return {**_out(u, 0), "one_time_password": pw}


class UserPatch(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    roles: list[str] | None = None
    active: bool | None = None


@router.patch("/users/{username}")
def update_user(username: str, body: UserPatch, a: A) -> dict:
    with auth.db()() as s:
        u = _get(s, a, username)
        if u.username == a.user and (
            body.active is False or (body.roles is not None and "admin" not in body.roles)
        ):
            raise HTTPException(400, "you cannot deactivate yourself or remove your own admin role")
        before = {"roles": list(u.roles), "active": u.active}
        if body.roles is not None:
            try:
                u.roles = list(auth.check_roles(body.roles))
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
        if body.active is not None:
            u.active = body.active
        if body.display_name is not None:
            u.display_name = body.display_name.strip()
        _audit(
            s,
            a,
            "user.updated",
            username=u.username,
            before=before,
            after={"roles": u.roles, "active": u.active},
        )
        s.commit()
        out = _out(u, 0)
    # A changed role or a deactivation applies now, not at the next sign-in.
    if (body.roles is not None or body.active is False) and username != a.user:
        auth.revoke_all(username)
    return out


@router.post("/users/{username}/reset-password")
def reset_password(username: str, a: A) -> dict:
    with auth.db()() as s:
        _get(s, a, username)
        _audit(s, a, "user.password_reset", username=username)
        s.commit()
    pw = _one_time_password()
    auth.set_password(username, pw, must_change=True)  # also ends their sessions
    return {"username": username, "one_time_password": pw}


@router.post("/users/{username}/sign-out")
def sign_out_everywhere(username: str, a: A) -> dict:
    with auth.db()() as s:
        _get(s, a, username)
        _audit(s, a, "user.signed_out", username=username)
        s.commit()
    return {"ended": auth.revoke_all(username)}
