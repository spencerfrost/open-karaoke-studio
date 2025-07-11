# backend/tests/unit/test_api/test_metadata_endpoints.py
"""
Unit tests for Metadata API endpoints
"""

from unittest.mock import Mock, patch

import pytest
from app.api.metadata import metadata_bp
from flask import Flask


@pytest.fixture
def app():
    """Create a test Flask app"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(metadata_bp)
    return app


@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()


class TestMetadataEndpoints:

    @patch("app.api.metadata.MetadataService")
    def test_search_endpoint_success(self, mock_metadata_service_class, client):
        """Test successful metadata search"""
        # Mock the service instance and its methods
        mock_service = Mock()
        mock_metadata_service_class.return_value = mock_service

        mock_service.search_metadata.return_value = [
            {
                "id": "12345",
                "title": "Test Song",
                "artist": "Test Artist",
                "album": "Test Album",
                "releaseDateFormatted": "2023-01-01",
                "releaseYear": 2023,
                "genre": "Rock",
                "durationSeconds": 210,
                "trackNumber": 1,
                "previewUrl": "http://example.com/preview.mp3",
                "artworkUrl100": "http://example.com/artwork.jpg",
                "isStreamable": True,
            }
        ]

        mock_service.format_metadata_response.return_value = {
            "results": [
                {
                    "metadataId": "12345",
                    "title": "Test Song",
                    "artist": "Test Artist",
                    "album": "Test Album",
                    "releaseDate": "2023-01-01",
                    "releaseYear": 2023,
                    "genre": "Rock",
                    "duration": 210,
                    "trackNumber": 1,
                    "previewUrl": "http://example.com/preview.mp3",
                    "artworkUrl": "http://example.com/artwork.jpg",
                    "isStreamable": True,
                    "artistId": None,
                    "albumId": None,
                    "discNumber": None,
                    "explicit": False,
                    "country": "",
                    "price": None,
                }
            ],
            "search": {
                "artist": "Test Artist",
                "title": "Test Song",
                "album": "",
                "limit": 5,
                "sort_by": "relevance",
            },
            "count": 1,
            "success": True,
        }

        response = client.get("/api/metadata/search?artist=Test Artist&title=Test Song")

        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["title"] == "Test Song"
        assert data["results"][0]["artist"] == "Test Artist"
        assert data["success"] == True

        # Verify service was called correctly
        mock_service.search_metadata.assert_called_once_with(
            "Test Artist", "Test Song", "", 5
        )

    @patch("app.api.metadata.MetadataService")
    def test_search_endpoint_with_album(self, mock_metadata_service_class, client):
        """Test metadata search with album parameter"""
        # Mock the service instance and its methods
        mock_service = Mock()
        mock_metadata_service_class.return_value = mock_service

        mock_service.search_metadata.return_value = []
        mock_service.format_metadata_response.return_value = {
            "results": [],
            "search": {
                "artist": "Test Artist",
                "title": "Test Song",
                "album": "Test Album",
                "limit": 5,
                "sort_by": "relevance",
            },
            "count": 0,
            "success": True,
        }

        response = client.get(
            "/api/metadata/search?artist=Test Artist&title=Test Song&album=Test Album"
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["results"] == []
        assert data["count"] == 0

        # Verify service was called with album parameter
        mock_service.search_metadata.assert_called_once_with(
            "Test Artist", "Test Song", "Test Album", 5
        )

    @patch("app.api.metadata.MetadataService")
    def test_search_endpoint_empty_results(self, mock_metadata_service_class, client):
        """Test metadata search returning empty results"""
        # Mock the service instance and its methods
        mock_service = Mock()
        mock_metadata_service_class.return_value = mock_service

        mock_service.search_metadata.return_value = []
        mock_service.format_metadata_response.return_value = {
            "results": [],
            "search": {
                "artist": "Unknown Artist",
                "title": "Unknown Song",
                "album": "",
                "limit": 5,
                "sort_by": "relevance",
            },
            "count": 0,
            "success": True,
        }

        response = client.get(
            "/api/metadata/search?artist=Unknown Artist&title=Unknown Song"
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["results"] == []
        assert data["count"] == 0

    @patch("app.api.metadata.MetadataService")
    def test_search_endpoint_validation_error(
        self, mock_metadata_service_class, client
    ):
        """Test metadata search with validation error"""
        # Mock the service instance and its methods
        mock_service = Mock()
        mock_metadata_service_class.return_value = mock_service
        mock_service.search_metadata.side_effect = ValueError(
            "Invalid search parameters"
        )

        response = client.get("/api/metadata/search?artist=Test Artist&title=Test Song")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "Invalid search parameters" in data["error"]

    @patch("app.api.metadata.MetadataService")
    def test_search_endpoint_server_error(self, mock_metadata_service_class, client):
        """Test metadata search with internal server error"""
        # Mock the service instance and its methods
        mock_service = Mock()
        mock_metadata_service_class.return_value = mock_service
        mock_service.search_metadata.side_effect = Exception(
            "Network connection failed"
        )

        response = client.get("/api/metadata/search?artist=Test Artist&title=Test Song")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data
        assert "internal error occurred" in data["error"]

    def test_search_endpoint_missing_required_params(self, client):
        """Test metadata search with missing required parameters"""
        # Missing both title and artist
        response = client.get("/api/metadata/search")
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert (
            "At least one of 'title' or 'artist' parameters is required"
            in data["error"]
        )

        # Only album provided (should fail)
        response = client.get("/api/metadata/search?album=Test Album")
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert (
            "At least one of 'title' or 'artist' parameters is required"
            in data["error"]
        )

    @patch("app.api.metadata.MetadataService")
    def test_search_endpoint_with_limit(self, mock_metadata_service_class, client):
        """Test metadata search with custom limit parameter"""
        # Mock the service instance and its methods
        mock_service = Mock()
        mock_metadata_service_class.return_value = mock_service

        mock_service.search_metadata.return_value = []
        mock_service.format_metadata_response.return_value = {
            "results": [],
            "search": {
                "artist": "Test Artist",
                "title": "Test Song",
                "album": "",
                "limit": 10,
                "sort_by": "relevance",
            },
            "count": 0,
            "success": True,
        }

        response = client.get(
            "/api/metadata/search?artist=Test Artist&title=Test Song&limit=10"
        )

        assert response.status_code == 200

        # Verify service was called with custom limit
        mock_service.search_metadata.assert_called_once_with(
            "Test Artist", "Test Song", "", 10
        )

    @patch("app.api.metadata.MetadataService")
    def test_search_endpoint_with_sort_by_param(
        self, mock_metadata_service_class, client
    ):
        """Test metadata search with sort_by parameter (backwards compatibility)"""
        # Mock the service instance and its methods
        mock_service = Mock()
        mock_metadata_service_class.return_value = mock_service

        mock_service.search_metadata.return_value = []
        mock_service.format_metadata_response.return_value = {
            "results": [],
            "search": {
                "artist": "Test Artist",
                "title": "Test Song",
                "album": "",
                "limit": 5,
                "sort_by": "date_desc",
            },
            "count": 0,
            "success": True,
        }

        response = client.get(
            "/api/metadata/search?artist=Test Artist&title=Test Song&sort_by=date_desc"
        )

        assert response.status_code == 200
        data = response.get_json()

        # Verify the sort_by parameter is included in search params for backwards compatibility
        assert data["search"]["sort_by"] == "date_desc"

        # Verify service was called (sort_by doesn't affect service call since iTunes naturally sorts)
        mock_service.search_metadata.assert_called_once_with(
            "Test Artist", "Test Song", "", 5
        )
