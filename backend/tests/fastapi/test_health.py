"""
Tests for FastAPI health endpoint.
"""

import pytest


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_returns_ok(self, client):
        """Test health endpoint returns OK status."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["framework"] == "fastapi"

    def test_health_includes_timestamp(self, client):
        """Test health endpoint includes timestamp."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data

    def test_health_includes_response_time(self, client):
        """Test health endpoint includes response time."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "response_time_ms" in data
        assert isinstance(data["response_time_ms"], (int, float))


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_api_info(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "api_endpoints" in data

    def test_root_lists_all_endpoints(self, client):
        """Test root endpoint lists all API endpoints."""
        response = client.get("/")
        
        assert response.status_code == 200
        endpoints = response.json()["api_endpoints"]
        
        # Check that all migrated endpoints are listed
        assert "songs" in endpoints
        assert "jobs" in endpoints
        assert "sessions" in endpoints
        assert "queue" in endpoints
        assert "youtube" in endpoints
        assert "youtube_music" in endpoints
        assert "metadata" in endpoints
        assert "lyrics" in endpoints
        assert "users" in endpoints

    def test_root_lists_websockets(self, client):
        """Test root endpoint lists WebSocket endpoints."""
        response = client.get("/")
        
        assert response.status_code == 200
        websockets = response.json()["websockets"]
        
        assert "jobs" in websockets
        assert "session" in websockets
