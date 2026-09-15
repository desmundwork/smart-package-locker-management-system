"""Hold expiry — a HELD locker not confirmed in time is auto-released."""
from datetime import timedelta

from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

import app.config as config
from app.models import (
    EventType,
    Locker,
    LockerStatus,
    NotificationLog,
    Package,
    Size,
    now_utc,
)
from app.services import complete_store, hold_locker, list_lockers, release_expired_holds


def _engine():
    e = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(e)
    return e


def test_expired_hold_is_released(monkeypatch):
    monkeypatch.setattr(config.settings, "hold_timeout_seconds", 60)
    engine = _engine()
    with Session(engine) as s:
        s.add(Locker(id="M-001", size=Size.MEDIUM, status=LockerStatus.AVAILABLE))
        s.commit()

        hold = hold_locker(s, Size.SMALL)
        assert hold.held is True
        assert s.get(Locker, "M-001").status == LockerStatus.HELD

        # Backdate the hold beyond the timeout.
        pkg = s.get(Package, hold.package_id)
        pkg.held_at = now_utc() - timedelta(seconds=120)
        s.add(pkg)
        s.commit()

        released = release_expired_holds(s)
        assert released == 1
        assert s.get(Locker, "M-001").status == LockerStatus.AVAILABLE
        assert s.get(Package, hold.package_id) is None

        # The expiry log records the released locker and the (now-deleted) package id.
        row = s.exec(
            select(NotificationLog).where(NotificationLog.event_type == EventType.HOLD_EXPIRED)
        ).one()
        assert row.locker_id == "M-001"
        assert row.package_id == hold.package_id


def test_confirming_expired_hold_fails(monkeypatch):
    monkeypatch.setattr(config.settings, "hold_timeout_seconds", 60)
    engine = _engine()
    with Session(engine) as s:
        s.add(Locker(id="M-001", size=Size.MEDIUM, status=LockerStatus.AVAILABLE))
        s.commit()
        hold = hold_locker(s, Size.SMALL)
        pkg = s.get(Package, hold.package_id)
        pkg.held_at = now_utc() - timedelta(seconds=120)
        s.add(pkg)
        s.commit()
        list_lockers(s)  # triggers the sweep

        result = complete_store(s, hold.package_id)
        assert result.stored is False


def test_fresh_hold_not_released(monkeypatch):
    monkeypatch.setattr(config.settings, "hold_timeout_seconds", 60)
    engine = _engine()
    with Session(engine) as s:
        s.add(Locker(id="M-001", size=Size.MEDIUM, status=LockerStatus.AVAILABLE))
        s.commit()
        hold = hold_locker(s, Size.SMALL)
        assert release_expired_holds(s) == 0
        assert s.get(Locker, "M-001").status == LockerStatus.HELD
        _ = hold


def test_timeout_zero_disables_expiry(monkeypatch):
    monkeypatch.setattr(config.settings, "hold_timeout_seconds", 0)
    engine = _engine()
    with Session(engine) as s:
        s.add(Locker(id="M-001", size=Size.MEDIUM, status=LockerStatus.AVAILABLE))
        s.commit()
        hold = hold_locker(s, Size.SMALL)
        pkg = s.get(Package, hold.package_id)
        pkg.held_at = now_utc() - timedelta(days=99)
        s.add(pkg)
        s.commit()
        assert release_expired_holds(s) == 0
