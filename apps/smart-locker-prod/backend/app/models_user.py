"""User model overlay for production auth.

Appended to the POC's models module (the build concatenates this into
app/models.py) so SQLModel.metadata picks up the User table alongside the
existing Locker/Package/NotificationLog tables and init_db() creates it.
"""
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """An operator account. Role governs which endpoints are permitted."""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    role: str  # "ADMIN" | "AGENT" | "CUSTOMER" (validated via auth.Role)
