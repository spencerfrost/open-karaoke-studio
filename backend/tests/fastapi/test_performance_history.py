"""Tests for performance history endpoint."""
import pytest


class TestPerformanceHistoryEndpoint:
    def test_get_performance_history_returns_ok(self, client):
        response = client.get("/api/performance-history")
        assert response.status_code == 200

    def test_get_performance_history_response_shape(self, client):
        response = client.get("/api/performance-history")
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

    def test_get_performance_history_default_pagination(self, client):
        response = client.get("/api/performance-history")
        data = response.json()
        assert data["limit"] == 50
        assert data["offset"] == 0

    def test_get_performance_history_custom_pagination(self, client):
        response = client.get("/api/performance-history?limit=10&offset=5")
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 5

    def test_get_performance_history_empty_initially(self, client):
        response = client.get("/api/performance-history")
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
