"""Locker management endpoints — requirements 1."""
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app import services
from app.db import get_session
from app.schemas import LockerCreate, LockerOut

router = APIRouter(prefix="/api/lockers", tags=["lockers"])


@router.post("", response_model=LockerOut, status_code=201)
def create_locker(body: LockerCreate, session: Session = Depends(get_session)) -> LockerOut:
    locker = services.create_locker(session, body.size)
    return LockerOut(**locker.model_dump())


@router.get("", response_model=list[LockerOut])
def list_lockers(session: Session = Depends(get_session)) -> list[LockerOut]:
    return [LockerOut(**l.model_dump()) for l in services.list_lockers(session)]
