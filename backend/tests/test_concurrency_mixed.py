"""Level 4 concurrency across mixed locker sizes — requirements 7.5.

With more concurrent requests than lockers, only the available lockers are
assigned (each to exactly one request, all distinct), and surplus requests get
the "no locker" message. Requests span sizes, so contention crosses size
boundaries (a SMALL package may claim a larger locker under smallest-fit).
"""
import concurrent.futures
import tempfile
from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Locker, LockerStatus, Size
from app.services import hold_locker


def _make_engine(tmp_path: Path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'mixed.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()

    return engine


def test_mixed_size_no_double_assignment():
    tmp = Path(tempfile.mkdtemp())
    engine = _make_engine(tmp)
    SQLModel.metadata.create_all(engine)

    # 2 of each size = 6 lockers total.
    with Session(engine) as s:
        for size in (Size.SMALL, Size.MEDIUM, Size.LARGE):
            for i in range(2):
                s.add(Locker(id=f"{size.value[0]}-{i+1:03d}", size=size, status=LockerStatus.AVAILABLE))
        s.commit()

    request_sizes = [Size.SMALL, Size.MEDIUM, Size.LARGE] * 10  # 30 requests

    def worker(size):
        with Session(engine) as session:
            return hold_locker(session, size)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(request_sizes)) as ex:
        results = [f.result() for f in [ex.submit(worker, s) for s in request_sizes]]

    held = [r for r in results if r.held]
    failed = [r for r in results if not r.held]

    assert len(held) == 6
    assert len(failed) == len(request_sizes) - 6
    assert all("no locker" in r.message.lower() for r in failed)

    # Every assignment is a distinct locker.
    assert len({r.locker_id for r in held}) == 6

    # Availability is correct and up to date: no locker left available.
    with Session(engine) as s:
        available = s.exec(select(Locker).where(Locker.status == LockerStatus.AVAILABLE)).all()
        assert list(available) == []
