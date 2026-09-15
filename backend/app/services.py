"""Service layer — design §3 and §4.

Business logic lives here; routers stay thin. Grows across milestones:
- create_locker / list_lockers    (requirements 1)
"""
from sqlmodel import Session, select

from app.models import Locker, Size

_SIZE_PREFIX = {Size.SMALL: "S", Size.MEDIUM: "M", Size.LARGE: "L"}


def _next_locker_id(session: Session, size: Size) -> str:
    # Number sequentially within each size so IDs aren't jumbled across sizes:
    # S-001, M-001, L-001, S-002, ...
    prefix = _SIZE_PREFIX[size]
    count = len(session.exec(select(Locker.id).where(Locker.size == size)).all())
    return f"{prefix}-{count + 1:03d}"


def create_locker(session: Session, size: Size) -> Locker:
    locker = Locker(id=_next_locker_id(session, size), size=size)
    session.add(locker)
    session.commit()
    session.refresh(locker)
    return locker


def list_lockers(session: Session) -> list[Locker]:
    return list(session.exec(select(Locker).order_by(Locker.id)).all())
