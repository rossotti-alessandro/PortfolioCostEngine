"""SC-11.8: views and downloads are audited without document content; audit entries cannot be changed."""

import os
import tempfile

os.environ.setdefault("PCE_DATA_DIR", tempfile.mkdtemp(prefix="pce-test-"))
os.environ.setdefault("PCE_DATABASE_URL", f"sqlite:///{os.environ['PCE_DATA_DIR']}/t.sqlite")

import pytest
from conftest import session_headers
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from pce.api import SessionFactory, app
from pce.db import AuditEvent

client = TestClient(app)
H = session_headers("audit-firm", "audit.viewer", "analyst")


def test_opening_a_prospect_and_viewing_a_document_are_audited(statement_pdf):
    pid = client.post(
        "/api/prospects", headers=H, json={"code": "AUD-1", "label": "SYNTHETIC", "domicile": "CH"}
    )
    pid = pid.json()["id"]
    files = [("files", ("Mario Rossi statement.pdf", statement_pdf.read_bytes(), "application/pdf"))]
    did = client.post(f"/api/prospects/{pid}/documents", headers=H, files=files).json()["results"][0][
        "document_id"
    ]
    assert client.get(f"/api/prospects/{pid}", headers=H).status_code == 200
    assert client.get(f"/api/documents/{did}/file", headers=H).status_code == 200
    log = client.get(f"/api/prospects/{pid}/audit", headers=H).json()
    actions = [e["action"] for e in log]
    assert "prospect.opened" in actions and "document.viewed" in actions
    viewed = next(e for e in log if e["action"] == "document.viewed")
    assert viewed["user"] == "audit.viewer" and viewed["detail"] == {"document_id": did}
    assert "Rossi" not in str([e for e in log if e["action"] in ("prospect.opened", "document.viewed")])


def test_audit_entries_cannot_be_changed():
    with SessionFactory() as db:
        db.add(AuditEvent(tenant_id="audit-firm", prospect_id=None, user="x", action="test.entry", detail={}))
        db.commit()
        with pytest.raises(IntegrityError, match="cannot be changed"):
            db.execute(
                update(AuditEvent).where(AuditEvent.action == "test.entry").values(user="someone else")
            )
        db.rollback()
        assert db.scalar(select(AuditEvent.user).where(AuditEvent.action == "test.entry")) == "x"
