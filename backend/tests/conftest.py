"""Shared fixtures for backend tests.

Uses shared in-memory SQLite to isolate tests from the development database.
"""

import atexit
import os
import tempfile
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from backend.database import Base, get_db
from backend.main import app

# Use a temp file for the test database so all connections share the same data
_db_fd, _db_path = tempfile.mkstemp(suffix=".test.db")
atexit.register(os.unlink, _db_path)
_test_engine = create_engine(f"sqlite:///{_db_path}", connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


def _get_test_db() -> Generator[Session, Any, None]:
    """Override for FastAPI get_db dependency — shares the test engine."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _get_test_db


@pytest.fixture(autouse=True)
def _test_db():
    """Create tables before each test, drop after, clean up temp file on exit."""
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture
def client() -> Generator[TestClient, Any, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session() -> Generator[Session, Any, None]:
    """Direct SQLAlchemy session for test data setup/verification."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
