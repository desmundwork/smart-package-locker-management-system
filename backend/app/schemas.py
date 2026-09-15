"""API request/response schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models import EventType, LockerStatus, Outcome, Size


class LockerCreate(BaseModel):
    size: Size


class LockerOut(BaseModel):
    id: str
    size: Size
    status: LockerStatus
    created_at: datetime


class NotificationOut(BaseModel):
    id: Optional[int] = None
    ts: datetime
    event_type: EventType
    outcome: Outcome
    locker_id: Optional[str]
    package_id: Optional[str]
    detail: str
