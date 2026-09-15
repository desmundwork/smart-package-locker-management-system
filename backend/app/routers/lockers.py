"""Locker management endpoints — requirements 1."""
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app import services
from app.db import get_session
from app.models import Locker, dimensions_for
from app.schemas import DimensionsOut, LockerCreate, LockerOut

router = APIRouter(prefix="/api/lockers", tags=["lockers"])


def _locker_out(locker: Locker) -> LockerOut:
    d = dimensions_for(locker.size)
    return LockerOut(
        **locker.model_dump(),
        dimensions=DimensionsOut(
            width_cm=d.width_cm, depth_cm=d.depth_cm, height_cm=d.height_cm,
            volume_litres=d.volume_litres,
        ),
    )


@router.post("", response_model=LockerOut, status_code=201)
def create_locker(body: LockerCreate, session: Session = Depends(get_session)) -> LockerOut:
    return _locker_out(services.create_locker(session, body.size))


@router.get("", response_model=list[LockerOut])
def list_lockers(session: Session = Depends(get_session)) -> list[LockerOut]:
    return [_locker_out(l) for l in services.list_lockers(session)]
