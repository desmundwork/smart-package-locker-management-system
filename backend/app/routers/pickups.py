"""Package retrieval endpoints (Customer) — requirements 5, 6.

Two-step pickup: open (validate + unlock, package taken) -> close (confirm door
shut, locker available again). Keeps lockers from being reused while open.
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app import services
from app.db import get_session
from app.schemas import CloseRequest, CloseResult, PickupRequest, PickupResult

router = APIRouter(prefix="/api/pickups", tags=["pickups"])


@router.post("/open", response_model=PickupResult)
def open_for_pickup(body: PickupRequest, session: Session = Depends(get_session)) -> PickupResult:
    return services.open_for_pickup(session, body.locker_id, body.pickup_code)


@router.post("/close", response_model=CloseResult)
def close_locker(body: CloseRequest, session: Session = Depends(get_session)) -> CloseResult:
    return services.close_locker(session, body.locker_id)
