"""SC-7.6: the firm tariff is set once by a senior and is the starting point of every new cost review."""

import os
import tempfile

os.environ.setdefault("PCE_DATA_DIR", tempfile.mkdtemp(prefix="pce-test-"))
os.environ.setdefault("PCE_DATABASE_URL", f"sqlite:///{os.environ['PCE_DATA_DIR']}/t.sqlite")

from conftest import session_headers
from fastapi.testclient import TestClient

from pce.api import app

client = TestClient(app)
ANALYST = session_headers("firm-t", "ana", "analyst")
SENIOR = session_headers("firm-t", "sam", "senior")
OTHER = session_headers("firm-u", "olga", "senior")

TARIFF = {
    "firm_name": "Safe Capital",
    "eam_tiers": [["5000000", "80"], [None, "60"]],
    "custody_bps": "12",
    "custody_min": "1200",
}


def new_prospect(code: str, headers: dict) -> dict:
    pid = client.post("/api/prospects", json={"code": code, "label": code}, headers=headers).json()["id"]
    return client.get(f"/api/prospects/{pid}/proposal", headers=headers).json()["config"]


def test_new_reviews_start_from_the_saved_firm_tariff():
    assert client.put("/api/firm/tariff", json=TARIFF, headers=SENIOR).status_code == 200
    got = client.get("/api/firm/tariff", headers=ANALYST).json()
    assert got["saved"] and got["config"]["custody_bps"] == "12" and got["updated_by"] == "sam"
    cfg = new_prospect("T-1", ANALYST)
    assert cfg["firm_name"] == "Safe Capital"
    assert cfg["eam_tiers"] == [["5000000", "80"], [None, "60"]]
    assert cfg["custody_min"] == "1200"
    assert "annual_turnover_chf" in cfg  # per-prospect estimates still come from the defaults


def test_only_seniors_change_it_and_other_firms_never_see_it():
    assert client.put("/api/firm/tariff", json={"custody_bps": "1"}, headers=ANALYST).status_code == 403
    assert "internal" not in client.get("/api/firm/tariff", headers=ANALYST).json()["config"]
    other = client.get("/api/firm/tariff", headers=OTHER).json()
    assert not other["saved"] and other["config"]["firm_name"] != "Safe Capital"
    assert new_prospect("U-1", OTHER)["firm_name"] != "Safe Capital"


def test_invalid_inputs_are_refused_and_nothing_is_saved():
    client.put("/api/firm/tariff", json=TARIFF, headers=SENIOR)
    for bad in ({"custody_bps": "-1"}, {"fx_bps": "abc"}, {"eam_tiers": [["x", "50"]]}):
        assert client.put("/api/firm/tariff", json=bad, headers=SENIOR).status_code == 422
    assert client.get("/api/firm/tariff", headers=SENIOR).json()["config"]["custody_bps"] == "12"


def test_prospect_only_keys_are_not_stored_as_firm_tariff():
    client.put("/api/firm/tariff", json={"annual_turnover_chf": "1", "custody_bps": "12"}, headers=SENIOR)
    assert "annual_turnover_chf" not in client.get("/api/firm/tariff", headers=SENIOR).json()["config"]
