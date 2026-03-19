"""
Pytest configuration for integration tests.

Uses FastAPI dependency_overrides to inject a real SQLite test database,
avoiding module cache clearing that pollutes other test suites.
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from unittest.mock import MagicMock

import app.api.host_settings as _host_settings_api
import app.api.jobs as _jobs_api
import app.api.karaoke_queue as _queue_api
import app.api.lyrics as _lyrics_api
import app.api.sessions as _sessions_api
import app.api.songs as _songs_api
from app.api.dependencies import get_current_user, get_db, require_host
from app.db.models import Base
from tests.conftest import create_test_app


def _get_mock_user():
    """Bypass auth for integration tests."""
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "testuser"
    mock_user.is_admin = True
    mock_user.is_host = True
    return mock_user

# Create a single file-based SQLite database for the integration test session
_test_db_fd, _test_db_path = tempfile.mkstemp(suffix=".db")
os.close(_test_db_fd)
_test_db_url = f"sqlite:///{_test_db_path}"

_engine = create_engine(_test_db_url, connect_args={"check_same_thread": False})
Base.metadata.create_all(_engine)
_TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _get_test_db():
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def integration_app():
    """FastAPI app wired to the integration test database."""
    app = create_test_app()
    # Override all local get_db functions (each module defines its own)
    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[_songs_api.get_db] = _get_test_db
    app.dependency_overrides[_jobs_api.get_db] = _get_test_db
    app.dependency_overrides[_queue_api.get_db] = _get_test_db
    app.dependency_overrides[_lyrics_api.get_db] = _get_test_db
    app.dependency_overrides[_sessions_api.get_db] = _get_test_db
    app.dependency_overrides[_host_settings_api.get_db] = _get_test_db
    # Bypass authentication for integration tests
    app.dependency_overrides[get_current_user] = _get_mock_user
    app.dependency_overrides[require_host] = _get_mock_user
    return app


@pytest.fixture(scope="session")
def client(integration_app):
    """Test client for integration tests."""
    with TestClient(integration_app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_tables():
    """Truncate all tables between tests to keep them isolated."""
    yield
    with _engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


def pytest_sessionfinish(session, exitstatus):
    """Clean up test database file after all tests complete."""
    try:
        os.unlink(_test_db_path)
    except Exception:
        pass
