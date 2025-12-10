"""
Tests for FastAPI metadata endpoint.
"""

from unittest.mock import Mock

import pytest


class TestMetadataSearch:
    """Tests for metadata search endpoint."""

    def test_search_with_title_and_artist(self, client, mock_metadata_service):
        """Test search with both title and artist."""
        response = client.get("/api/metadata/search?title=Bohemian+Rhapsody&artist=Queen")
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "search_params" in data
        assert data["search_params"]["title"] == "Bohemian Rhapsody"
        assert data["search_params"]["artist"] == "Queen"
        mock_metadata_service.search_metadata.assert_called_once()

    def test_search_with_title_only(self, client, mock_metadata_service):
        """Test search with title only."""
        response = client.get("/api/metadata/search?title=Bohemian+Rhapsody")
        
        assert response.status_code == 200
        mock_metadata_service.search_metadata.assert_called_once_with("", "Bohemian Rhapsody", "", 5)

    def test_search_with_artist_only(self, client, mock_metadata_service):
        """Test search with artist only."""
        response = client.get("/api/metadata/search?artist=Queen")
        
        assert response.status_code == 200
        mock_metadata_service.search_metadata.assert_called_once_with("Queen", "", "", 5)

    def test_search_requires_title_or_artist(self, client):
        """Test that at least title or artist is required."""
        response = client.get("/api/metadata/search")
        
        assert response.status_code == 400
        assert "title" in response.json()["detail"]["error"].lower() or "artist" in response.json()["detail"]["error"].lower()

    def test_search_with_all_parameters(self, client, mock_metadata_service):
        """Test search with all parameters."""
        response = client.get(
            "/api/metadata/search?title=Bohemian+Rhapsody&artist=Queen&album=A+Night+at+the+Opera&limit=10"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["search_params"]["album"] == "A Night at the Opera"
        assert data["search_params"]["limit"] == 10

    def test_search_validates_limit(self, client):
        """Test limit validation."""
        # Too high
        response = client.get("/api/metadata/search?title=test&limit=100")
        assert response.status_code == 422

        # Too low
        response = client.get("/api/metadata/search?title=test&limit=0")
        assert response.status_code == 422

    def test_search_returns_count(self, client, mock_metadata_service):
        """Test that response includes result count."""
        response = client.get("/api/metadata/search?title=test")
        
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["count"] == len(data["results"])

    def test_search_handles_service_error(self, client, mock_metadata_service):
        """Test handling of service errors."""
        mock_metadata_service.search_metadata.side_effect = Exception("iTunes API Error")
        
        response = client.get("/api/metadata/search?title=test")
        
        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()
