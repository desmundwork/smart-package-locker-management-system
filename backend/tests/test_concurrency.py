"""Concurrency safety — requirements 7 (Level 4).

Fire N concurrent store requests at M<N available lockers. Assert exactly M
succeed, each with a distinct locker, and the rest get "no locker".
"""
import concurrent.futures
import tempfile
from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.models import Locker, LockerStatus, Size
from app.services import hold_locker


def _make_engine(tmp_path: Path):
    # File-based SQLite so each thread gets its own connection (realistic model).
    # busy_timeout makes concurrent writers wait for the lock instead of erroring.
    engine = create_engine(
        f"sqlite:///{tmp_path / 'conc.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()

    return engine


def test_no_double_assignment_under_concurrency():
    tmp = Path(tempfile.mkdtemp())
    engine = _make_engine(tmp)
    SQLModel.metadata.create_all(engine)

    M = 5   # available lockers
    N = 20  # concurrent requests
    with Session(engine) as s:
        for i in range(M):
            s.add(Locker(id=f"L-{i+1:03d}", size=Size.MEDIUM, status=LockerStatus.AVAILABLE))
        s.commit()

    def worker():
        with Session(engine) as session:
            return hold_locker(session, Size.SMALL)

    with concurrent.futures.ThreadPoolExecutor(max_workers=N) as ex:
        results = [f.result() for f in [ex.submit(worker) for _ in range(N)]]

    held = [r for r in results if r.held]
    failed = [r for r in results if not r.held]

    assert len(held) == M
    assert len(failed) == N - M
    # Every successful hold got a distinct locker.
    locker_ids = [r.locker_id for r in held]
    assert len(set(locker_ids)) == M
