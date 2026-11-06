"""CRM: contacts, stage history, funnel, tenant isolation and no internal economics in payloads."""

import os
import tempfile

os.environ.setdefault("PCE_DATA_DIR", tempfile.mkdtemp(prefix="pce-test-"))
os.environ.setdefault("PCE_DATABASE_URL", f"sqlite:///{os.environ['PCE_DATA_DIR']}/t.sqlite")

from conftest import session_headers
from fastapi.testclient import TestClient

from pce.api import app
from pce.crm.funnel import compute_funnel

client = TestClient(app)
A = session_headers("crm-a", "crm.ana", "analyst")
B = session_headers("crm-b", "crm.bob", "senior")
SEED = session_headers("crm-seed", "crm.seeder", "analyst")
FORBIDDEN = ("margin", "internal", "revenue", "contribution")


def new(name: str = "Test family", headers: dict = A, **kw) -> dict:
    r = client.post("/api/crm/contacts", json={"name": name, **kw}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def stage(cid: int, to: str, headers: dict = A, **kw):
    return client.post(f"/api/crm/contacts/{cid}/stage", json={"to_stage": to, **kw}, headers=headers)


def keys(o) -> set[str]:
    if isinstance(o, dict):
        return set(o) | {k for v in o.values() for k in keys(v)}
    if isinstance(o, list):
        return {k for v in o for k in keys(v)}
    return set()


# --- pure funnel -------------------------------------------------------------------------------


def ev(cid: int, to: str, day: int) -> dict:
    return {"contact_id": cid, "to_stage": to, "at": f"2026-03-{day:02d}T09:00:00+00:00"}


def ct(cid: int, st: str, aum: str | None = "1000000", **kw) -> dict:
    return {"id": cid, "stage": st, "created_at": "2026-03-01T09:00:00+00:00", "estimated_aum": aum,
            "currency": "CHF", "source": "referral", **kw}  # fmt: skip


def test_funnel_counts_furthest_stage_reached_including_lost():
    contacts = [ct(1, "won"), ct(2, "lost", lost_reason="price"), ct(3, "lead")]
    events = [
        ev(1, "lead", 1), ev(1, "qualified", 3), ev(1, "won", 11),
        ev(2, "lead", 1), ev(2, "qualified", 2), ev(2, "documents_received", 6), ev(2, "lost", 9),
        ev(3, "lead", 1),
    ]  # fmt: skip
    f = compute_funnel(contacts, events)
    reached = {s["stage"]: s["reached"] for s in f["stages"]}
    # Contact 1 jumped to won: it passed every stage. Contact 2 reached documents before being lost.
    assert reached == {"lead": 3, "qualified": 2, "documents_received": 2, "cost_review": 1,
                       "proposal_sent": 1, "won": 1}  # fmt: skip
    assert f["win_rate"] == "0.5000" and f["overall_conversion"] == "0.3333"
    assert f["stages"][1]["conversion_from_previous"] == "0.6667" and f["stages"][1]["drop_off"] == 1
    assert f["lost_reasons"] == [{"reason": "price", "label": "Price", "count": 1,
                                  "lost_after": {"documents_received": 1}}]  # fmt: skip
    assert f["median_days_to_win"] == "10.0"
    assert f["stages"][1]["median_days_in_stage"] == "6.0"  # qualified lasted 8 days (c1) and 4 days (c2)


def test_funnel_ratios_with_no_data_are_not_determined_not_zero():
    f = compute_funnel([], [])
    assert f["win_rate"] is None and f["overall_conversion"] is None
    assert all(s["share_of_total"] is None for s in f["stages"])


def test_funnel_unknown_aum_is_counted_not_zero():
    f = compute_funnel([ct(1, "lead", None), ct(2, "lead", "2500000")], [ev(1, "lead", 1), ev(2, "lead", 1)])
    lead = f["stages"][0]
    assert lead["aum"] == {"CHF": "2500000"} and lead["aum_unknown"] == 1
    assert f["pipeline_aum_unknown"] == 1


# --- API ---------------------------------------------------------------------------------------


def test_create_move_and_history():
    c = new("Vega test family", estimated_aum="3500000", current_banks=["Bank X (Synthetic)"])
    assert c["stage"] == "lead" and c["lifecycle"] == "prospect" and c["owner"] == "crm.ana"
    assert stage(c["id"], "qualified", note="intro call ok").status_code == 200
    assert stage(c["id"], "qualified").status_code == 409
    r = stage(c["id"], "won").json()
    assert r["lifecycle"] == "client"
    assert [h["to_stage"] for h in r["history"]] == ["lead", "qualified", "won"]
    assert r["history"][1]["note"] == "intro call ok" and r["history"][1]["user"] == "crm.ana"
    clients = client.get("/api/crm/contacts?lifecycle=client", headers=A).json()
    assert c["id"] in [k["id"] for k in clients]


def test_lost_needs_reason_and_reopen_clears_it():
    c = new()
    assert stage(c["id"], "lost").status_code == 422
    r = stage(c["id"], "lost", lost_reason="timing").json()
    assert r["lost_reason"] == "timing" and r["lifecycle"] == "lost"
    assert stage(c["id"], "qualified").json()["lost_reason"] is None


def test_validation_rejects_bad_input():
    assert client.post("/api/crm/contacts", json={"name": ""}, headers=A).status_code == 422
    assert (
        client.post("/api/crm/contacts", json={"name": "x", "estimated_aum": "abc"}, headers=A).status_code
        == 422
    )
    assert (
        client.post("/api/crm/contacts", json={"name": "x", "estimated_aum": "-1"}, headers=A).status_code
        == 422
    )
    assert client.post("/api/crm/contacts", json={"name": "x", "stage": "won"}, headers=A).status_code == 422
    assert stage(new()["id"], "nowhere").status_code == 422


def test_patch_and_activity():
    c = new()
    body = {"next_action": "Send letter", "estimated_aum": ""}
    r = client.patch(f"/api/crm/contacts/{c['id']}", json=body, headers=A).json()
    assert r["next_action"] == "Send letter" and r["estimated_aum"] is None
    body = {"kind": "meeting", "summary": "Met in Lugano"}
    a = client.post(f"/api/crm/contacts/{c['id']}/activities", json=body, headers=A)
    assert a.status_code == 201
    assert (
        client.get(f"/api/crm/contacts/{c['id']}", headers=A).json()["activities"][0]["summary"]
        == "Met in Lugano"
    )


def test_cross_tenant_isolation():
    c = new("Tenant A only")
    assert client.get(f"/api/crm/contacts/{c['id']}", headers=B).status_code == 404
    assert client.patch(f"/api/crm/contacts/{c['id']}", json={"name": "x"}, headers=B).status_code == 404
    assert stage(c["id"], "won", headers=B).status_code == 404
    assert client.post(f"/api/crm/contacts/{c['id']}/cost-review", json={}, headers=B).status_code == 404
    assert all(k["id"] != c["id"] for k in client.get("/api/crm/contacts", headers=B).json())
    # Linking to another tenant's cost review is refused too.
    pid = client.post("/api/prospects", json={"code": "B-1", "label": "B prospect"}, headers=B).json()["id"]
    assert (
        client.post(
            f"/api/crm/contacts/{c['id']}/cost-review", json={"prospect_id": pid}, headers=A
        ).status_code
        == 404
    )


def test_cost_review_link_creates_prospect_once():
    c = new("Linked family", domicile="it")
    r1 = client.post(f"/api/crm/contacts/{c['id']}/cost-review", json={}, headers=A).json()
    r2 = client.post(f"/api/crm/contacts/{c['id']}/cost-review", json={}, headers=A).json()
    assert r1["prospect"] == r2["prospect"] and r1["prospect"]["code"] == f"CRM-{c['id']}"
    p = client.get(f"/api/prospects/{r1['prospect']['id']}", headers=A)
    assert p.status_code == 200


def test_seed_is_idempotent_synthetic_and_funnel_is_consistent():
    h = SEED
    first = client.post("/api/crm/demo/seed", headers=h).json()["contacts_added"]
    assert first == 41
    assert client.post("/api/crm/demo/seed", headers=h).json()["contacts_added"] == 0
    contacts = client.get("/api/crm/contacts", headers=h).json()
    assert len(contacts) == 41 and all(k["synthetic"] for k in contacts)
    f = client.get("/api/crm/funnel", headers=h).json()
    assert f["synthetic"] is True and f["total"] == 41
    reached = [s["reached"] for s in f["stages"]]
    assert reached == sorted(reached, reverse=True) and reached[0] == 41
    assert f["won"] == f["stages"][-1]["reached"] and f["won"] + f["lost"] + f["open"] == 41
    assert f["won"] > 0 and f["lost"] > 0
    assert sum(r["count"] for r in f["lost_reasons"]) == f["lost"]
    assert sum(s["contacts"] for s in f["by_source"]) == 41
    p1042 = next(k for k in contacts if k["prospect"] and k["prospect"]["code"] == "P-1042")
    link = client.get(f"/api/crm/by-prospect/{p1042['prospect']['id']}", headers=h).json()
    assert link["contact_id"] == p1042["id"] and link["stage"] == "cost_review"
    assert client.get(f"/api/crm/by-prospect/{p1042['prospect']['id']}", headers=B).status_code == 404
    cohort = client.get("/api/crm/funnel?since=2026-06-01&until=2026-06-30", headers=h).json()
    assert 0 < cohort["total"] < 41


def test_crm_payloads_never_carry_internal_economics():
    h = SEED
    client.post("/api/crm/demo/seed", headers=h)
    cid = client.get("/api/crm/contacts", headers=h).json()[0]["id"]
    for path in ("/api/crm/contacts", f"/api/crm/contacts/{cid}", "/api/crm/funnel", "/api/crm/meta"):
        ks = keys(client.get(path, headers=h).json())
        assert not [k for k in ks if any(w in k.lower() for w in FORBIDDEN)], path
