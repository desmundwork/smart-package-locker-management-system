"""Service layer — design §3 and §4.

Business logic lives here; routers stay thin. Grows across milestones:
- create_locker / list_lockers    (requirements 1)
- hold_locker                     (requirements 3, 7 — smallest-fit + atomic claim)
"""
import secrets
import string

from sqlalchemy import update
from sqlmodel import Session, select

from app.models import (
    EventType,
    Locker,
    LockerStatus,
    Outcome,
    Package,
    PackageStatus,
    Size,
    now_utc,
    size_rank,
)
from app.notifier import notifier
from app.schemas import CancelResult, CompleteResult, HoldResult

_CODE_ALPHABET = string.ascii_uppercase + string.digits


def _new_pickup_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))


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


def hold_locker(session: Session, size: Size) -> HoldResult:
    """Step 1 of 2: reserve the smallest fitting locker and open its door.

    Atomically claims AVAILABLE -> HELD (this is the concurrency guarantee: two
    agents can never hold the same locker). Creates a PENDING package with the
    pickup code but no stored_at yet — the charge clock only starts on confirm.
    """
    notifier.record(session, EventType.STORE_ATTEMPT, Outcome.SUCCESS, f"size={size.value}")

    while True:
        candidates = session.exec(
            select(Locker).where(Locker.status == LockerStatus.AVAILABLE)
        ).all()
        candidates = sorted(
            (l for l in candidates if size_rank(l.size) >= size_rank(size)),
            key=lambda l: (size_rank(l.size), l.id),
        )
        if not candidates:
            notifier.record(
                session, EventType.HOLD_FAILURE, Outcome.FAILURE, f"no locker fits size={size.value}"
            )
            session.commit()
            return HoldResult(held=False, message="Sorry, no locker is free for this size right now.")

        target = candidates[0]
        result = session.exec(
            update(Locker)
            .where(Locker.id == target.id, Locker.status == LockerStatus.AVAILABLE)
            .values(status=LockerStatus.HELD)
        )
        if result.rowcount == 0:
            session.rollback()
            continue  # lost the race; try the next candidate

        pkg = Package(
            id=f"P-{secrets.token_hex(4)}",
            size=size,
            locker_id=target.id,
            pickup_code=_new_pickup_code(),
            status=PackageStatus.PENDING,
            held_at=now_utc(),
        )
        session.add(pkg)
        notifier.record(
            session, EventType.HOLD_SUCCESS, Outcome.SUCCESS,
            f"locker {target.id} held, door open", locker_id=target.id, package_id=pkg.id,
        )
        session.commit()
        return HoldResult(
            held=True,
            package_id=pkg.id,
            locker_id=target.id,
            pickup_code=pkg.pickup_code,
            message=f"Locker {target.id} is open. Place the package inside, then confirm.",
        )


def complete_store(session: Session, package_id: str) -> CompleteResult:
    """Step 2 of 2: the agent confirms the package is inside; close and store."""
    pkg = session.get(Package, package_id)
    if pkg is None or pkg.status != PackageStatus.PENDING:
        session.rollback()
        return CompleteResult(stored=False, message="Nothing to confirm for that package.")

    now = now_utc()
    pkg.status = PackageStatus.STORED
    pkg.stored_at = now  # charge clock starts now
    session.add(pkg)

    locker = session.get(Locker, pkg.locker_id)
    if locker is not None:
        locker.status = LockerStatus.OCCUPIED
        session.add(locker)

    notifier.record(
        session, EventType.STORE_SUCCESS, Outcome.SUCCESS,
        f"stored in {pkg.locker_id}, door closed", locker_id=pkg.locker_id, package_id=pkg.id,
    )
    notifier.record(
        session, EventType.CODE_SEND, Outcome.SUCCESS,
        "pickup code sent to customer (simulated)", locker_id=pkg.locker_id, package_id=pkg.id,
    )
    session.commit()
    return CompleteResult(
        stored=True,
        locker_id=pkg.locker_id,
        pickup_code=pkg.pickup_code,
        package_id=pkg.id,
        message=f"All done. Package stored in {pkg.locker_id} and the pickup code is on its way to the customer.",
    )


def cancel_hold(session: Session, package_id: str) -> CancelResult:
    """Agent backs out before confirming: discard the pending package, free the locker."""
    pkg = session.get(Package, package_id)
    if pkg is None or pkg.status != PackageStatus.PENDING:
        session.rollback()
        return CancelResult(cancelled=False, message="Nothing to cancel for that package.")

    locker = session.get(Locker, pkg.locker_id)
    locker_id = pkg.locker_id
    session.delete(pkg)
    if locker is not None:
        locker.status = LockerStatus.AVAILABLE
        session.add(locker)

    notifier.record(
        session, EventType.STORE_CANCELLED, Outcome.SUCCESS,
        f"hold released, {locker_id} available again", locker_id=locker_id, package_id=package_id,
    )
    session.commit()
    return CancelResult(cancelled=True, message=f"Cancelled. Locker {locker_id} is free again.")
