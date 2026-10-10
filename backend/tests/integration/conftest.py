"""
Pytest configuration for integration tests.

Endpoints run against the shared throwaway database set up in tests/conftest.py,
so tests can seed and inspect data with app.db.database.SessionLocal directly.
Only authentication is overridden here.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from tests.conftest import create_test_app

from app.api.dependencies import (
    RequesterContext,
    get_current_user,
    require_admin,
    require_host,
    require_host_or_session_member,
)


def _get_mock_user():
    """Bypass auth for integration tests."""
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "testuser"
    mock_user.is_admin = True
    mock_user.is_host = True
    # Explicit: a MagicMock attribute would otherwise be truthy and trip
    # demo-account guards (e.g. host-settings updates return 403).
    mock_user.is_demo = False
    return mock_user


def _get_mock_requester():
    """Bypass the host-or-session-member gate for integration tests."""
    return RequesterContext(user=_get_mock_user())


@pytest.fixture(scope="session")
def integration_app():
    """FastAPI app with authentication bypassed."""
    app = create_test_app()
    app.dependency_overrides[get_current_user] = _get_mock_user
    app.dependency_overrides[require_host] = _get_mock_user
    app.dependency_overrides[require_admin] = _get_mock_user
    app.dependency_overrides[require_host_or_session_member] = _get_mock_requester
    return app


@pytest.fixture(scope="session")
def client(integration_app):
    """Test client for integration tests."""
    with TestClient(integration_app) as c:
        yield c


@pytest.fixture(scope="session")
def unauthenticated_app():
    """FastAPI app with *no* auth bypass.

    Used to prove that deliberately public routes stay reachable without an
    Authorization header. Routes guarded by HTTPBearer will 401 here.
    """
    return create_test_app()


@pytest.fixture(scope="session")
def unauthenticated_client(unauthenticated_app):
    """Test client that sends no credentials."""
    with TestClient(unauthenticated_app) as c:
        yield c
