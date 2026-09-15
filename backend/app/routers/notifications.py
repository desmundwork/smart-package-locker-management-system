"""Transaction log endpoint (Admin) — requirements 8."""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.models import NotificationLog
from app.schemas import NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    limit: int = 200, session: Session = Depends(get_session)
) -> list[NotificationOut]:
    rows = session.exec(
        select(NotificationLog).order_by(NotificationLog.id.desc()).limit(limit)
    ).all()
    return [NotificationOut(**r.model_dump()) for r in rows]
