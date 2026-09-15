"""Concurrent expiry sweeps must release each stale hold exactly once.

Two agents hitting /hold as a hold expires both trigger release_expired_holds.
The atomic HELD -> AVAILABLE claim guarantees only one sweep releases the hold,
so we never get duplicate HOLD_EXPIRED logs or a double-freed locker.
"""
import concurrent.futures
import tempfile
from datetime import timedelta
from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

import app.config as config
from app.models import EventType, Locker, LockerStatus, NotificationLog, Package, Size, now_utc
from app.services import hold_locker, release_expired_holds


def _make_engine(tmp_path: Path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'release.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()

    return engine


def test_concurrent_sweeps_release_each_hold_once(monkeypatch):
    monkeypatch.setattr(config.settings, "hold_timeout_seconds", 60)
    tmp = Path(tempfile.mkdtemp())
    engine = _make_engine(tmp)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as s:
        s.add(Locker(id="M-001", size=Size.MEDIUM, status=LockerStatus.AVAILABLE))
        s.commit()
        hold = hold_locker(s, Size.SMALL)
        pkg = s.get(Package, hold.package_id)
        pkg.held_at = now_utc() - timedelta(seconds=120)
        s.add(pkg)
        s.commit()

    def sweep():
        with Session(engine) as session:
            return release_expired_holds(session)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        counts = [f.result() for f in [ex.submit(sweep) for _ in range(8)]]

    assert sum(counts) == 1  # exactly one sweep released the hold

    with Session(engine) as s:
        assert s.get(Locker, "M-001").status == LockerStatus.AVAILABLE
        assert s.get(Package, hold.package_id) is None
        logs = s.exec(
            select(NotificationLog).where(NotificationLog.event_type == EventType.HOLD_EXPIRED)
        ).all()
        assert len(logs) == 1
