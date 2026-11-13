"""SC-11.7: personal accounts in the database, first sign-in setup, authenticator codes, admin actions."""

import os
import tempfile
import time

os.environ.setdefault("PCE_DATA_DIR", tempfile.mkdtemp(prefix="pce-test-"))
os.environ.setdefault("PCE_DATABASE_URL", f"sqlite:///{os.environ['PCE_DATA_DIR']}/t.sqlite")

import pytest
from fastapi.testclient import TestClient

from pce import auth, security, users
from pce.api import app

PW = "a long enough new password"


@pytest.fixture(autouse=True)
def _fresh_throttle():
    for t in (auth.PER_CLIENT, auth.PER_USER):
        t._hits.clear()
    auth._last_step.clear()


def code(secret: str, offset: int = 0) -> str:
    return auth.totp_code(secret, int(time.time() // auth.TOTP_STEP_S) + offset)


def sign_in(username: str, password: str, totp: str | None = None) -> tuple[TestClient, dict, dict]:
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"username": username, "password": password, "code": totp})
    assert r.status_code == 200, r.text
    return c, {security.CSRF_HEADER: r.json()["csrf_token"]}, r.json()


def ready_user(name: str, tenant: str = "acc-firm", admin: bool = False) -> str:
    """A database account that finished setup; returns its authenticator secret."""
    users.create(name, tenant, ["analyst", "senior"], admin=admin)
    secret = auth.new_totp_secret()
    users.finish_setup(name, PW, secret)
    return secret


def test_totp_matches_rfc6238_vector():
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # noqa: S105 - RFC 6238 appendix B public test seed
    assert auth.totp_code(secret, 59 // 30) == "287082"
    assert auth.totp_code(secret, 1111111109 // 30) == "081804"


def test_first_sign_in_forces_new_password_and_authenticator(monkeypatch):
    monkeypatch.setenv("PCE_REQUIRE_MFA", "1")
    otp = users.create("acc.new", "acc-firm", ["analyst"])
    c, h, me = sign_in("acc.new", otp)
    assert me["setup_required"] and me["must_change_password"]
    assert c.get("/api/prospects").status_code == 403  # nothing but account setup until it is done

    s = c.get("/api/auth/setup").json()
    assert s["uri"].startswith("otpauth://totp/FeeLens:acc.new?secret=")
    bad = c.post("/api/auth/setup", headers=h, json={"new_password": PW})
    assert bad.status_code == 400  # MFA required: a password alone does not finish setup
    wrong = {"new_password": PW, "secret": s["secret"], "proof": s["proof"], "code": "000000"}
    assert c.post("/api/auth/setup", headers=h, json=wrong).status_code == 400
    forged = {**wrong, "secret": auth.new_totp_secret(), "code": None}
    assert c.post("/api/auth/setup", headers=h, json=forged).status_code == 400  # key not issued by us

    ok = c.post("/api/auth/setup", headers=h, json={**wrong, "code": code(s["secret"])})
    assert ok.status_code == 200, ok.text
    assert not ok.json()["setup_required"] and ok.json()["mfa"]
    assert c.get("/api/prospects").status_code == 200

    # The one-time password is gone; the new one needs the authenticator code.
    assert (
        TestClient(app).post("/api/auth/login", json={"username": "acc.new", "password": otp}).status_code
        == 401
    )
    r = TestClient(app).post("/api/auth/login", json={"username": "acc.new", "password": PW})
    assert r.status_code == 401 and r.json()["detail"] == security.MFA_REQUIRED
    sign_in("acc.new", PW, code(s["secret"], 1))


def test_wrong_or_replayed_code_is_refused():
    secret = ready_user("acc.codes")
    bad = TestClient(app).post(
        "/api/auth/login", json={"username": "acc.codes", "password": PW, "code": "123456"}
    )
    assert bad.status_code == 401 and bad.json()["detail"] == "wrong authenticator code"
    used = code(secret)
    sign_in("acc.codes", PW, used)
    again = TestClient(app).post(
        "/api/auth/login", json={"username": "acc.codes", "password": PW, "code": used}
    )
    assert again.status_code == 401


def test_admin_manages_only_own_firm_and_actions_end_sessions():
    a_secret = ready_user("acc.admin", admin=True)
    u_secret = ready_user("acc.member")
    ready_user("other.member", tenant="other-firm")
    admin, ah, _ = sign_in("acc.admin", PW, code(a_secret))
    member, _, _ = sign_in("acc.member", PW, code(u_secret))

    assert member.get("/api/admin/users").status_code == 403  # not an admin
    names = {u["username"] for u in admin.get("/api/admin/users").json()}
    assert {"acc.admin", "acc.member"} <= names and "other.member" not in names
    assert admin.post("/api/admin/users/other.member/disable", headers=ah).status_code == 404

    created = admin.post("/api/admin/users", headers=ah, json={"username": "Acc.Third", "roles": ["analyst"]})
    assert created.status_code == 201 and len(created.json()["one_time_password"]) >= auth.MIN_PASSWORD_LEN
    bad_role = admin.post("/api/admin/users", headers=ah, json={"username": "acc.x", "roles": ["root"]})
    assert bad_role.status_code == 400

    assert member.get("/api/prospects").status_code == 200
    assert admin.post("/api/admin/users/acc.member/sign-out", headers=ah).status_code == 200
    assert member.get("/api/prospects").status_code == 401  # session ended by the admin

    assert admin.post("/api/admin/users/acc.member/disable", headers=ah).status_code == 200
    r = TestClient(app).post("/api/auth/login", json={"username": "acc.member", "password": PW})
    assert r.status_code == 401  # disabled looks like unknown

    reset = admin.post("/api/admin/users/acc.member/enable", headers=ah)
    assert reset.status_code == 200
    otp = admin.post("/api/admin/users/acc.member/reset", headers=ah).json()["one_time_password"]
    _, _, me = sign_in("acc.member", otp)  # second factor cleared: the person links it again
    assert me["setup_required"] and not me["mfa"]
    assert admin.post("/api/admin/users/acc.admin/disable", headers=ah).status_code == 400


def test_account_events_are_audited_without_secrets():
    from sqlalchemy import select

    from pce.db import AuditEvent

    secret = ready_user("acc.audited")
    sign_in("acc.audited", PW, code(secret))
    with users._db() as db:
        rows = db.scalars(select(AuditEvent).where(AuditEvent.user == "acc.audited")).all()
    assert [r.action for r in rows] == ["auth.signed_in"]
    assert PW not in str(rows[0].detail) and secret not in str(rows[0].detail)


def test_cli_creates_admin_and_prints_one_time_password(capsys):
    assert users.main(["create", "cli.admin", "--tenant", "acc-firm", "--role", "senior", "--admin"]) == 0
    out = capsys.readouterr().out
    assert "One-time password" in out
    assert users.main(["create", "cli.admin", "--tenant", "acc-firm", "--role", "senior"]) == 1
    acc = auth.get_account("cli.admin")
    assert acc and acc.admin and acc.must_change_password and acc.tenant == "acc-firm"
