"""Shared test fixtures: in-memory DB, test client."""

import os

os.environ.setdefault("FITNESS_RATE_LIMIT_DISABLED", "1")

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import *  # noqa: F401,F403 – register all models

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(TEST_ENGINE, "connect")
def _set_sqlite_pragma(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSession = sessionmaker(bind=TEST_ENGINE, autoflush=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def db_session():
    """Create tables, yield session, then drop everything."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSession()

    def _override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield session
    session.rollback()
    session.close()
    Base.metadata.drop_all(bind=TEST_ENGINE)
    app.dependency_overrides.clear()


@pytest.fixture
def client(db_session):
    from fastapi.testclient import TestClient
    return TestClient(app)
