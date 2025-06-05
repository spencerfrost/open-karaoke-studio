"""
Unit tests for the lyrics service.
"""

import pytest
from unittest.mock import Mock, patch
import requests
from requests.exceptions import Timeout, ConnectionError

from app.services.lyrics_service import make_request, USER_AGENT


class TestLyricsService:
    """Test suite for lyrics service functions."""

    @pytest.fixture
    def sample_response_data(self):
        """Sample response data for testing."""
        return {
            "id": 12345,
            "name": "Test Song",
            "artistName": "Test Artist",
            "albumName": "Test Album",
            "duration": 180.5,
            "plainLyrics": "Line 1\nLine 2\nLine 3",
            "syncedLyrics": "[00:00.00] Line 1\n[00:03.50] Line 2\n[00:07.00] Line 3"
        }

    @patch('app.services.lyrics_service.requests.get')
    def test_make_request_success(self, mock_get, sample_response_data, app):
        """Test successful API request."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_response_data
        mock_get.return_value = mock_response
        
        path = "/api/search"
        params = {"q": "test artist test song"}
        
        # Act
        with app.app_context():
            status, data = make_request(path, params)
        
        # Assert
        assert status == 200
        assert data == sample_response_data
        mock_get.assert_called_once_with(
            "https://lrclib.net/api/search",
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=10
        )

    @patch('app.services.lyrics_service.requests.get')
    def test_make_request_404_not_found(self, mock_get, app):
        """Test API request when lyrics not found."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Not found"}
        mock_get.return_value = mock_response
        
        path = "/api/get"
        params = {"artist_name": "Unknown Artist", "track_name": "Unknown Song"}
        
        # Act
        with app.app_context():
            status, data = make_request(path, params)
        
        # Assert
        assert status == 404
        assert data == {"error": "Not found"}

    @patch('app.services.lyrics_service.requests.get')
    def test_make_request_invalid_json(self, mock_get, app):
        """Test API request with invalid JSON response."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Invalid response text"
        mock_get.return_value = mock_response
        
        path = "/api/search"
        params = {"q": "test"}
        
        # Act
        with app.app_context():
            status, data = make_request(path, params)
        
        # Assert
        assert status == 200
        assert data == {"error": "Invalid JSON from LRCLIB"}

    @patch('app.services.lyrics_service.requests.get')
    def test_make_request_timeout(self, mock_get, app):
        """Test API request timeout handling."""
        # Arrange
        mock_get.side_effect = Timeout("Request timed out")
        
        path = "/api/search"
        params = {"q": "test"}
        
        # Act & Assert
        with app.app_context():
            with pytest.raises(Timeout):
                make_request(path, params)

    def test_user_agent_constant(self):
        """Test that USER_AGENT constant is properly defined."""
        assert USER_AGENT == "OpenKaraokeStudio/0.1 (https://github.com/spencerfrost/open-karaoke)"
        assert isinstance(USER_AGENT, str)
        assert len(USER_AGENT) > 0
