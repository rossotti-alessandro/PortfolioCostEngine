"""SC-10.4: the demo seed must not hold the SQLite write lock while it reads documents.

On Render the seed runs in the background for a minute or two after start; sign-in writes a session row
and used to fail with ``database is locked`` (HTTP 500) for that whole time.
"""

from __future__ import annotations

import threading
import time

from fastapi.testclient import TestClient
from sqlalchemy import text

from pce import api, auth
from pce.api import Ctx, SessionFactory, app

READ_S = 0.3  # stands in for reading one document (OCR takes far longer on Render)


def test_sign_in_succeeds_while_the_demo_seeds(monkeypatch):
    def slow_ingest(db, c, p, name, data):
        time.sleep(READ_S)  # reading happens before anything is written, as in the real ingest
        db.execute(text("UPDATE prospect SET label = label WHERE id = :i"), {"i": p.id})
        db.flush()
        return None, False

    monkeypatch.setattr(api, "ingest", slow_ingest)
    auth.add_account("seedlock", "correct horse battery staple", "seed-lock-firm", ("analyst",))

    def seed() -> None:
        with SessionFactory() as db:
            api.seed_demo(db, Ctx(tenant="seed-lock-firm", user="system.seed", role="senior"))

    t = threading.Thread(target=seed)
    t.start()
    time.sleep(READ_S * 2.5)  # a few documents in: the seed's transaction has written rows
    start = time.monotonic()
    r = TestClient(app).post(
        "/api/auth/login", json={"username": "seedlock", "password": "correct horse battery staple"}
    )
    waited = time.monotonic() - start
    t.join()
    assert r.status_code == 200
    assert waited < READ_S * 3, f"sign-in waited {waited:.1f}s for the seed"
