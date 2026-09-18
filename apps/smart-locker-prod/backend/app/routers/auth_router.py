"""Authentication endpoints — production only.

    POST /api/auth/login  -> exchange username/password for a JWT access token
    GET  /api/auth/me     -> return the current authenticated identity
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlmodel import Session

from app.auth import (
    CurrentUser,
    Role,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from app.config import settings
from app.db import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class MeOut(BaseModel):
    username: str
    role: str


@router.post("/login", response_model=TokenOut)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> TokenOut:
    user = authenticate_user(session, form.username, form.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    role = Role(user.role)
    token = create_access_token(subject=user.username, role=role)
    return TokenOut(access_token=token, role=role.value, username=user.username)


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser = Depends(get_current_user)) -> MeOut:
    return MeOut(username=user.username, role=user.role.value)


class DemoCredential(BaseModel):
    view: str
    role: str
    username: str
    password: str


class DemoCredentialsOut(BaseModel):
    review_mode: bool
    credentials: list[DemoCredential]


# Map each view to its seeded (username, password) from configuration.
def _seed_for(view: str) -> tuple[str, str, Role] | None:
    table = {
        "admin": (settings.seed_admin_username, settings.seed_admin_password, Role.ADMIN),
        "agent": (settings.seed_agent_username, settings.seed_agent_password, Role.AGENT),
        "customer": (
            settings.seed_customer_username,
            settings.seed_customer_password,
            Role.CUSTOMER,
        ),
    }
    return table.get(view)


@router.get("/demo-credentials", response_model=DemoCredentialsOut)
def demo_credentials(view: str | None = None) -> DemoCredentialsOut:
    """Return seeded demo credentials for easy reviewing.

    Only active when REVIEW_MODE is enabled; otherwise returns an empty list so
    the login page shows nothing. This endpoint intentionally exposes seed
    passwords and MUST stay disabled in a real production deployment.

    ``view`` optionally narrows to a single role (admin/agent/customer); omit
    to return all configured seed accounts.
    """
    if not settings.review_mode:
        return DemoCredentialsOut(review_mode=False, credentials=[])

    views = [view] if view in ("admin", "agent", "customer") else ["admin", "agent", "customer"]
    creds: list[DemoCredential] = []
    for v in views:
        seed = _seed_for(v)
        if not seed:
            continue
        username, password, role = seed
        # Only include accounts that were actually seeded (password set).
        if username and password:
            creds.append(
                DemoCredential(view=v, role=role.value, username=username, password=password)
            )
    return DemoCredentialsOut(review_mode=True, credentials=creds)
