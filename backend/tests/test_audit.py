"""Tamper-evident activity log: sign-ins, views, downloads, admin actions, and who may read it (SC-11.8).

SYNTHETIC data only.
"""

import os
import tempfile

os.environ.setdefault("PCE_DATA_DIR", tempfile.mkdtemp(prefix="pce-test-"))
os.environ.setdefault("PCE_DATABASE_URL", f"sqlite:///{os.environ['PCE_DATA_DIR']}/t.sqlite")

from conftest import session_headers
from fastapi.testclient import TestClient
from sqlalchemy import text

from pce import audit, auth
from pce.api import app

client = TestClient(app)
PW = "SYNTHETIC audit passphrase"
ANALYST = session_headers("audit-firm", "audit.analyst", "analyst")
VIEWER = session_headers("audit-firm", "audit.viewer", "viewer")
SENIOR = session_headers("audit-firm", "audit.senior", "senior")
ADMIN = session_headers("audit-firm", "audit.admin", "admin")
OTHER = session_headers("audit-other", "audit.othersenior", "senior")


def log(h: dict = VIEWER, **params) -> dict:
    r = client.get("/api/audit", params=params, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def actions(h: dict = VIEWER, **params) -> list[str]:
    return [e["action"] for e in log(h, **params)["events"]]


def test_sign_in_failure_sign_out_are_logged():
    auth.add_account("audit.person", PW, "audit-firm", ("analyst",))
    c = TestClient(app)
    assert (
        c.post(
            "/api/auth/login", json={"username": "audit.person", "password": "wrong password!"}
        ).status_code
        == 401
    )
    r = c.post("/api/auth/login", json={"username": "audit.person", "password": PW})
    assert r.status_code == 200
    c.post("/api/auth/logout", headers={"X-CSRF-Token": r.json()["csrf_token"]})
    got = actions(user="audit.person")
    assert got[:3] == ["auth.logout", "auth.login", "auth.login_failed"], got


def test_viewing_a_document_and_downloading_a_report_are_logged(statement_pdf):
    pid = client.post(
        "/api/prospects", json={"code": "AUD-1", "label": "SYNTHETIC", "domicile": "CH"}, headers=ANALYST
    ).json()["id"]
    up = client.post(
        f"/api/prospects/{pid}/documents",
        files=[("files", ("statement.pdf", statement_pdf.read_bytes(), "application/pdf"))],
        headers=ANALYST,
    )
    did = up.json()["results"][0]["document_id"]
    assert client.get(f"/api/documents/{did}/file", headers=VIEWER).status_code == 200
    ev = log(user="audit.viewer", action="document.")["events"][0]
    assert (
        ev["action"] == "document.viewed"
        and ev["detail"] == {"document_id": did}
        and ev["prospect_id"] == pid
    )


def test_admin_viewer_and_senior_read_the_log_others_do_not():
    for h in (ADMIN, VIEWER, SENIOR):
        assert client.get("/api/audit", headers=h).status_code == 200
    assert client.get("/api/audit", headers=ANALYST).status_code == 403
    assert "audit.viewed" in actions(ADMIN, action="audit.")  # reading the log is itself logged


def test_one_firm_never_sees_another_firms_events():
    client.post("/api/admin/users", json={"username": "audit.hire", "roles": ["viewer"]}, headers=ADMIN)
    assert any(e["action"] == "user.created" for e in log(ADMIN)["events"])
    other = log(OTHER)
    assert all(e["user"] == "audit.othersenior" for e in other["events"]), other["events"]


def test_tamper_check_finds_changed_inserted_and_deleted_rows():
    """Each tampering is done in a transaction that is rolled back, so the real log stays intact."""
    assert log(SENIOR)["check"]["ok"] is True
    newest = log(SENIOR)["events"][0]["id"]
    sql = {
        "changed after it was written": "UPDATE audit_event SET user = 'nobody' WHERE id = :i",
        "deleted": "DELETE FROM audit_event WHERE id = :i",
        "not written by the application": (
            "INSERT INTO audit_event (id, tenant_id, at, user, action, detail) "
            "VALUES (:i + 1000, 'audit-firm', '2026-01-01', 'ghost', 'report.approved', '{}')"
        ),
    }
    for problem, stmt in sql.items():
        with auth.db()() as s:
            s.execute(text(stmt), {"i": newest})
            check = audit.verify(s, "audit-firm")
            s.rollback()
        assert check["ok"] is False, problem
        if problem == "deleted":
            assert check["deleted"] == 1
        else:
            event_id = newest + (1000 if problem.startswith("not") else 0)
            assert {"event_id": event_id, "problem": problem} in check["problems"]
    assert log(SENIOR)["check"]["ok"] is True
