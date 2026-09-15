"""Notification subsystem — LogNotifier writes rows; endpoint returns newest first."""
from sqlmodel import Session

import app.db as db
from app.models import EventType, Outcome
from app.notifier import notifier


def test_records_and_lists_newest_first(client):
    with Session(db.engine) as s:
        notifier.record(s, EventType.STORE_ATTEMPT, Outcome.SUCCESS, "first", locker_id="S-001")
        notifier.record(s, EventType.HOLD_SUCCESS, Outcome.SUCCESS, "second", locker_id="S-001", package_id="P-1")
        s.commit()

    rows = client.get("/api/notifications").json()
    assert len(rows) == 2
    # Newest first (higher id first).
    assert rows[0]["event_type"] == "HOLD_SUCCESS"
    assert rows[0]["detail"] == "second"
    assert rows[0]["package_id"] == "P-1"
    assert rows[1]["event_type"] == "STORE_ATTEMPT"


def test_empty_log(client):
    assert client.get("/api/notifications").json() == []


def test_limit_param(client):
    with Session(db.engine) as s:
        for i in range(5):
            notifier.record(s, EventType.STORE_ATTEMPT, Outcome.SUCCESS, f"n{i}")
        s.commit()
    rows = client.get("/api/notifications?limit=2").json()
    assert len(rows) == 2
