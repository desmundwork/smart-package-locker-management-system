"""Idempotent user seeding for production.

Creates the three bootstrap accounts (admin/agent/customer) on startup if they
don't already exist, using hashed passwords from configuration. Skips any role
whose password isn't configured, and never overwrites an existing user.
"""
from sqlmodel import Session, select

from app.auth import Role, hash_password
from app.config import settings
from app.db import engine
from app.models import User


def _ensure_user(session: Session, username: str, password: str, role: Role) -> None:
    if not username or not password:
        return  # role not configured for this deploy; skip.
    existing = session.exec(select(User).where(User.username == username)).first()
    if existing:
        return  # never clobber an existing account.
    session.add(
        User(username=username, password_hash=hash_password(password), role=role.value)
    )


def seed_users() -> None:
    with Session(engine) as session:
        _ensure_user(session, settings.seed_admin_username, settings.seed_admin_password, Role.ADMIN)
        _ensure_user(session, settings.seed_agent_username, settings.seed_agent_password, Role.AGENT)
        _ensure_user(
            session, settings.seed_customer_username, settings.seed_customer_password, Role.CUSTOMER
        )
        session.commit()
