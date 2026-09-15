"""Shared test fixtures: an app bound to a fresh in-memory SQLite DB."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine
from sqlmodel.pool import StaticPool


@pytest.fixture()
def client(monkeypatch):
    # Fresh in-memory DB per test, shared across connections via StaticPool.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import app.db as db

    monkeypatch.setattr(db, "engine", engine)
    SQLModel.metadata.create_all(engine)

    from app.main import app

    with TestClient(app) as c:
        yield c
