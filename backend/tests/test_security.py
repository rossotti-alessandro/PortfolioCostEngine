"""Login, sessions, CSRF, throttling, headers and upload guards (SC-9.4)."""

import os
import re
import tempfile

os.environ.setdefault("PCE_DATA_DIR", tempfile.mkdtemp(prefix="pce-test-"))
os.environ.setdefault("PCE_DATABASE_URL", f"sqlite:///{os.environ['PCE_DATA_DIR']}/t.sqlite")

import pytest
from conftest import session_headers
from fastapi.testclient import TestClient

from pce import auth, security
from pce.api import app, safe_filename

PW = "a long enough test password"
auth.add_account("sec.admin", PW, "sec-firm", auth.ROLES, admin=True)
auth.add_account("sec.analyst", PW, "sec-firm", ("analyst",))


@pytest.fixture(autouse=True)
def _fresh_throttle():
    for t in (auth.PER_CLIENT, auth.PER_USER):
        t._hits.clear()


def login(user: str = "sec.admin", pw: str = PW) -> tuple[TestClient, dict]:
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"username": user, "password": pw})
    assert r.status_code == 200, r.text
    return c, {security.CSRF_HEADER: r.json()["csrf_token"]}


def test_every_api_route_needs_a_session():
    anon = TestClient(app)
    assert anon.get("/api/health").status_code == 200
    open_paths = {"/api/health", "/api/auth/login", "/api/auth/logout"}
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path.startswith("/api/") or path in open_paths:
            continue
        for method in getattr(route, "methods", set()) - {"HEAD"}:
            url = re.sub(r"\{[^}]+\}", "1", path)
            r = anon.request(method, url)
            assert r.status_code == 401, (method, url, r.status_code)
    for doc in ("/docs", "/openapi.json"):
        assert anon.get(doc).status_code == 401


def test_login_sets_hardened_cookie_and_me_works():
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"username": "SEC.Admin ", "password": PW})
    assert r.status_code == 200
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/" in cookie
    me = c.get("/api/auth/me").json()
    assert me["username"] == "sec.admin" and me["admin"] and set(me["roles"]) == set(auth.ROLES)
    assert c.get("/api/prospects").status_code == 200
    c.post("/api/auth/logout")
    assert c.get("/api/prospects").status_code == 401


def test_wrong_password_and_unknown_user_look_the_same():
    c = TestClient(app)
    a = c.post("/api/auth/login", json={"username": "sec.admin", "password": "nope"})
    b = c.post("/api/auth/login", json={"username": "nobody", "password": "nope"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_sixth_failure_from_one_client_is_throttled():
    c = TestClient(app)
    codes = [
        c.post("/api/auth/login", json={"username": "sec.admin", "password": f"bad{i}"}).status_code
        for i in range(6)
    ]
    assert codes == [401] * 5 + [429]
    r = c.post("/api/auth/login", json={"username": "sec.admin", "password": PW})
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0  # even the right password waits


def test_tampered_or_expired_session_is_refused():
    acc = auth.get_account("sec.admin")
    tok = auth.issue_session(acc)
    body, sig = tok.split(".")
    forged = auth._b64(auth._unb64(body).replace(b"sec.admin", b"sec.analyst")) + "." + sig
    assert auth.read_session(forged) is None
    assert auth.read_session(auth.issue_session(acc, now=0)) is None
    assert auth.read_session(tok) == acc


def test_password_change_ends_old_sessions():
    acc = auth.add_account("sec.rotate", PW, "sec-firm", ("analyst",))
    tok = auth.issue_session(acc)
    auth.add_account("sec.rotate", PW + "!", "sec-firm", ("analyst",))
    assert auth.read_session(tok) is None


def test_mutations_need_csrf_token_and_same_origin():
    c, csrf = login()
    body = {"code": "SEC-1", "label": "SYNTHETIC", "domicile": "CH"}
    assert c.post("/api/prospects", json=body).status_code == 403
    assert c.post("/api/prospects", json=body, headers={security.CSRF_HEADER: "x"}).status_code == 403
    evil = {**csrf, "Origin": "https://evil.example"}
    assert c.post("/api/prospects", json=body, headers=evil).status_code == 403
    assert c.post("/api/auth/login", json={"username": "a", "password": "b"}, headers=evil).status_code == 403
    ok = c.post("/api/prospects", json=body, headers={**csrf, "Origin": "http://testserver"})
    assert ok.status_code == 201, ok.text
    other, _ = login()  # a token from another session does not work here
    assert other.post("/api/prospects", json=body, headers=csrf).status_code == 403


def test_headers_cannot_change_tenant_user_or_raise_role():
    c, csrf = login("sec.analyst")
    spoof = {"X-Tenant-Id": "firm-a", "X-User": "sam"}
    assert c.get("/api/prospects", headers=spoof).status_code == 200
    created = c.post(
        "/api/prospects",
        json={"code": "SEC-2", "label": "SYNTHETIC", "domicile": "CH"},
        headers={**csrf, **spoof},
    ).json()
    audit = c.get(f"/api/prospects/{created['id']}/audit").json()
    assert all(a["user"] == "sec.analyst" for a in audit)
    assert c.get(f"/api/prospects/{created['id']}/internal", headers={"X-Role": "senior"}).status_code == 403
    assert (
        TestClient(app)
        .get(f"/api/prospects/{created['id']}", headers=session_headers("sec-other", "sec.o", "senior"))
        .status_code
        == 404
    )


def test_security_headers_on_api_ui_and_errors():
    anon = TestClient(app)
    for r in (anon.get("/api/health"), anon.get("/api/prospects"), anon.get("/")):
        h = r.headers
        assert "frame-ancestors 'none'" in h["content-security-policy"]
        assert "script-src 'self'" in h["content-security-policy"]
        assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
        assert h["referrer-policy"] == "no-referrer"
    assert anon.get("/api/health").headers["cache-control"] == "no-store"


def test_oversized_request_is_refused_before_parsing():
    c, csrf = login()
    r = c.post(
        "/api/prospects/1/documents",
        headers={**csrf, "Content-Length": str(security.MAX_BODY_BYTES + 1)},
        content=b"x",
    )
    assert r.status_code == 413


def test_upload_rejects_disguised_files_and_cleans_names(statement_pdf):
    c, csrf = login()
    pid = c.post(
        "/api/prospects", json={"code": "SEC-3", "label": "SYNTHETIC", "domicile": "CH"}, headers=csrf
    ).json()["id"]
    fake = ("files", ("fake.pdf", b"%PDF-1.4\n" + b"MZ" * 10, "application/pdf"))
    html = ("files", ("x.xlsx", b"<html><script>alert(1)</script></html>", "application/vnd.ms-excel"))
    res = c.post(f"/api/prospects/{pid}/documents", files=[fake, html], headers=csrf).json()["results"]
    assert [r["status"] for r in res] == ["rejected", "rejected"]
    too_many = [("files", (f"f{i}.pdf", b"%PDF", "application/pdf")) for i in range(21)]
    assert c.post(f"/api/prospects/{pid}/documents", files=too_many, headers=csrf).status_code == 413
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("C:\\x\\a<b>.pdf") == "ab.pdf"
    assert safe_filename("\x00\n.pdf") == "pdf"


def test_password_hash_roundtrip():
    h = auth.hash_password(PW)
    assert h.startswith("scrypt$") and auth.verify_password(PW, h)
    assert not auth.verify_password(PW + "x", h) and not auth.verify_password(PW, "garbage")
    with pytest.raises(ValueError):
        auth.add_account("short", "short", "t")
