"""Package storage endpoints (Delivery Agent) — requirements 3, 7.

Two-step store: hold (reserve locker, open door) -> complete (confirm stored)
or cancel (release the hold).
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app import services
from app.db import get_session
from app.schemas import HoldResult, PackageStore

router = APIRouter(prefix="/api/packages", tags=["packages"])


@router.post("/hold", response_model=HoldResult)
def hold_locker(body: PackageStore, session: Session = Depends(get_session)) -> HoldResult:
    return services.hold_locker(session, body.size)
