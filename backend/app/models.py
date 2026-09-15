"""Domain models (SQLModel) — design §2.

Size ordering SMALL < MEDIUM < LARGE drives the fit rule. New sizes are added
by extending SIZE_ORDER only; allocation logic reads the ordering, not literals.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


def now_utc() -> datetime:
    """Timezone-aware UTC now. Single source so stored/retrieved timestamps
    are always comparable (avoids naive/aware mixing)."""
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    """Normalize a datetime to timezone-aware UTC.

    SQLite reads timestamps back as naive; since everything is stored via
    now_utc() (UTC), a naive value is interpreted as UTC. This is the single
    place any code reconciles naive/aware datetimes so comparisons and
    subtractions are always well-defined.
    """
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


class Size(str, Enum):
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"


# Ordered smallest -> largest. Extension point: append new sizes here.
SIZE_ORDER = [Size.SMALL, Size.MEDIUM, Size.LARGE]


def size_rank(size: Size) -> int:
    return SIZE_ORDER.index(size)


class LockerStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    HELD = "HELD"          # reserved for an agent mid-drop-off (door open, not yet confirmed)
    OCCUPIED = "OCCUPIED"
    OPEN = "OPEN"          # unlocked for a customer pickup, awaiting door-close confirmation


class PackageStatus(str, Enum):
    PENDING = "PENDING"    # locker held, package not yet confirmed stored
    STORED = "STORED"
    RETRIEVED = "RETRIEVED"


class EventType(str, Enum):
    STORE_ATTEMPT = "STORE_ATTEMPT"
    HOLD_SUCCESS = "HOLD_SUCCESS"      # locker reserved, door opened for agent
    HOLD_FAILURE = "HOLD_FAILURE"      # no suitable locker to reserve
    STORE_SUCCESS = "STORE_SUCCESS"    # agent confirmed; package stored, door closed
    STORE_CANCELLED = "STORE_CANCELLED"  # agent backed out; locker released
    HOLD_EXPIRED = "HOLD_EXPIRED"        # hold timed out; locker auto-released
    PICKUP_SUCCESS = "PICKUP_SUCCESS"    # code validated, locker unlocked, package taken
    PICKUP_FAILURE = "PICKUP_FAILURE"
    PICKUP_CLOSED = "PICKUP_CLOSED"      # customer confirmed door shut; locker available
    CODE_SEND = "CODE_SEND"


class Outcome(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class Locker(SQLModel, table=True):
    id: str = Field(primary_key=True)
    size: Size
    status: LockerStatus = Field(default=LockerStatus.AVAILABLE, index=True)
    created_at: datetime = Field(default_factory=now_utc)


class Package(SQLModel, table=True):
    id: str = Field(primary_key=True)
    size: Size
    locker_id: Optional[str] = Field(default=None, foreign_key="locker.id")
    pickup_code: str = Field(index=True, unique=True)
    status: PackageStatus = Field(default=PackageStatus.PENDING, index=True)
    held_at: datetime = Field(default_factory=now_utc)   # when the locker was reserved
    stored_at: Optional[datetime] = None                 # set on confirm; charge clock starts here
    retrieved_at: Optional[datetime] = None
    storage_charge: Optional[float] = None


class NotificationLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=now_utc)
    event_type: EventType
    outcome: Outcome
    locker_id: Optional[str] = None
    package_id: Optional[str] = None
    detail: str = ""
