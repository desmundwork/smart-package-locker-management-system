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
