"""
Unit tests for the lyrics service.
"""

from unittest.mock import Mock, patch

import pytest
import requests
from app.exceptions import ServiceError
from app.services.lyrics_service import LyricsService


class TestLyricsService:
    """Test suite for LyricsService class."""

    @pytest.fixture
    def lyrics_service(self):
        """Create a LyricsService instance for testing."""
        return LyricsService()

    @pytest.fixture
    def sample_lyrics_data(self):
        """Sample lyrics data for testing."""
        return {
            "id": 12345,
            "trackName": "Test Song",
            "artistName": "Test Artist",
            "albumName": "Test Album",
            "duration": 180.5,
            "plainLyrics": "Line 1\nLine 2\nLine 3",
            "syncedLyrics": "[00:00.00] Line 1\n[00:03.50] Line 2\n[00:07.00] Line 3",
        }

    @patch("app.services.lyrics_service.requests.get")
    def test_search_lyrics_success(self, mock_get, lyrics_service, sample_lyrics_data):
        """Test successful lyrics search."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [sample_lyrics_data]
        mock_get.return_value = mock_response

        # Act
        results = lyrics_service.search_lyrics("Test Artist Test Song")

        # Assert
        assert len(results) == 1
        assert results[0]["trackName"] == "Test Song"
        assert results[0]["artistName"] == "Test Artist"
        mock_get.assert_called_once()

    @patch("app.services.lyrics_service.requests.get")
    def test_search_lyrics_multiple_results(
        self, mock_get, lyrics_service, sample_lyrics_data
    ):
        """Test lyrics search with multiple results."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        second_result = sample_lyrics_data.copy()
        second_result["id"] = 12346
        second_result["albumName"] = "Another Album"
        mock_response.json.return_value = [sample_lyrics_data, second_result]
        mock_get.return_value = mock_response

        # Act
        results = lyrics_service.search_lyrics("Test Query")

        # Assert
        assert len(results) == 2
        assert results[0]["id"] == 12345
        assert results[1]["id"] == 12346

    @patch("app.services.lyrics_service.requests.get")
    def test_search_lyrics_no_results(self, mock_get, lyrics_service):
        """Test lyrics search with no results."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        # Act
        results = lyrics_service.search_lyrics("Unknown Song")

        # Assert
        assert results == []

    @patch("app.services.lyrics_service.requests.get")
    def test_search_lyrics_404_not_found(self, mock_get, lyrics_service):
        """Test lyrics search with 404 response."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Not found"}
        mock_get.return_value = mock_response

        # Act
        results = lyrics_service.search_lyrics("Unknown Song")

        # Assert - should return empty list for 404
        assert results == []

    @patch("app.services.lyrics_service.requests.get")
    def test_search_lyrics_structured_success(
        self, mock_get, lyrics_service, sample_lyrics_data
    ):
        """Test structured lyrics search."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [sample_lyrics_data]
        mock_get.return_value = mock_response

        # Act
        results = lyrics_service.search_lyrics_structured({
            "track_name": "Test Song",
            "artist_name": "Test Artist",
        })

        # Assert
        assert len(results) == 1
        assert results[0]["trackName"] == "Test Song"

    @patch("app.services.lyrics_service.requests.get")
    def test_search_lyrics_network_error_fallback(self, mock_get, lyrics_service):
        """Test that lyrics search tries backup URL on network error."""
        # Arrange - first call fails, second succeeds
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = [{"id": 1, "trackName": "Test"}]
        mock_get.side_effect = [
            requests.RequestException("Connection failed"),
            mock_response_success,
        ]

        # Act
        results = lyrics_service.search_lyrics("Test Query")

        # Assert
        assert len(results) == 1
        assert mock_get.call_count == 2  # Tried both URLs

    @patch("app.services.lyrics_service.requests.get")
    def test_search_lyrics_all_urls_fail(self, mock_get, lyrics_service):
        """Test that lyrics search raises error when all URLs fail."""
        # Arrange
        mock_get.side_effect = requests.RequestException("Connection failed")

        # Act & Assert
        with pytest.raises(ServiceError) as exc_info:
            lyrics_service.search_lyrics("Test Query")
        assert "Failed to connect" in str(exc_info.value)

    @patch("app.services.lyrics_service.requests.get")
    def test_search_lyrics_server_error(self, mock_get, lyrics_service):
        """Test that lyrics search tries backup on server error."""
        # Arrange
        mock_response_error = Mock()
        mock_response_error.status_code = 500
        mock_response_error.json.return_value = {"error": "Internal server error"}
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = [{"id": 1, "trackName": "Test"}]
        
        mock_get.side_effect = [mock_response_error, mock_response_success]

        # Act
        results = lyrics_service.search_lyrics("Test Query")

        # Assert
        assert len(results) == 1
        assert mock_get.call_count == 2

    def test_lyrics_service_urls(self, lyrics_service):
        """Test that lyrics service has correct URLs configured."""
        assert lyrics_service.primary_url == "https://lrclib.net"
        assert lyrics_service.backup_url == "https://lrclib.mrspinn.ca"

    def test_lyrics_service_headers(self, lyrics_service):
        """Test that lyrics service has correct headers."""
        assert "User-Agent" in lyrics_service.headers
        assert "OpenKaraokeStudio" in lyrics_service.headers["User-Agent"]
