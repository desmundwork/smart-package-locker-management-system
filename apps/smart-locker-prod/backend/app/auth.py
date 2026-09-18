"""Authentication & authorization for the production deployment.

Adds JWT-based auth and role-based access control on top of the POC's
business logic. Three roles map to the three operator views:

    ADMIN    -> manage lockers, view all transactions
    AGENT    -> store packages (hold / complete / cancel)
    CUSTOMER -> pick up packages (open / close)

Design notes:
- Passwords are hashed with bcrypt (never stored in plaintext).
- Access tokens are short-lived JWTs (HS256) carrying the subject (username)
  and role claim. Stateless verification keeps the API horizontally scalable.
- Users are stored in the DB (see models.User) and seeded on startup from
  env-configured bootstrap credentials so a fresh deploy is usable but not
  hardcoded to insecure defaults in code.
"""
from __future__ import annotations

from datetime import timedelta
from enum import Enum
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlmodel import Session, select

from app.config import settings
from app.db import get_session
from app.models import User, now_utc

# bcrypt via passlib. Auto-selects the configured scheme on verify.
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token endpoint used by OpenAPI's "Authorize" button and clients.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class Role(str, Enum):
    ADMIN = "ADMIN"
    AGENT = "AGENT"
    CUSTOMER = "CUSTOMER"


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_access_token(*, subject: str, role: Role) -> str:
    """Issue a signed JWT with subject + role and an expiry."""
    expire = now_utc() + timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {"sub": subject, "role": role.value, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def authenticate_user(session: Session, username: str, password: str) -> Optional[User]:
    user = session.exec(select(User).where(User.username == username)).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


class CurrentUser:
    """Resolved identity attached to a request after token verification."""

    def __init__(self, username: str, role: Role) -> None:
        self.username = username
        self.role = role


def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        username = payload.get("sub")
        role_raw = payload.get("role")
        if username is None or role_raw is None:
            raise credentials_exc
        role = Role(role_raw)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exc
    return CurrentUser(username=username, role=role)


def require_role(*allowed: Role):
    """Dependency factory enforcing that the caller holds one of ``allowed``.

    Usage:
        @router.post(..., dependencies=[Depends(require_role(Role.ADMIN))])
    """

    def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role in {[r.value for r in allowed]}",
            )
        return user

    return _checker
