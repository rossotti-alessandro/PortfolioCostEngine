"""SC-11.11: erase a prospect and everything derived from it; admins only; one audit entry stays."""

import os
import tempfile
from pathlib import Path

os.environ.setdefault("PCE_DATA_DIR", tempfile.mkdtemp(prefix="pce-test-"))
os.environ.setdefault("PCE_DATABASE_URL", f"sqlite:///{os.environ['PCE_DATA_DIR']}/t.sqlite")

from conftest import session_headers
from fastapi.testclient import TestClient
from sqlalchemy import select

from pce import auth, security
from pce.api import SessionFactory, app
from pce.crm.models import Contact
from pce.db import AuditEvent, Document, FactRow, Prospect

client = TestClient(app)
ANALYST = session_headers("del-firm", "del.analyst", "analyst")
OTHER = session_headers("del-other", "del.other", "senior")


def admin_headers(tenant: str, user: str) -> dict:
    acc = auth.add_account(user, "correct horse battery staple", tenant, ("senior",), admin=True)
    token = auth.issue_session(acc)
    return {"Cookie": f"{security.SESSION_COOKIE}={token}", security.CSRF_HEADER: auth.csrf_token(token)}


ADMIN = admin_headers("del-firm", "del.admin")
OTHER_ADMIN = admin_headers("del-other", "del.otheradmin")


def prospect_with_doc(code: str, pdf: Path) -> tuple[int, str]:
    pid = client.post(
        "/api/prospects", headers=ADMIN, json={"code": code, "label": "SYNTHETIC", "domicile": "CH"}
    )
    assert pid.status_code == 201, pid.text
    pid = pid.json()["id"]
    r = client.post(
        f"/api/prospects/{pid}/documents",
        headers=ADMIN,
        files=[("files", ("statement.pdf", pdf.read_bytes(), "application/pdf"))],
    )
    assert r.status_code == 200, r.text
    with SessionFactory() as db:
        path = db.scalar(select(Document.storage_path).where(Document.prospect_id == pid))
    return pid, path


def erase(pid: int, code: str, headers: dict = ADMIN, **params) -> object:
    return client.delete(
        f"/api/prospects/{pid}",
        headers=headers,
        params={"confirm": code, "reason": "prospect_request", **params},
    )


def test_erasure_removes_every_row_and_the_file_and_keeps_one_audit_entry(statement_pdf):
    pid, path = prospect_with_doc("DEL-1", statement_pdf)
    keep, _ = prospect_with_doc("DEL-2", statement_pdf)  # same file, same firm: shared on disk
    with SessionFactory() as db:
        db.add(Contact(tenant_id="del-firm", name="SYNTHETIC Person", owner="del.admin", prospect_id=pid))
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
        doc_ids = db.scalars(select(Document.id)).all()
        assert all(f.document_id in doc_ids for f in db.scalars(select(FactRow)))
        log = db.scalars(select(AuditEvent).where(AuditEvent.action == "prospect.erased")).all()[-1]
    assert log.prospect_id is None and "DEL-1" not in str(log.detail) and "statement" not in str(log.detail)
    assert client.get(f"/api/prospects/{pid}", headers=ADMIN).status_code == 404

    assert erase(keep, "DEL-2").json()["files_removed"] == 1
    assert not Path(path).exists()  # last user gone: the original is deleted


def test_non_admin_and_other_firm_cannot_erase(statement_pdf):
    pid, path = prospect_with_doc("DEL-3", statement_pdf)
    assert erase(pid, "DEL-3", headers=ANALYST).status_code == 403
    assert erase(pid, "DEL-3", headers=OTHER_ADMIN).status_code == 404
    assert erase(pid, "DEL-3", headers=OTHER).status_code == 403
    assert client.get(f"/api/prospects/{pid}", headers=ADMIN).status_code == 200 and Path(path).exists()
    bad_reason = client.delete(
        f"/api/prospects/{pid}", headers=ADMIN, params={"confirm": "DEL-3", "reason": "Mario Rossi asked"}
    )
    assert bad_reason.status_code == 422  # free text could carry a name into the kept audit entry
