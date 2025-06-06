"""
Unit tests for the lyrics service.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from requests.exceptions import Timeout, ConnectionError
from pathlib import Path
import tempfile
import shutil

from app.services.lyrics_service import LyricsService, make_request, USER_AGENT
from app.services.file_service import FileService
from app.exceptions import ServiceError, ValidationError


class TestLyricsService:
    """Test suite for LyricsService class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_file_service(self, temp_dir):
        """Create a mock file service."""
        file_service = Mock(spec=FileService)
        file_service.get_song_directory.return_value = temp_dir / "test_song_id"
        return file_service

    @pytest.fixture
    def lyrics_service(self, mock_file_service):
        """Create a LyricsService instance for testing."""
        return LyricsService(file_service=mock_file_service)

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
            "syncedLyrics": "[00:00.00] Line 1\n[00:03.50] Line 2\n[00:07.00] Line 3"
        }

    @patch('app.services.lyrics_service.requests.get')
    def test_fetch_lyrics_success_with_album(self, mock_get, lyrics_service, sample_lyrics_data):
        """Test successful lyrics fetching with album info."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_lyrics_data
        mock_get.return_value = mock_response
        
        # Act
        result = lyrics_service.fetch_lyrics("Test Song", "Test Artist", "Test Album")
        
        # Assert
        assert result == sample_lyrics_data
        assert mock_get.call_count >= 1  # Could be cached or direct get

    @patch('app.services.lyrics_service.requests.get')
    def test_fetch_lyrics_fallback_to_search(self, mock_get, lyrics_service, sample_lyrics_data):
        """Test lyrics fetching fallback to search when direct get fails."""
        # Arrange - First calls (cached, direct) fail, search succeeds
        def mock_get_side_effect(url, **kwargs):
            mock_response = Mock()
            if "/api/search" in url:
                mock_response.status_code = 200
                mock_response.json.return_value = [sample_lyrics_data]
            else:
                mock_response.status_code = 404
                mock_response.json.return_value = {"error": "Not found"}
            return mock_response
        
        mock_get.side_effect = mock_get_side_effect
        
        # Act
        result = lyrics_service.fetch_lyrics("Test Song", "Test Artist", "Test Album")
        
        # Assert
        assert result == sample_lyrics_data

    @patch('app.services.lyrics_service.requests.get')
    def test_fetch_lyrics_not_found(self, mock_get, lyrics_service):
        """Test lyrics fetching when no results found."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Not found"}
        mock_get.return_value = mock_response
        
        # Act
        result = lyrics_service.fetch_lyrics("Unknown Song", "Unknown Artist")
        
        # Assert
        assert result is None

    @patch('app.services.lyrics_service.requests.get')
    def test_search_lyrics_success(self, mock_get, lyrics_service, sample_lyrics_data):
        """Test successful lyrics search."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [sample_lyrics_data]
        mock_get.return_value = mock_response
        
        # Act
        results = lyrics_service.search_lyrics("test query")
        
        # Assert
        assert results == [sample_lyrics_data]
        mock_get.assert_called_once()

    def test_get_lyrics_file_exists(self, lyrics_service, temp_dir):
        """Test getting lyrics from existing file."""
        # Arrange
        song_id = "test_song_id"
        lyrics_text = "Test lyrics content"
        lyrics_dir = temp_dir / song_id
        lyrics_dir.mkdir(parents=True)
        lyrics_file = lyrics_dir / "lyrics.txt"
        lyrics_file.write_text(lyrics_text, encoding='utf-8')
        
        # Act
        result = lyrics_service.get_lyrics(song_id)
        
        # Assert
        assert result == lyrics_text

    def test_get_lyrics_file_not_exists(self, lyrics_service):
        """Test getting lyrics when file doesn't exist."""
        # Act
        result = lyrics_service.get_lyrics("nonexistent_song")
        
        # Assert
        assert result is None

    def test_save_lyrics_success(self, lyrics_service, temp_dir):
        """Test saving lyrics to file."""
        # Arrange
        song_id = "test_song_id"
        lyrics_text = "Valid lyrics content"
        
        # Act
        result = lyrics_service.save_lyrics(song_id, lyrics_text)
        
        # Assert
        assert result is True
        lyrics_file = temp_dir / song_id / "lyrics.txt"
        assert lyrics_file.exists()
        assert lyrics_file.read_text(encoding='utf-8') == lyrics_text

    def test_save_lyrics_invalid(self, lyrics_service):
        """Test saving invalid lyrics."""
        # Act & Assert
        with pytest.raises(ValidationError):
            lyrics_service.save_lyrics("test_song", "")
        
        with pytest.raises(ValidationError):
            lyrics_service.save_lyrics("test_song", "  ")

    def test_validate_lyrics(self, lyrics_service):
        """Test lyrics validation."""
        # Valid cases
        assert lyrics_service.validate_lyrics("Valid lyrics") is True
        assert lyrics_service.validate_lyrics("Line 1\nLine 2") is True
        
        # Invalid cases
        assert lyrics_service.validate_lyrics("") is False
        assert lyrics_service.validate_lyrics("  ") is False
        assert lyrics_service.validate_lyrics("ab") is False  # Too short
        assert lyrics_service.validate_lyrics(None) is False
        assert lyrics_service.validate_lyrics(123) is False

    def test_lyrics_file_exists(self, lyrics_service, temp_dir):
        """Test checking if lyrics file exists."""
        # Arrange
        song_id = "test_song_id"
        lyrics_dir = temp_dir / song_id
        lyrics_dir.mkdir(parents=True)
        lyrics_file = lyrics_dir / "lyrics.txt"
        
        # Test file doesn't exist
        assert lyrics_service.lyrics_file_exists(song_id) is False
        
        # Create file and test it exists
        lyrics_file.write_text("test")
        assert lyrics_service.lyrics_file_exists(song_id) is True

    def test_get_lyrics_file_path(self, lyrics_service, mock_file_service):
        """Test getting lyrics file path."""
        # Act
        path = lyrics_service.get_lyrics_file_path("test_song_id")
        
        # Assert
        assert path.endswith("lyrics.txt")
        mock_file_service.get_song_directory.assert_called_once_with("test_song_id")

    def test_create_default_lyrics(self, lyrics_service):
        """Test creating default lyrics."""
        # Act
        default = lyrics_service.create_default_lyrics("test_song_id")
        
        # Assert
        assert default == "[Instrumental]"

    @patch('app.services.lyrics_service.requests.get')
    def test_service_error_handling(self, mock_get, lyrics_service):
        """Test service error handling for network issues."""
        # Arrange
        mock_get.side_effect = requests.RequestException("Network error")
        
        # Act & Assert
        with pytest.raises(ServiceError):
            lyrics_service.fetch_lyrics("Test Song", "Test Artist")


class TestLegacyMakeRequest:
    """Test suite for legacy make_request function."""

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

    def test_user_agent_constant(self):
        """Test that USER_AGENT constant is properly defined."""
        assert USER_AGENT == "OpenKaraokeStudio/0.1 (https://github.com/spencerfrost/open-karaoke)"
        assert isinstance(USER_AGENT, str)
        assert len(USER_AGENT) > 0
