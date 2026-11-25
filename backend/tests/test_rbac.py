"""Named users, role permissions, revocable sessions and four-eyes approval (SC-11.12). SYNTHETIC data."""

import os
import tempfile

os.environ.setdefault("PCE_DATA_DIR", tempfile.mkdtemp(prefix="pce-test-"))
os.environ.setdefault("PCE_DATABASE_URL", f"sqlite:///{os.environ['PCE_DATA_DIR']}/t.sqlite")

from conftest import session_headers
from fastapi.testclient import TestClient

from pce import auth, security
from pce.api import app

client = TestClient(app)
VIEWER = session_headers("rbac-firm", "rbac.viewer", "viewer")
ANALYST = session_headers("rbac-firm", "rbac.analyst", "analyst")
SENIOR = session_headers("rbac-firm", "rbac.senior", "senior")
SENIOR2 = session_headers("rbac-firm", "rbac.senior2", "senior")
ADMIN = session_headers("rbac-firm", "rbac.admin", "admin")
OTHER_ADMIN = session_headers("rbac-other", "rbac.otheradmin", "admin")


def new_prospect(code: str, h: dict = ANALYST) -> int:
    r = client.post("/api/prospects", json={"code": code, "label": "SYNTHETIC", "domicile": "CH"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def sign_in(username: str, password: str) -> tuple[TestClient, dict]:
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return c, {security.CSRF_HEADER: r.json()["csrf_token"]}


def test_viewer_reads_but_never_writes_or_sees_internal():
    pid = new_prospect("RBAC-V")
    assert client.get(f"/api/prospects/{pid}", headers=VIEWER).status_code == 200
    assert client.get("/api/crm/contacts", headers=VIEWER).status_code == 200
    for method, url, body in [
        ("post", "/api/prospects", {"code": "X", "label": "SYNTHETIC", "domicile": "CH"}),
        ("patch", f"/api/prospects/{pid}", {"label": "changed"}),
        ("put", f"/api/prospects/{pid}/proposal", {}),
        ("post", "/api/crm/contacts", {"name": "SYNTHETIC viewer"}),
        ("post", f"/api/prospects/{pid}/approve", {}),
    ]:
        r = getattr(client, method)(url, json=body, headers=VIEWER)
        assert r.status_code == 403, (method, url, r.text)
    assert client.get(f"/api/prospects/{pid}/internal", headers=VIEWER).status_code == 403
    assert client.get("/api/admin/users", headers=VIEWER).status_code == 403


def test_only_admins_manage_people_and_admins_do_not_read_portfolios():
    assert client.get("/api/admin/users", headers=ANALYST).status_code == 403
    assert client.get("/api/admin/users", headers=SENIOR).status_code == 403
    assert client.get("/api/admin/users", headers=ADMIN).status_code == 200
    assert client.get("/api/prospects", headers=ADMIN).status_code == 403  # least privilege


def test_admin_adds_a_person_who_must_choose_a_password_first():
    r = client.post(
        "/api/admin/users",
        json={"username": "rbac.new", "display_name": "SYNTHETIC Person", "roles": ["analyst"]},
        headers=ADMIN,
    )
    assert r.status_code == 201, r.text
    otp = r.json()["one_time_password"]
    assert len(otp) >= auth.MIN_PASSWORD_LEN
    assert (
        client.post(
            "/api/admin/users", json={"username": "rbac.new", "roles": ["analyst"]}, headers=ADMIN
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/admin/users", json={"username": "x y", "roles": ["analyst"]}, headers=ADMIN
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/admin/users", json={"username": "rbac.bad", "roles": ["root"]}, headers=ADMIN
        ).status_code
        == 422
    )

    c, csrf = sign_in("rbac.new", otp)
    assert c.get("/api/auth/me").json()["must_change_password"] is True
    assert c.get("/api/prospects").status_code == 403  # nothing until the password is changed
    new_pw = "a brand new SYNTHETIC passphrase"
    assert (
        c.post(
            "/api/auth/password", json={"current": "wrong one here!", "new": new_pw}, headers=csrf
        ).status_code
        == 403
    )
    r = c.post("/api/auth/password", json={"current": otp, "new": new_pw}, headers=csrf)
    assert r.status_code == 200, r.text
    assert r.json()["must_change_password"] is False
    assert c.get("/api/prospects").status_code == 200
    assert (
        TestClient(app).post("/api/auth/login", json={"username": "rbac.new", "password": otp}).status_code
        == 401
    )
    sign_in("rbac.new", new_pw)


def test_sign_out_revokes_the_session_even_for_a_copied_cookie():
    acc = auth.get_account("rbac.analyst")
    token = auth.issue_session(acc)
    cookie = {"Cookie": f"{security.SESSION_COOKIE}={token}", "X-Role": "analyst"}
    assert client.get("/api/prospects", headers=cookie).status_code == 200
    client.post("/api/auth/logout", headers=cookie)
    assert client.get("/api/prospects", headers=cookie).status_code == 401


def test_idle_session_expires():
    acc = auth.get_account("rbac.analyst")
    t0 = 2_000_000_000.0
    token = auth.issue_session(acc, now=t0)
    assert auth.read_session(token, now=t0 + auth.IDLE_TIMEOUT_S - 5) == acc
    later = t0 + auth.IDLE_TIMEOUT_S - 5 + auth.IDLE_TIMEOUT_S + 1  # activity above moved last_seen
    assert auth.read_session(token, now=later) is None


def test_deactivate_role_change_and_sign_out_everywhere_apply_at_once():
    pw = client.post(
        "/api/admin/users", json={"username": "rbac.leaver", "roles": ["analyst"]}, headers=ADMIN
    )
    otp = pw.json()["one_time_password"]
    c, csrf = sign_in("rbac.leaver", otp)
    good = "SYNTHETIC leaver passphrase"
    c.post("/api/auth/password", json={"current": otp, "new": good}, headers=csrf)
    assert c.get("/api/prospects").status_code == 200
    # Another firm's admin cannot see or touch this person.
    assert (
        client.patch("/api/admin/users/rbac.leaver", json={"active": False}, headers=OTHER_ADMIN).status_code
        == 404
    )
    assert "rbac.leaver" not in str(client.get("/api/admin/users", headers=OTHER_ADMIN).json())
    # Role change: the open session ends.
    assert (
        client.patch("/api/admin/users/rbac.leaver", json={"roles": ["viewer"]}, headers=ADMIN).status_code
        == 200
    )
    assert c.get("/api/prospects").status_code == 401
    c, csrf = sign_in("rbac.leaver", good)
    assert (
        c.post(
            "/api/prospects", json={"code": "L", "label": "SYNTHETIC", "domicile": "CH"}, headers=csrf
        ).status_code
        == 403
    )
    assert client.post("/api/admin/users/rbac.leaver/sign-out", headers=ADMIN).json()["ended"] >= 1
    assert c.get("/api/prospects").status_code == 401
    # Deactivated: cannot sign in at all.
    client.patch("/api/admin/users/rbac.leaver", json={"active": False}, headers=ADMIN)
    assert (
        TestClient(app)
        .post("/api/auth/login", json={"username": "rbac.leaver", "password": good})
        .status_code
        == 401
    )


def test_admin_cannot_lock_themselves_out():
    r = client.post("/api/admin/users", json={"username": "rbac.admin2", "roles": ["admin"]}, headers=ADMIN)
    otp = r.json()["one_time_password"]
    c, csrf = sign_in("rbac.admin2", otp)
    good = "SYNTHETIC second admin passphrase"
    me = c.post("/api/auth/password", json={"current": otp, "new": good}, headers=csrf).json()
    csrf = {security.CSRF_HEADER: me["csrf_token"]}  # a new session, so a new CSRF token
    assert c.patch("/api/admin/users/rbac.admin2", json={"active": False}, headers=csrf).status_code == 400
    assert (
        c.patch("/api/admin/users/rbac.admin2", json={"roles": ["viewer"]}, headers=csrf).status_code == 400
    )


def test_four_eyes_the_preparer_cannot_approve(statement_pdf):
    pid = new_prospect("RBAC-4E", SENIOR)
    up = client.post(
        f"/api/prospects/{pid}/documents",
        files=[("files", ("statement.pdf", statement_pdf.read_bytes(), "application/pdf"))],
        headers=SENIOR,
    )
    assert up.status_code == 200, up.text
    r = client.post(f"/api/prospects/{pid}/approve", json={}, headers=SENIOR)
    assert r.status_code == 403 and "second person" in r.json()["detail"]
    assert (
        client.post(f"/api/prospects/{pid}/approve", json={"note": "SYNTHETIC"}, headers=SENIOR2).status_code
        == 200
    )


def test_env_admin_is_break_glass_and_holds_every_role():
    auth.add_account("rbac.envadmin", "SYNTHETIC env admin passphrase", "rbac-firm", admin=True)
    c, _ = sign_in("rbac.envadmin", "SYNTHETIC env admin passphrase")
    me = c.get("/api/auth/me").json()
    assert me["admin"] and {"admin", "viewer", "senior"} <= set(me["roles"])
    assert c.get("/api/admin/users", headers={"X-Role": "admin"}).status_code == 200
    assert c.get("/api/prospects").status_code == 200
