import json
import os
import re
import tempfile
from decimal import Decimal
from pathlib import Path

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


def test_document_pipeline_traces_every_stage():
    pid = seeded()
    docs = client.get(f"/api/prospects/{pid}/documents", headers=A).json()
    by_name = {d["filename"]: d for d in docs}
    keys = ["upload", "read", "classify", "extract", "review", "validate", "categorize", "result"]
    for d in docs:
        r = client.get(f"/api/documents/{d['id']}/pipeline", headers=A)
        assert r.status_code == 200
        body = r.json()
        assert [s["key"] for s in body["stages"]] == keys
        assert all(s["status"] in ("ok", "warn", "fail", "skipped") for s in body["stages"])
        assert {"label": "SHA-256", "value": d["sha256"]} in body["stages"][0]["details"]
        assert not re.search(r"min_margin_pct|servicing_cost|annual_contribution", json.dumps(body))
    scan = client.get(
        f"/api/documents/{by_name['alpha_estratto_conto_Q3_2026_scan.pdf']['id']}/pipeline", headers=A
    ).json()
    read = scan["stages"][1]
    assert read["status"] == "warn" and any("OCR" in w for w in read["warnings"])  # scanned pages flagged
    assert read["ms"] is not None and scan["total_ms"] > 0
    stmt = by_name["alpha_statement_of_assets_2026-09-30.pdf"]
    st = {
        s["key"]: s for s in client.get(f"/api/documents/{stmt['id']}/pipeline", headers=A).json()["stages"]
    }
    assert all(v["where"].startswith("p.") for v in st["extract"]["values"])  # every value has its page
    assert any("add up" in c["title"] for c in st["validate"]["checks"])
    kid = by_name["kid_ZZGEQLDRA013.pdf"]
    cat = client.get(f"/api/documents/{kid['id']}/pipeline", headers=A).json()["stages"][6]
    assert {"counted", "included_in_parent"} <= {a["role"] for a in cat["atoms"]}  # AMF inside OCF, once
    assert client.get(f"/api/documents/{kid['id']}/pipeline", headers=B).status_code == 404


def test_every_counted_line_traces_to_its_source_inline():
    pid = seeded()
    r = client.get(f"/api/prospects/{pid}/analysis", headers=A).json()
    counted = [a for a in r["current"]["atoms"] if a["role"] == "counted"]
    assert counted and all(a["evidence"] for a in counted)
    for a in counted:
        for e in a["evidence"]:
            assert e["filename"] and ((e["page"] and e["bbox"]) or (e["sheet"] and e["cell"]))
    fund = next(a for a in counted if a["fee_code"] == "FUND_ONGOING" and a["basis_amount"])
    roles = {e["role"]: e for e in fund["evidence"]}
    assert set(roles) == {"value", "basis"}  # the rate from the KID and the holding value from the statement
    assert Decimal(roles["basis"]["value"]) == Decimal(fund["basis_amount"])
    assert r["review_points"] and r["review_points"][0]["severity"] == "high"
    assert not re.search(r"min_margin_pct|servicing_cost|annual_contribution", json.dumps(r))


def pdf_text(content: bytes) -> str:
    import io

    import pdfplumber

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        return "\n".join(pg.extract_text() or "" for pg in pdf.pages)


def test_report_pdf_italian_full_sources_and_read_status():
    pid = seeded()
    en = pdf_text(client.get(f"/api/prospects/{pid}/report.pdf", headers=A).content)
    it = client.get(f"/api/prospects/{pid}/report.pdf?lang=it", headers=A)
    assert it.headers["content-disposition"].endswith('-it.pdf"')
    it_text = pdf_text(it.content)
    assert "Analisi dei costi del portafoglio" in it_text and "Allegato" in it_text
    assert "Portfolio cost review" in en and "Risparmio" not in en
    # Every sourced appendix line names its full file and page (wrapped, never cut).
    a = client.get(f"/api/prospects/{pid}/analysis", headers=A).json()
    flat = re.sub(r"\s+", "", en)
    for atom in a["scenarios"]["current_comparable"]["atoms"]:
        if atom["role"] == "counted" and atom.get("evidence_sources"):
            assert re.sub(r"\s+", "", atom["evidence_sources"][0]) in flat
    assert re.search(r"\d+ values read from \d+ documents", en)
    assert client.get(f"/api/prospects/{pid}/report.pdf?lang=xx", headers=A).status_code == 422


def test_report_never_calls_a_dearer_proposal_a_saving():
    from pce.report import saving_parts

    assert saving_parts("-2588.07", "at_least") == (
        False,
        "Proposal costs more per year",
        "at most",
        "2588.07",
    )
    assert saving_parts("6520.10", "at_least") == (True, "Annual saving", "at least", "6520.10")
    C = session_headers("firm-c", "cat", "analyst")
    pid = client.post("/api/demo/seed", headers=C).json()["id"]
    client.put(f"/api/prospects/{pid}/proposal", headers=C, json={"custody_bps": "200"})
    a = client.get(f"/api/prospects/{pid}/analysis", headers=C).json()
    assert Decimal(a["scenarios"]["same_holdings"]["comparison"]["annual_saving"]) < 0
    text = pdf_text(client.get(f"/api/prospects/{pid}/report.pdf", headers=C).content)
    assert "Proposal costs more per year" in text
    assert "Annual saving" not in text and "CHF -" not in text.split("Annual cost by layer")[0]


def test_report_without_statement_shows_no_total():
    D = session_headers("firm-d", "dan", "analyst")
    pid = client.post(
        "/api/prospects", headers=D, json={"code": "P-KID", "label": "KID only", "domicile": "CH"}
    )
    pid = pid.json()["id"]
    kid = Path(__file__).resolve().parents[2] / "data/synthetic/prospect_p1042/kid_ZZWLDIDX0014.pdf"
    client.post(
        f"/api/prospects/{pid}/documents",
        headers=D,
        files=[("files", (kid.name, kid.read_bytes(), "application/pdf"))],
    )
    text = pdf_text(client.get(f"/api/prospects/{pid}/report.pdf", headers=D).content)
    assert "Costs are not calculated yet" in text
    assert "CHF 0" not in text and "saving" not in text.lower()
