"""
Integration test fixtures for FastAPI.

These fixtures ensure integration tests use the FastAPI TestClient,
not the pytest-flask client.
"""

import pytest
from fastapi.testclient import TestClient

# Import from tests/conftest.py
from tests.conftest import create_test_app


@pytest.fixture(scope="module")
def fastapi_app():
    """Create FastAPI application for integration testing."""
    return create_test_app()


@pytest.fixture(scope="module")
def client(fastapi_app):
    """
    Create FastAPI test client for integration tests.
    
    This overrides any pytest-flask fixtures to ensure we use httpx TestClient.
    """
    with TestClient(fastapi_app) as test_client:
        yield test_client
