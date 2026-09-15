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


class PackageStore(BaseModel):
    size: Size


class HoldResult(BaseModel):
    held: bool
    package_id: Optional[str] = None
    locker_id: Optional[str] = None
    pickup_code: Optional[str] = None
    message: str


class CompleteRequest(BaseModel):
    package_id: str


class CompleteResult(BaseModel):
    stored: bool
    locker_id: Optional[str] = None
    pickup_code: Optional[str] = None
    package_id: Optional[str] = None
    message: str


class CancelRequest(BaseModel):
    package_id: str


class CancelResult(BaseModel):
    cancelled: bool
    message: str


class NotificationOut(BaseModel):
    id: Optional[int] = None
    ts: datetime
    event_type: EventType
    outcome: Outcome
    locker_id: Optional[str]
    package_id: Optional[str]
    detail: str
