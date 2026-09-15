"""Smoke tests for the data model and DB layer."""
from datetime import datetime, timezone

from sqlmodel import Session, select

import app.db as db
from app.models import Locker, LockerStatus, Size, SIZE_ORDER, as_utc, now_utc, size_rank


def test_size_ordering():
    assert [size_rank(s) for s in SIZE_ORDER] == [0, 1, 2]
    assert size_rank(Size.SMALL) < size_rank(Size.MEDIUM) < size_rank(Size.LARGE)


def test_now_utc_is_aware():
    assert now_utc().tzinfo is not None


def test_as_utc_normalizes_naive_and_aware():
    naive = datetime(2026, 1, 1, 12, 0, 0)
    aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert as_utc(naive) == aware
    assert as_utc(aware) == aware


def test_locker_persists_with_defaults(client):
    # client fixture patches db.engine to a fresh in-memory DB and creates tables.
    with Session(db.engine) as s:
        s.add(Locker(id="S-001", size=Size.SMALL))
        s.commit()
        row = s.exec(select(Locker)).one()
    assert row.id == "S-001"
    assert row.status == LockerStatus.AVAILABLE  # default
    assert row.created_at is not None
