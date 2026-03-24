"""
iTunes Service Tests

Test suite for iTunes service functionality including:
- iTunes API search operations
- Canonical release filtering
- Error handling and edge cases
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
import requests
from app.services.itunes_service import (
    _filter_canonical_releases,
    search_itunes,
)


class TestItunesSearch:
    """Test iTunes search functionality"""

    @patch("app.services.itunes_service.requests.get")
    def test_search_itunes_success(self, mock_get):
        """Test successful iTunes search with valid results"""
        # Arrange
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.json.return_value = {
            "results": [
                {
                    "trackId": 123456789,
                    "trackName": "Test Song",
                    "artistName": "Test Artist",
                    "artistId": 987654321,
                    "collectionName": "Test Album",
                    "collectionId": 111222333,
                    "releaseDate": "2023-01-15T12:00:00Z",
                    "primaryGenreName": "Pop",
                    "trackTimeMillis": 180000,
                    "trackNumber": 1,
                    "discNumber": 1,
                    "country": "USA",
                    "currency": "USD",
                    "trackPrice": 1.29,
                    "previewUrl": "https://example.com/preview.mp3",
                    "artworkUrl30": "https://example.com/art30.jpg",
                    "artworkUrl60": "https://example.com/art60.jpg",
                    "artworkUrl100": "https://example.com/art100.jpg",
                    "collectionPrice": 9.99,
                    "trackExplicitness": "notExplicit",
                    "collectionExplicitness": "notExplicit",
                    "isStreamable": True,
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        results = search_itunes("Test Artist", "Test Song")

        # Assert
        assert len(results) == 1
        track = results[0]
        assert track["id"] == 123456789
        assert track["title"] == "Test Song"
        assert track["artist"] == "Test Artist"
        assert track["album"] == "Test Album"
        assert track["releaseYear"] == 2023
        assert track["releaseDateFormatted"] == "2023-01-15"

        # Verify API call parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "https://itunes.apple.com/search"
        params = call_args[1]["params"]
        assert params["term"] == "Test Artist Test Song"
        assert params["entity"] == "song"
        assert params["media"] == "music"

    @patch("app.services.itunes_service.requests.get")
    def test_search_itunes_with_album(self, mock_get):
        """Test iTunes search including album in search terms"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        search_itunes("Artist", "Song", "Album")

        # Assert
        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert params["term"] == "Artist Song Album"

    @patch("app.services.itunes_service.requests.get")
    def test_search_itunes_empty_results(self, mock_get):
        """Test iTunes search with no results"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        results = search_itunes("Nonexistent Artist", "Nonexistent Song")

        # Assert
        assert results == []

    @patch("app.services.itunes_service.requests.get")
    def test_search_itunes_api_timeout(self, mock_get):
        """Test iTunes search with API timeout"""
        # Arrange
        mock_get.side_effect = requests.Timeout("Request timeout")

        # Act
        results = search_itunes("Artist", "Song")

        # Assert
        assert results == []

    @patch("app.services.itunes_service.requests.get")
    def test_search_itunes_api_error(self, mock_get):
        """Test iTunes search with API error"""
        # Arrange
        mock_get.side_effect = requests.RequestException("API Error")

        # Act
        results = search_itunes("Artist", "Song")

        # Assert
        assert results == []

    @patch("app.services.itunes_service.requests.get")
    def test_search_itunes_invalid_release_date(self, mock_get):
        """Test iTunes search with invalid release date format"""
        # Arrange
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.json.return_value = {
            "results": [
                {
                    "trackId": 123,
                    "trackName": "Test Song",
                    "artistName": "Test Artist",
                    "releaseDate": "invalid-date-format",
                    "trackTimeMillis": 180000,
                    "collectionName": "Test Album",  # Required for filtering
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        results = search_itunes("Test Artist", "Test Song")

        # Assert
        assert len(results) == 1
        track = results[0]
        assert track["releaseYear"] is None
        assert track["releaseDateFormatted"] is None

    @patch("app.services.itunes_service.requests.get")
    def test_search_itunes_missing_fields(self, mock_get):
        """Test iTunes search with missing optional fields"""
        # Arrange
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.json.return_value = {
            "results": [
                {
                    "trackId": 123,
                    "trackName": "Test Song",
                    "artistName": "Test Artist",
                    "collectionName": "Test Album",  # Required for filtering
                    # Missing many optional fields
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        results = search_itunes("Test Artist", "Test Song")

        # Assert
        assert len(results) == 1
        track = results[0]
        assert track["id"] == 123
        assert track["title"] == "Test Song"
        assert track["artist"] == "Test Artist"
        assert track["album"] == "Test Album"


class TestItunesFilterCanonicalReleases:
    """Test iTunes canonical release filtering"""

    def test_filter_canonical_releases_exact_match(self):
        """Test filtering with exact artist and title match"""
        # Arrange
        tracks = [
            {
                "title": "Test Song",
                "artist": "Test Artist",
                "album": "Main Album",
                "releaseYear": 2023,
            },
            {
                "title": "Test Song (Remix)",
                "artist": "Test Artist",
                "album": "Remix Album",
                "releaseYear": 2023,
            },
        ]

        # Act
        filtered = _filter_canonical_releases(tracks, "Test Artist", "Test Song")

        # Assert
        assert len(filtered) >= 1
        # Should prefer exact title match
        exact_matches = [t for t in filtered if t["title"] == "Test Song"]
        assert len(exact_matches) > 0

    def test_filter_canonical_releases_case_insensitive(self):
        """Test filtering is case insensitive"""
        # Arrange
        tracks = [
            {
                "title": "TEST SONG",
                "artist": "TEST ARTIST",
                "album": "Album",
                "releaseYear": 2023,
            }
        ]

        # Act
        filtered = _filter_canonical_releases(tracks, "test artist", "test song")

        # Assert
        assert len(filtered) == 1

    def test_filter_canonical_releases_prefer_studio_albums(self):
        """Test filtering prefers studio albums over compilations"""
        # Arrange
        tracks = [
            {
                "title": "Test Song",
                "artist": "Test Artist",
                "album": "Greatest Hits",
                "releaseYear": 2020,
            },
            {
                "title": "Test Song",
                "artist": "Test Artist",
                "album": "Studio Album",
                "releaseYear": 2019,
            },
        ]

        # Act
        filtered = _filter_canonical_releases(tracks, "Test Artist", "Test Song")

        # Assert
        # Should prefer non-compilation album
        studio_matches = [t for t in filtered if "Greatest Hits" not in t["album"]]
        assert len(studio_matches) > 0


# Integration test helpers
@pytest.fixture
def sample_itunes_response():
    """Sample iTunes API response for testing"""
    return {
        "results": [
            {
                "trackId": 123456789,
                "trackName": "Test Song",
                "artistName": "Test Artist",
                "artistId": 987654321,
                "collectionName": "Test Album",
                "collectionId": 111222333,
                "releaseDate": "2023-01-15T12:00:00Z",
                "primaryGenreName": "Pop",
                "trackTimeMillis": 180000,
                "artworkUrl100": "https://example.com/art100.jpg",
            }
        ]
    }


@pytest.fixture
def sample_track_data():
    """Sample iTunes track data for testing"""
    return {
        "id": 123456789,
        "title": "Test Song",
        "artist": "Test Artist",
        "album": "Test Album",
        "genre": "Pop",
        "releaseYear": 2023,
        "duration": 180000,
        "artworkUrl100": "https://example.com/art100.jpg",
    }
