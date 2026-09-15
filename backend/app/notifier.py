"""Notification subsystem — design §; requirements 8.

`Notifier` is the swappable interface; `LogNotifier` records every event in the
NotificationLog table (the POC has no real SMS/email). Replace with an SMS/email
implementation later without touching callers.
"""
from typing import Optional, Protocol

from sqlmodel import Session

from app.models import EventType, NotificationLog, Outcome


class Notifier(Protocol):
    def record(
        self,
        session: Session,
        event_type: EventType,
        outcome: Outcome,
        detail: str = "",
        locker_id: Optional[str] = None,
        package_id: Optional[str] = None,
    ) -> None: ...


class LogNotifier:
    def record(
        self,
        session: Session,
        event_type: EventType,
        outcome: Outcome,
        detail: str = "",
        locker_id: Optional[str] = None,
        package_id: Optional[str] = None,
    ) -> None:
        session.add(
            NotificationLog(
                event_type=event_type,
                outcome=outcome,
                detail=detail,
                locker_id=locker_id,
                package_id=package_id,
            )
        )


notifier: Notifier = LogNotifier()
