import json
import os
import re
import tempfile

os.environ["PCE_DATA_DIR"] = tempfile.mkdtemp(prefix="pce-test-")
os.environ["PCE_DATABASE_URL"] = f"sqlite:///{os.environ['PCE_DATA_DIR']}/t.sqlite"

import pytest
from conftest import session_headers
from fastapi.testclient import TestClient

from pce.api import app

pytestmark = pytest.mark.ocr  # seeding reads the scanned synthetic statement
client = TestClient(app)
A = session_headers("firm-a", "ana", "analyst")
SENIOR = session_headers("firm-a", "sam", "senior")
B = session_headers("firm-b", "bob", "senior")


def seeded() -> int:
    return client.post("/api/demo/seed", headers=A).json()["id"]


def test_seed_is_idempotent():
    pid = seeded()
    again = client.post("/api/demo/seed", headers=A).json()
    assert again["id"] == pid and again["documents_added"] == 0
    assert len(client.get(f"/api/prospects/{pid}/documents", headers=A).json()) == 11


def test_cross_tenant_access_denied():
    pid = seeded()
    assert client.get(f"/api/prospects/{pid}/analysis", headers=B).status_code == 404
    doc = client.get(f"/api/prospects/{pid}/documents", headers=A).json()[0]
    assert client.get(f"/api/documents/{doc['id']}/file", headers=B).status_code == 404
    assert client.get("/api/prospects", headers=B).json() == []


def test_analysis_hides_internal_and_internal_requires_role():
    pid = seeded()
    r = client.get(f"/api/prospects/{pid}/analysis", headers=A).json()
    assert "internal" not in r
    assert "internal" not in r["proposal_inputs"]  # servicing cost and minimum margin are firm-only
    assert not re.search(r"min_margin_pct|servicing_cost|annual_contribution", json.dumps(r))
    assert client.get(f"/api/prospects/{pid}/internal", headers=A).status_code == 403
    assert (
        client.get(f"/api/prospects/{pid}/internal", headers=SENIOR).json()["internal"]["verdict"]
        == "insufficient_evidence"
    )


def test_correction_persists_with_history_and_changes_totals():
    pid = seeded()
    docs = client.get(f"/api/prospects/{pid}/documents", headers=A).json()
    rep = next(d for d in docs if d["doc_type"] == "cost_report")
    fx = next(
        f
        for f in client.get(f"/api/documents/{rep['id']}/facts", headers=A).json()
        if f["fee_code"] == "FX_COMMISSION"
    )
    before = client.get(f"/api/prospects/{pid}/analysis", headers=A).json()["current"]["total_known"]
    assert (
        client.post(
            f"/api/facts/{fx['id']}/review", headers=A, json={"action": "correct", "value": "1340.00"}
        ).status_code
        == 422
    )
    ok = client.post(
        f"/api/facts/{fx['id']}/review",
        headers=A,
        json={"action": "correct", "value": "1'340.00", "reason": "debit advice shows 1,340"},
    )
    assert ok.json()["value"] == "1340.00" and ok.json()["value_extracted"] == "1240.00"
    after = client.get(f"/api/prospects/{pid}/analysis", headers=A).json()["current"]["total_known"]
    assert float(after) - float(before) == 100.0
    hist = client.get(f"/api/facts/{fx['id']}/history", headers=A).json()
    assert hist[-1]["old"] == "1240.00" and hist[-1]["reason"]
    client.post(f"/api/facts/{fx['id']}/review", headers=A, json={"action": "reset"})


def test_upload_guards_and_duplicates():
    pid = seeded()
    bad = client.post(
        f"/api/prospects/{pid}/documents",
        headers=A,
        files=[
            ("files", ("x.exe", b"MZ...", "application/octet-stream")),
            ("files", ("fake.pdf", b"not a pdf", "application/pdf")),
        ],
    ).json()["results"]
    assert all(x["status"] == "rejected" for x in bad)
    from pathlib import Path

    kid = next(Path(__file__).resolve().parents[2].glob("data/synthetic/prospect_p1042/kid_ZZWLDIDX0014.pdf"))
    dup = client.post(
        f"/api/prospects/{pid}/documents",
        headers=A,
        files=[("files", (kid.name, kid.read_bytes(), "application/pdf"))],
    ).json()["results"]
    assert dup[0]["status"] == "duplicate"


def test_report_pdf_and_approval_snapshot():
    pid = seeded()
    assert client.post(f"/api/prospects/{pid}/approve", headers=A, json={}).status_code == 403
    client.post(f"/api/prospects/{pid}/approve", headers=SENIOR, json={"note": "ok"})
    r = client.get(f"/api/prospects/{pid}/analysis", headers=A).json()
    assert r["approval"]["valid"]
    pdf = client.get(f"/api/prospects/{pid}/report.pdf", headers=A)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert b"contribution" not in pdf.content.lower()


def test_proposal_versioning():
    pid = seeded()
    v = client.put(f"/api/prospects/{pid}/proposal", headers=A, json={"custody_bps": "8"}).json()["version"]
    prop = client.get(f"/api/prospects/{pid}/proposal", headers=A).json()
    assert prop["config"]["custody_bps"] == "8" and prop["history"][0]["version"] == v
    assert (
        client.put(f"/api/prospects/{pid}/proposal", headers=A, json={"custody_bps": "-1"}).status_code == 422
    )
    client.put(f"/api/prospects/{pid}/proposal", headers=A, json={"custody_bps": "10"})
