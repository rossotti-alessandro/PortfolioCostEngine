"""Who may do what: one table, checked for every /api request (SC-11.12).

Routes keep their own checks (internal economics, approval); this table is the outer wall, so a new route
that forgets a check still cannot be written by a read-only role or reached by the wrong one.

Roles
- analyst: prepares cost reviews and works the CRM.
- senior: like analyst, sees internal economics, approves client reports (four-eyes in ``pce.api``).
- relationship_manager: like analyst, sees internal economics, cannot approve.
- viewer: read-only (compliance, auditor). Never internal economics, never writes.
- admin: manages people and sessions of its own firm. Holds no client-data rights by itself, so an
  IT administrator does not read portfolios (least privilege). The env break-glass admin holds every role.

The firm's activity log (who signed in, viewed, downloaded, changed what) is read by admin, viewer
(compliance) and senior: ``audit.read``. Erasing a prospect and everything derived from it (SC-11.11)
cannot be undone and is ``data.erase``: senior only.
"""

from __future__ import annotations

import re

ROLES = ("analyst", "senior", "relationship_manager", "viewer", "admin")

PERMISSIONS: dict[str, frozenset[str]] = {
    "data.read": frozenset({"analyst", "senior", "relationship_manager", "viewer"}),
    "data.write": frozenset({"analyst", "senior", "relationship_manager"}),
    "internal.read": frozenset({"senior", "relationship_manager"}),
    "report.approve": frozenset({"senior"}),
    "users.manage": frozenset({"admin"}),
    "audit.read": frozenset({"admin", "viewer", "senior"}),
    "data.erase": frozenset({"senior"}),
}

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def can(role: str, permission: str) -> bool:
    return role in PERMISSIONS[permission]


def required(method: str, path: str) -> str:
    """The permission a request needs. Unknown /api paths fall into the data permissions."""
    if path.startswith("/api/admin/"):
        return "users.manage"
    if path == "/api/audit":
        return "audit.read"
    if method == "DELETE" and re.fullmatch(r"/api/prospects/\d+", path):
        return "data.erase"
    if path.endswith("/internal"):
        return "internal.read"
    if path.endswith("/approve"):
        return "report.approve"
    return "data.read" if method in SAFE_METHODS else "data.write"


def active_role(held: tuple[str, ...], asked: str | None) -> str | None:
    """The role a request acts in: the one asked for (X-Role) if held, else a sensible default."""
    if asked:
        return asked if asked in held else None
    for r in ("analyst", "senior", "relationship_manager", "viewer", "admin"):
        if r in held:
            return r
    return None
