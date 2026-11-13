"""SC-11.6: the retention job erases idle prospects and keeps recent ones and those that became clients."""

import os
import tempfile
from datetime import UTC, datetime, timedelta

os.environ.setdefault("PCE_DATA_DIR", tempfile.mkdtemp(prefix="pce-test-"))
os.environ.setdefault("PCE_DATABASE_URL", f"sqlite:///{os.environ['PCE_DATA_DIR']}/t.sqlite")

from sqlalchemy import select

from pce import retention
from pce.crm.models import Contact
from pce.db import AuditEvent, Prospect, make_session_factory


def ago(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat(timespec="seconds")


def test_idle_prospects_are_erased_and_others_kept(tmp_path):
    db = make_session_factory(f"sqlite:///{tmp_path}/r.sqlite")()
    idle = Prospect(tenant_id="r", code="OLD", label="SYNTHETIC", created_at=ago(200))
    active = Prospect(tenant_id="r", code="ACTIVE", label="SYNTHETIC", created_at=ago(200))
    fresh = Prospect(tenant_id="r", code="NEW", label="SYNTHETIC", created_at=ago(5))
    client = Prospect(tenant_id="r", code="WON", label="SYNTHETIC", created_at=ago(200))
    db.add_all([idle, active, fresh, client])
    db.flush()
    db.add(AuditEvent(tenant_id="r", prospect_id=active.id, user="u", action="prospect.opened", at=ago(3)))
    db.add(Contact(tenant_id="r", name="SYNTHETIC", owner="u", stage="won", prospect_id=client.id))
    db.commit()

    assert [r["prospect_id"] for r in retention.run(db, 90, dry_run=True)] == [idle.id]
    assert db.get(Prospect, idle.id) is not None  # dry run changes nothing
    done = retention.run(db, 90, dry_run=False)
    assert [r["prospect_id"] for r in done] == [idle.id]
    assert set(db.scalars(select(Prospect.code))) == {"ACTIVE", "NEW", "WON"}
    erased = db.scalars(select(AuditEvent).where(AuditEvent.action == "prospect.erased")).one()
    assert erased.user == "system.retention" and erased.detail["reason"] == "retention_expired"
