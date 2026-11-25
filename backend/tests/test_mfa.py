"""Authenticator-app second factor (TOTP, SC-11.7). SYNTHETIC accounts only."""

import os
import tempfile

os.environ.setdefault("PCE_DATA_DIR", tempfile.mkdtemp(prefix="pce-test-"))
os.environ.setdefault("PCE_DATABASE_URL", f"sqlite:///{os.environ['PCE_DATA_DIR']}/t.sqlite")

import base64
import time

import pytest
from conftest import session_headers
from fastapi.testclient import TestClient

from pce import auth, security
from pce.api import app

ADMIN = session_headers("mfa-firm", "mfa.admin", "admin")
PW = "SYNTHETIC mfa passphrase"


def code(secret: str, offset: int = 0) -> str:
    return auth.totp_code(secret, int(time.time() // auth.TOTP_STEP_S) + offset)


def person(name: str) -> tuple[TestClient, dict]:
    """A named analyst who has chosen a password; returns a signed-in client and its CSRF header."""
    c = TestClient(app)
    otp = c.post("/api/admin/users", json={"username": name, "roles": ["analyst"]}, headers=ADMIN).json()[
        "one_time_password"
    ]
    r = c.post("/api/auth/login", json={"username": name, "password": otp})
    me = c.post(
        "/api/auth/password",
        json={"current": otp, "new": PW},
        headers={security.CSRF_HEADER: r.json()["csrf_token"]},
    ).json()
    return c, {security.CSRF_HEADER: me["csrf_token"]}


def enable(c: TestClient, csrf: dict) -> tuple[str, dict]:
    key = c.get("/api/auth/mfa").json()
    r = c.post(
        "/api/auth/mfa",
        json={"secret": key["secret"], "proof": key["proof"], "code": code(key["secret"])},
        headers=csrf,
    )
    assert r.status_code == 200, r.text
    assert r.json()["mfa"] is True
    return key["secret"], {security.CSRF_HEADER: r.json()["csrf_token"]}


def test_totp_matches_the_rfc_6238_reference():
    # RFC 6238 appendix B, SHA-1, T = 59 s: 94287082 -> the last 6 digits.
    secret = base64.b32encode(b"12345678901234567890").decode()  # the RFC test key
    assert auth.totp_code(secret, 59 // 30) == "287082"


def test_after_enabling_sign_in_needs_the_code_and_each_code_works_once():
    c, csrf = person("mfa.ana")
    old = {"Cookie": f"{security.SESSION_COOKIE}={c.cookies[security.SESSION_COOKIE]}"}
    secret, _ = enable(c, csrf)
    fresh = TestClient(app)
    r = fresh.post("/api/auth/login", json={"username": "mfa.ana", "password": PW})
    assert r.status_code == 401 and r.json()["detail"] == security.MFA_REQUIRED
    assert (
        fresh.post(
            "/api/auth/login", json={"username": "mfa.ana", "password": PW, "code": "000000"}
        ).status_code
        == 401
    )
    good = code(secret, 1)  # the next window: the enable call above used the current one
    assert (
        fresh.post("/api/auth/login", json={"username": "mfa.ana", "password": PW, "code": good}).status_code
        == 200
    )
    replay = TestClient(app).post(
        "/api/auth/login", json={"username": "mfa.ana", "password": PW, "code": good}
    )
    assert replay.status_code == 401  # a code is accepted once
    assert TestClient(app).get("/api/prospects", headers=old).status_code == 401  # older sessions end
    assert c.get("/api/prospects").status_code == 200  # the session that enabled it is renewed


def test_a_forged_key_is_refused():
    c, csrf = person("mfa.forge")
    mine = auth.new_totp_secret()
    r = c.post("/api/auth/mfa", json={"secret": mine, "proof": "x" * 20, "code": code(mine)}, headers=csrf)
    assert r.status_code == 400


def test_admin_password_reset_removes_the_authenticator():
    c, csrf = person("mfa.lost")
    enable(c, csrf)
    otp = (
        TestClient(app)
        .post("/api/admin/users/mfa.lost/reset-password", headers=ADMIN)
        .json()["one_time_password"]
    )
    r = TestClient(app).post("/api/auth/login", json={"username": "mfa.lost", "password": otp})
    assert r.status_code == 200 and r.json()["mfa"] is False


def test_required_mfa_keeps_an_account_in_setup(monkeypatch: pytest.MonkeyPatch):
    c, csrf = person("mfa.must")
    monkeypatch.setenv("PCE_REQUIRE_MFA", "1")
    assert c.get("/api/auth/me").json()["mfa_setup_needed"] is True
    assert c.get("/api/prospects").status_code == 403
    _, csrf = enable(c, csrf)
    assert c.get("/api/prospects").status_code == 200
