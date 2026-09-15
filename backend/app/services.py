"""Service layer — design §3 and §4.

Business logic lives here; routers stay thin. Grows across milestones:
- create_locker / list_lockers    (requirements 1)
- hold_locker                     (requirements 3, 7 — smallest-fit + atomic claim)
"""
import secrets
import string
from datetime import timedelta

from sqlalchemy import update
from sqlmodel import Session, select

from app.charges import billable_days, storage_charge
from app.config import settings
from app.models import (
    EventType,
    Locker,
    LockerStatus,
    Outcome,
    Package,
    PackageStatus,
    Size,
    as_utc,
    now_utc,
    size_rank,
)
from app.notifier import notifier
from app.schemas import CancelResult, CloseResult, CompleteResult, HoldResult, PickupResult

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


def release_expired_holds(session: Session) -> int:
    """Release HELD lockers whose PENDING package wasn't confirmed in time.

    Run lazily before hold/list so no background thread is needed. Returns the
    number of holds released. The HELD -> AVAILABLE flip is a conditional UPDATE,
    so under concurrent sweeps each expired hold is released exactly once.
    """
    timeout = settings.hold_timeout_seconds
    if timeout <= 0:
        return 0
    cutoff = now_utc() - timedelta(seconds=timeout)
    stale = session.exec(
        select(Package).where(Package.status == PackageStatus.PENDING)
    ).all()
    released = 0
    for pkg in stale:
        if as_utc(pkg.held_at) > cutoff:
            continue
        locker_id = pkg.locker_id
        package_id = pkg.id

        # Atomically flip the locker HELD -> AVAILABLE. rowcount==1 means this
        # sweep won the release; a concurrent sweep that lost sees 0 and skips,
        # so the package is deleted and logged exactly once (safe under Postgres).
        result = session.exec(
            update(Locker)
            .where(Locker.id == locker_id, Locker.status == LockerStatus.HELD)
            .values(status=LockerStatus.AVAILABLE)
        )
        if result.rowcount == 0:
            session.rollback()
            continue

        session.delete(pkg)  # attrs read above; gone after delete
        notifier.record(
            session, EventType.HOLD_EXPIRED, Outcome.SUCCESS,
            f"hold expired after {timeout}s, {locker_id} released",
            locker_id=locker_id, package_id=package_id,
        )
        session.commit()  # commit per-hold so concurrent sweeps see the new state
        released += 1
    return released


def list_lockers(session: Session) -> list[Locker]:
    release_expired_holds(session)
    return list(session.exec(select(Locker).order_by(Locker.id)).all())


def hold_locker(session: Session, size: Size) -> HoldResult:
    """Step 1 of 2: reserve the smallest fitting locker and open its door.

    Atomically claims AVAILABLE -> HELD (this is the concurrency guarantee: two
    agents can never hold the same locker). Creates a PENDING package with the
    pickup code but no stored_at yet — the charge clock only starts on confirm.
    """
    release_expired_holds(session)
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


def open_for_pickup(session: Session, locker_id: str, pickup_code: str) -> PickupResult:
    """Step 1 of 2: validate the code and unlock the locker for the customer.

    The package is removed here, but the locker goes to OPEN (not AVAILABLE) — it
    can't be reused until the customer confirms the door is shut (close_locker),
    so nothing is left physically open. (Storage charge is added in a later step.)
    """
    pkg = session.exec(
        select(Package).where(
            Package.locker_id == locker_id,
            Package.pickup_code == pickup_code,
            Package.status == PackageStatus.STORED,
        )
    ).first()

    if pkg is None:
        notifier.record(
            session, EventType.PICKUP_FAILURE, Outcome.FAILURE,
            f"invalid pickup for locker={locker_id}", locker_id=locker_id,
        )
        session.commit()
        return PickupResult(opened=False, message="That locker number and code don't match. Please check and try again.")

    now = now_utc()
    stored_at = pkg.stored_at
    charge = storage_charge(stored_at, now, settings.storage_unit_rate)
    days = billable_days(stored_at, now)

    pkg.status = PackageStatus.RETRIEVED
    pkg.retrieved_at = now
    pkg.storage_charge = charge
    session.add(pkg)

    locker = session.get(Locker, locker_id)
    if locker is not None:
        locker.status = LockerStatus.OPEN
        session.add(locker)

    notifier.record(
        session, EventType.PICKUP_SUCCESS, Outcome.SUCCESS,
        f"unlocked, package taken, charge={charge}", locker_id=locker_id, package_id=pkg.id,
    )
    session.commit()
    return PickupResult(
        opened=True,
        locker_id=locker_id,
        package_id=pkg.id,
        storage_charge=charge,
        stored_at=stored_at,
        retrieved_at=now,
        billable_days=days,
        message=f"Locker {locker_id} is unlocked. Take your package, then close the door.",
    )


def close_locker(session: Session, locker_id: str) -> CloseResult:
    """Step 2 of 2: the customer confirms the door is shut; free the locker."""
    locker = session.get(Locker, locker_id)
    if locker is None or locker.status != LockerStatus.OPEN:
        session.rollback()
        return CloseResult(closed=False, message="That locker isn't open.")

    locker.status = LockerStatus.AVAILABLE
    session.add(locker)
    notifier.record(
        session, EventType.PICKUP_CLOSED, Outcome.SUCCESS,
        f"{locker_id} closed and available again", locker_id=locker_id,
    )
    session.commit()
    return CloseResult(closed=True, message=f"Locker {locker_id} is closed. Thanks!")
