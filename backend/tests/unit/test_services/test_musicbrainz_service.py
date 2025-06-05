"""
Unit tests for the MusicBrainz service.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from app.services.musicbrainz_service import (
    search_musicbrainz,
    get_cover_art,
    enhance_metadata_with_musicbrainz
)


class TestMusicBrainzService:
    """Test suite for MusicBrainz service functions."""

    @pytest.fixture
    def sample_search_result(self):
        """Sample MusicBrainz search result for testing."""
        return [
            {
                'id': '12345-abc-def',
                'title': 'Test Song',
                'artist-credit': [{'artist': {'name': 'Test Artist'}}],
                'length': 180000,  # in milliseconds
                'release-list': [
                    {
                        'id': 'release-123',
                        'title': 'Test Album',
                        'date': '2023-01-01'
                    }
                ]
            }
        ]

    @patch('app.services.musicbrainz_service.musicbrainzngs.search_recordings')
    def test_search_musicbrainz_success(self, mock_search, sample_search_result):
        """Test successful MusicBrainz search."""
        # Arrange
        mock_search.return_value = {
            'recording-list': sample_search_result
        }
        
        # Act
        result = search_musicbrainz("Test Artist", "Test Song")
        
        # Assert
        assert len(result) == 1
        assert result[0]['title'] == 'Test Song'
        mock_search.assert_called_once()

    @pytest.fixture
    def sample_recording_data(self):
        """Sample MusicBrainz recording data for testing."""
        return {
            "recordings": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "title": "Test Song",
                    "length": 180000,  # 3 minutes in milliseconds
                    "artist-credit": [
                        {
                            "name": "Test Artist",
                            "artist": {
                                "id": "456e7890-e89b-12d3-a456-426614174001",
                                "name": "Test Artist"
                            }
                        }
                    ],
                    "releases": [
                        {
                            "id": "789e0123-e89b-12d3-a456-426614174002",
                            "title": "Test Album",
                            "date": "2023-01-01"
                        }
                    ]
                }
            ]
        }

    @pytest.fixture
    def sample_artist_data(self):
        """Sample MusicBrainz artist data for testing."""
        return {
            "artists": [
                {
                    "id": "456e7890-e89b-12d3-a456-426614174001",
                    "name": "Test Artist",
                    "disambiguation": "rock band",
                    "life-span": {
                        "begin": "2000",
                        "end": None
                    },
                    "area": {
                        "name": "United States"
                    }
                }
            ]
        }

    def test_search_recording_success(self, musicbrainz_service, sample_recording_data):
        """Test successful recording search."""
        # Arrange
        song_title = "Test Song"
        artist_name = "Test Artist"
        
        with patch('app.services.musicbrainz_service.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_recording_data
            mock_get.return_value = mock_response
            
            # Act
            result = musicbrainz_service.search_recording(song_title, artist_name)
            
            # Assert
            assert result is not None
            assert len(result) == 1
            assert result[0]["title"] == "Test Song"
            assert result[0]["artist"] == "Test Artist"
            assert result[0]["duration"] == 180  # Converted to seconds

    def test_search_recording_no_results(self, musicbrainz_service):
        """Test recording search with no results."""
        # Arrange
        song_title = "Unknown Song"
        artist_name = "Unknown Artist"
        
        with patch('app.services.musicbrainz_service.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"recordings": []}
            mock_get.return_value = mock_response
            
            # Act
            result = musicbrainz_service.search_recording(song_title, artist_name)
            
            # Assert
            assert result == []

    def test_search_recording_api_error(self, musicbrainz_service):
        """Test recording search when API returns error."""
        # Arrange
        song_title = "Test Song"
        artist_name = "Test Artist"
        
        with patch('app.services.musicbrainz_service.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = Exception("API Error")
            mock_get.return_value = mock_response
            
            # Act & Assert
            with pytest.raises(Exception, match="API Error"):
                musicbrainz_service.search_recording(song_title, artist_name)

    def test_search_artist_success(self, musicbrainz_service, sample_artist_data):
        """Test successful artist search."""
        # Arrange
        artist_name = "Test Artist"
        
        with patch('app.services.musicbrainz_service.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_artist_data
            mock_get.return_value = mock_response
            
            # Act
            result = musicbrainz_service.search_artist(artist_name)
            
            # Assert
            assert result is not None
            assert len(result) == 1
            assert result[0]["name"] == "Test Artist"
            assert result[0]["country"] == "United States"

    def test_get_recording_by_id_success(self, musicbrainz_service, sample_recording_data):
        """Test successful recording retrieval by ID."""
        # Arrange
        recording_id = "123e4567-e89b-12d3-a456-426614174000"
        recording_data = sample_recording_data["recordings"][0]
        
        with patch('app.services.musicbrainz_service.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = recording_data
            mock_get.return_value = mock_response
            
            # Act
            result = musicbrainz_service.get_recording_by_id(recording_id)
            
            # Assert
            assert result is not None
            assert result["id"] == recording_id
            assert result["title"] == "Test Song"

    def test_get_recording_by_id_not_found(self, musicbrainz_service):
        """Test recording retrieval when recording doesn't exist."""
        # Arrange
        recording_id = "nonexistent-id"
        
        with patch('app.services.musicbrainz_service.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            # Act
            result = musicbrainz_service.get_recording_by_id(recording_id)
            
            # Assert
            assert result is None

    def test_rate_limiting(self, musicbrainz_service):
        """Test that rate limiting is respected."""
        # Arrange
        with patch('app.services.musicbrainz_service.time.sleep') as mock_sleep:
            with patch('app.services.musicbrainz_service.requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 503  # Service unavailable (rate limited)
                mock_get.return_value = mock_response
                
                # Act
                try:
                    musicbrainz_service.search_recording("Test", "Artist")
                except Exception:
                    pass  # Expected to fail
                
                # Assert
                mock_sleep.assert_called()  # Should have slept due to rate limiting

    def test_parse_artist_credit(self, musicbrainz_service):
        """Test parsing of artist credit information."""
        # Arrange
        artist_credit = [
            {"name": "Artist One"},
            {"name": " feat. "},
            {"name": "Artist Two"}
        ]
        
        # Act
        result = musicbrainz_service._parse_artist_credit(artist_credit)
        
        # Assert
        assert result == "Artist One feat. Artist Two"

    def test_parse_duration(self, musicbrainz_service):
        """Test parsing of duration from milliseconds to seconds."""
        # Arrange
        duration_ms = 180000  # 3 minutes
        
        # Act
        result = musicbrainz_service._parse_duration(duration_ms)
        
        # Assert
        assert result == 180

    def test_parse_duration_none(self, musicbrainz_service):
        """Test parsing of None duration."""
        # Arrange
        duration_ms = None
        
        # Act
        result = musicbrainz_service._parse_duration(duration_ms)
        
        # Assert
        assert result is None

    def test_format_search_query(self, musicbrainz_service):
        """Test formatting of search queries."""
        # Arrange
        title = "Test Song"
        artist = "Test Artist"
        
        # Act
        result = musicbrainz_service._format_search_query(title, artist)
        
        # Assert
        assert "Test Song" in result
        assert "Test Artist" in result
        assert "recording:" in result or "artist:" in result
