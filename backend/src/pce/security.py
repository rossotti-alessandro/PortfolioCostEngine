"""Web hardening: the login gate on /api/*, CSRF and Origin checks, security headers, request size cap.

One middleware so the order is explicit: size cap, then authentication, then CSRF, then the route,
then headers on every response (errors included). Routes still take the session through ``pce.api.ctx``;
the middleware is defence in depth for routes that forget it.
"""

from __future__ import annotations

import hmac
import os
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from . import auth, users

COOKIE_SECURE = os.environ.get("PCE_COOKIE_SECURE", "1") != "0"
# __Host- pins the cookie to this exact host over HTTPS, Path=/ and no Domain: subdomains cannot set it.
SESSION_COOKIE = "__Host-feelens_session" if COOKIE_SECURE else "feelens_session"
CSRF_HEADER = "X-CSRF-Token"
PUBLIC_API = {"/api/health", "/api/auth/login", "/api/auth/me", "/api/auth/logout"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
# Uploads: 20 files of at most 25 MB each (pce.api.MAX_UPLOAD_BYTES), plus multipart overhead.
MAX_BODY_BYTES = int(os.environ.get("PCE_MAX_REQUEST_MB", "100")) * 1024 * 1024
DEV_ORIGINS = {"http://localhost:5173", "http://127.0.0.1:5173"}

CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        # React and Recharts set style attributes; no inline <script> is ever allowed.
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self' data:",
        "worker-src 'self' blob:",  # PDF.js worker
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)
HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}
if COOKIE_SECURE:
    HEADERS["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"


def client_key(request: Request) -> str:
    # Behind Render's proxy uvicorn runs with --proxy-headers, so this is the forwarded client address.
    return request.client.host if request.client else "unknown"


def _origin_ok(request: Request) -> bool:
    """Reject cross-site writes. Browsers send Origin on every POST/PUT/PATCH/DELETE."""
    origin = request.headers.get("origin") or request.headers.get("referer")
    if not origin:
        return True  # non-browser clients; they still need the session cookie and the CSRF token
    o = urlsplit(origin)
    here = request.headers.get("host", "")
    return o.netloc == here or f"{o.scheme}://{o.netloc}" in DEV_ORIGINS


def _deny(status: int, detail: str) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status)


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        resp = await self._guard(request, call_next)
        for k, v in HEADERS.items():
            resp.headers.setdefault(k, v)
        if request.url.path.startswith("/api/"):
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    async def _guard(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        try:
            if int(request.headers.get("content-length", "0")) > MAX_BODY_BYTES:
                return _deny(413, "request too large")
        except ValueError:
            return _deny(400, "bad content-length")
        if not path.startswith("/api/") and path not in ("/docs", "/redoc", "/openapi.json"):
            return await call_next(request)  # the built UI: public, it holds no data
        unsafe = request.method not in SAFE_METHODS
        if unsafe and not _origin_ok(request):
            return _deny(403, "cross-site request refused")
        if path in PUBLIC_API:
            return await call_next(request)
        token = request.cookies.get(SESSION_COOKIE)
        acc = auth.read_session(token)
        if not acc or not token:
            return _deny(401, "sign in required")
        if unsafe and not auth.check_csrf(token, request.headers.get(CSRF_HEADER)):
            return _deny(403, "missing or invalid CSRF token")
        if auth.setup_required(acc) and not path.startswith("/api/auth/"):
            return _deny(403, "finish account setup first")  # only /api/auth/* until password and MFA are set
        if path.startswith("/api/admin/") and not acc.admin:
            return _deny(403, "admin only")
        request.state.account = acc
        return await call_next(request)


# ------------------------------------------------------------------ routes
router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=12)  # authenticator app code, when the account has one


MFA_REQUIRED = "authenticator code required"


def _me(acc: auth.Account, token: str) -> dict:
    return {
        "username": acc.username,
        "tenant": acc.tenant,
        "roles": list(acc.roles),
        "admin": acc.admin,
        "mfa": bool(acc.totp_secret),
        "setup_required": auth.setup_required(acc),
        "must_change_password": acc.must_change_password,
        "csrf_token": auth.csrf_token(token),
    }


def _set_cookie(response: Response, acc: auth.Account) -> str:
    token = auth.issue_session(acc)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=auth.SESSION_TTL_S,
        path="/",
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="strict",
    )
    return token


def _record(acc: auth.Account | None, action: str, **detail: object) -> None:
    if acc and acc.stored:  # env and test accounts have no firm database to write to
        users.record(acc.tenant, acc.username, action, **detail)


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response) -> dict:
    ck, uk = f"ip:{client_key(request)}", f"user:{body.username.strip().lower()}"
    wait = max(auth.PER_CLIENT.blocked(ck), auth.PER_USER.blocked(uk))
    if wait:
        raise HTTPException(
            429, "too many failed sign-ins, try again later", headers={"Retry-After": str(int(wait) + 1)}
        )
    acc = auth.authenticate(body.username, body.password)
    if not acc:
        auth.PER_CLIENT.fail(ck)
        auth.PER_USER.fail(uk)
        raise HTTPException(401, "wrong username or password")
    if acc.totp_secret:
        if not body.code:
            raise HTTPException(401, MFA_REQUIRED)  # password was right: ask for the second factor
        if not auth.verify_totp(acc.totp_secret, body.code, acc.username):
            auth.PER_CLIENT.fail(ck)
            auth.PER_USER.fail(uk)
            _record(acc, "auth.mfa_failed")
            raise HTTPException(401, "wrong authenticator code")
    auth.PER_CLIENT.reset(ck)
    _record(acc, "auth.signed_in", mfa=bool(acc.totp_secret))
    return _me(acc, _set_cookie(response, acc))


def _session(session: str | None) -> tuple[auth.Account, str]:
    acc = auth.read_session(session)
    if not acc or not session:
        raise HTTPException(401, "sign in required")
    return acc, session


@router.get("/me")
def me(session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None) -> dict:
    acc, token = _session(session)
    return _me(acc, token)


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE, path="/", secure=COOKIE_SECURE, httponly=True, samesite="strict")
    return {"ok": True}


# ------------------------------------------------------------------ account setup (first sign-in)
def _setup_proof(username: str, secret: str) -> str:
    # The new secret travels through the browser; this signature proves the server issued it for this user.
    return auth.csrf_token(f"totp-setup:{username}:{secret}")


@router.get("/setup")
def setup_start(session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None) -> dict:
    """A fresh authenticator key for this account. Nothing is saved until a code from it is confirmed."""
    acc, _ = _session(session)
    secret = auth.new_totp_secret()
    return {
        "secret": secret,
        "uri": auth.totp_uri(secret, acc.username),
        "proof": _setup_proof(acc.username, secret),
        "must_change_password": acc.must_change_password,
    }


class SetupIn(BaseModel):
    new_password: str | None = Field(default=None, max_length=200)
    secret: str | None = Field(default=None, max_length=64)
    proof: str | None = Field(default=None, max_length=100)
    code: str | None = Field(default=None, max_length=12)


@router.post("/setup")
def setup_finish(
    body: SetupIn,
    response: Response,
    session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> dict:
    acc, _ = _session(session)  # the middleware has checked the CSRF token
    if not acc.stored:
        raise HTTPException(400, "this account is managed by the server configuration")
    if acc.must_change_password and not body.new_password:
        raise HTTPException(400, "choose a new password")
    secret = None
    if body.secret:
        if not hmac.compare_digest(_setup_proof(acc.username, body.secret), body.proof or ""):
            raise HTTPException(400, "setup key expired, reload the page")
        if not auth.verify_totp(body.secret, body.code or "", acc.username):
            raise HTTPException(400, "wrong authenticator code")
        secret = body.secret
    elif auth.require_mfa() and not acc.totp_secret:
        raise HTTPException(400, "link an authenticator app")
    try:
        users.finish_setup(acc.username, body.new_password, secret)
    except users.UserError as exc:
        raise HTTPException(400, str(exc)) from exc
    _record(acc, "auth.setup_done", password=bool(body.new_password), mfa=bool(secret))
    fresh = auth.get_account(acc.username)
    assert fresh is not None
    return _me(fresh, _set_cookie(response, fresh))


# ------------------------------------------------------------------ account admin (admins of the same firm)
admin_router = APIRouter(prefix="/api/admin/users", tags=["admin"])


def _admin(request: Request) -> auth.Account:
    acc = getattr(request.state, "account", None)
    if acc is None or not acc.admin:  # the middleware already refuses non-admins; defence in depth
        raise HTTPException(403, "admin only")
    return acc


class NewUserIn(BaseModel):
    username: str = Field(min_length=2, max_length=100)
    roles: list[str] = Field(min_length=1)
    admin: bool = False


@admin_router.get("")
def admin_list(request: Request) -> list[dict]:
    return users.list_users(_admin(request).tenant)


@admin_router.post("", status_code=201)
def admin_create(body: NewUserIn, request: Request) -> dict:
    a = _admin(request)
    try:
        pw = users.create(body.username, a.tenant, body.roles, body.admin, by=a.username)
    except users.UserError as exc:
        raise HTTPException(400, str(exc)) from exc
    users.record(a.tenant, a.username, "admin.user_created", target=body.username.lower(), admin=body.admin)
    return {"username": body.username.lower(), "one_time_password": pw}


@admin_router.post("/{username}/{action}")
def admin_action(username: str, action: str, request: Request) -> dict:
    a = _admin(request)
    if username.lower() == a.username and action in ("disable", "reset"):
        raise HTTPException(400, "ask another admin to do this for your own account")
    try:
        if action == "reset":
            out: dict = {"one_time_password": users.reset(username, a.tenant)}
        elif action in ("disable", "enable"):
            users.set_active(username, action == "enable", a.tenant)
            out = {"ok": True}
        elif action == "sign-out":
            users.sign_out_everywhere(username, a.tenant)
            out = {"ok": True}
        else:
            raise HTTPException(404, "unknown action")
    except users.UserError as exc:
        raise HTTPException(404, str(exc)) from exc
    users.record(a.tenant, a.username, f"admin.user_{action.replace('-', '_')}", target=username.lower())
    return out
