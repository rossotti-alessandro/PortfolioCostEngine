"""Web hardening: the login gate on /api/*, CSRF and Origin checks, security headers, request size cap.

One middleware so the order is explicit: size cap, then authentication, then CSRF, then the route,
then headers on every response (errors included). Routes still take the session through ``pce.api.ctx``;
the middleware is defence in depth for routes that forget it.
"""

from __future__ import annotations

import os
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from . import auth

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
        request.state.account = acc
        return await call_next(request)


# ------------------------------------------------------------------ routes
router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


def _me(acc: auth.Account, token: str) -> dict:
    return {
        "username": acc.username,
        "tenant": acc.tenant,
        "roles": list(acc.roles),
        "admin": acc.admin,
        "csrf_token": auth.csrf_token(token),
    }


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
    auth.PER_CLIENT.reset(ck)
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
    return _me(acc, token)


@router.get("/me")
def me(session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None) -> dict:
    acc = auth.read_session(session)
    if not acc or not session:
        raise HTTPException(401, "sign in required")
    return _me(acc, session)


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE, path="/", secure=COOKIE_SECURE, httponly=True, samesite="strict")
    return {"ok": True}
