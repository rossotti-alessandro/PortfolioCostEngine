"""Erase a prospect and everything derived from it (SC-11.11): seniors only, one log entry stays, and the
tamper check still passes. SYNTHETIC data only."""

import os
import tempfile
from pathlib import Path

os.environ.setdefault("PCE_DATA_DIR", tempfile.mkdtemp(prefix="pce-test-"))
os.environ.setdefault("PCE_DATABASE_URL", f"sqlite:///{os.environ['PCE_DATA_DIR']}/t.sqlite")

from conftest import session_headers
from fastapi.testclient import TestClient
from sqlalchemy import select

from pce import audit
from pce.api import SessionFactory, app
from pce.crm.models import Activity, Contact
from pce.db import AuditEvent, Document, FactRow, Prospect

client = TestClient(app)
SENIOR = session_headers("del-firm", "del.senior", "senior")
ANALYST = session_headers("del-firm", "del.analyst", "analyst")
VIEWER = session_headers("del-firm", "del.viewer", "viewer")
ADMIN = session_headers("del-firm", "del.admin", "admin")
OTHER = session_headers("del-other", "del.other", "senior")


def prospect_with_doc(code: str, pdf: Path) -> tuple[int, str]:
    r = client.post(
        "/api/prospects", headers=SENIOR, json={"code": code, "label": "SYNTHETIC", "domicile": "CH"}
    )
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    up = client.post(
        f"/api/prospects/{pid}/documents",
        headers=SENIOR,
        files=[("files", ("statement.pdf", pdf.read_bytes(), "application/pdf"))],
    )
    assert up.status_code == 200, up.text
    with SessionFactory() as db:
        path = db.scalar(select(Document.storage_path).where(Document.prospect_id == pid))
    return pid, path


def erase(pid: int, code: str, headers: dict = SENIOR, **params):
    return client.delete(
        f"/api/prospects/{pid}",
        headers=headers,
        params={"confirm": code, "reason": "prospect_request", **params},
    )


def test_erasure_removes_every_row_and_the_file_and_keeps_one_log_entry(statement_pdf):
    pid, path = prospect_with_doc("DEL-1", statement_pdf)
    keep, _ = prospect_with_doc("DEL-2", statement_pdf)  # same file, same firm: shared on disk
    with SessionFactory() as db:
        k = Contact(tenant_id="del-firm", name="SYNTHETIC Person", owner="del.senior", prospect_id=pid)
        db.add(k)
        db.flush()
        db.add(Activity(tenant_id="del-firm", contact_id=k.id, kind="note", summary="SYNTHETIC", user="u"))
        db.commit()
    assert erase(pid, "WRONG").status_code == 400

    r = erase(pid, "DEL-1", erase_contact="true")
    assert r.status_code == 200, r.text
    assert r.json()["documents"] == 1 and r.json()["contacts_deleted"] == 1
    assert Path(path).exists()  # still used by DEL-2
    with SessionFactory() as db:
        assert db.get(Prospect, pid) is None
        assert not db.scalars(select(Document).where(Document.prospect_id == pid)).all()
        assert not db.scalars(select(AuditEvent).where(AuditEvent.prospect_id == pid)).all()
        assert not db.scalars(select(Contact).where(Contact.name == "SYNTHETIC Person")).all()
        assert not db.scalars(select(Activity).where(Activity.summary == "SYNTHETIC")).all()
        doc_ids = db.scalars(select(Document.id)).all()
        assert all(f.document_id in doc_ids for f in db.scalars(select(FactRow)))
        log = db.scalars(select(AuditEvent).where(AuditEvent.action == "prospect.erased")).all()[-1]
        check = audit.verify(db, "del-firm")
    assert log.prospect_id is None and "DEL-1" not in str(log.detail) and "statement" not in str(log.detail)
    assert check["ok"] is True, check  # the gaps were made by the application and are listed in its entry
    assert client.get(f"/api/prospects/{pid}", headers=SENIOR).status_code == 404

    assert erase(keep, "DEL-2").json()["files_removed"] == 1
    assert not Path(path).exists()  # last user gone: the original is deleted


def test_only_a_senior_of_the_same_firm_can_erase(statement_pdf):
    pid, path = prospect_with_doc("DEL-3", statement_pdf)
    for h in (ANALYST, VIEWER, ADMIN):
        assert erase(pid, "DEL-3", headers=h).status_code == 403
    assert erase(pid, "DEL-3", headers=OTHER).status_code == 404
    assert client.get(f"/api/prospects/{pid}", headers=SENIOR).status_code == 200 and Path(path).exists()
    bad_reason = client.delete(
        f"/api/prospects/{pid}", headers=SENIOR, params={"confirm": "DEL-3", "reason": "SYNTHETIC Name asked"}
    )
    assert bad_reason.status_code == 422  # free text could carry a name into the kept log entry
