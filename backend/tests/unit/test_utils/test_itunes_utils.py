"""
Tests for iTunes utilities - Phase 7 of Song Model Emergency Surgery

Tests the new efficient iTunes metadata enhancement functions.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from scripts.utils.itunes_utils import (
    enhance_song_with_itunes_data,
    search_itunes_for_song,
    validate_itunes_match,
)


class TestEnhanceSongWithItunesData:
    """Test the new efficient iTunes data enhancement function"""

    def test_enhance_with_basic_itunes_data(self):
        """Test enhancing song with basic iTunes data"""
        # Create a mock DbSong
        mock_song = Mock()
        mock_song.id = "test-song-123"
        mock_song.title = "Original Title"
        mock_song.artist = "Original Artist"
        mock_song.album = None
        mock_song.genre = None
        mock_song.duration = None

        # Mock iTunes data
        itunes_data = {
            "trackId": 12345,
            "trackName": "Enhanced Title",
            "artistName": "Enhanced Artist",
            "collectionName": "Enhanced Album",
            "primaryGenreName": "Rock",
            "trackTimeMillis": 180000,
            "artistId": 67890,
            "collectionId": 54321,
            "trackExplicitness": "notExplicit",
            "previewUrl": "https://example.com/preview.mp3",
            "releaseDate": "2023-01-15T00:00:00Z",
            "artworkUrl30": "https://example.com/art30.jpg",
            "artworkUrl60": "https://example.com/art60.jpg",
            "artworkUrl100": "https://example.com/art100.jpg",
            "artworkUrl600": "https://example.com/art600.jpg",
        }

        # Call the function
        enhanced = enhance_song_with_itunes_data(mock_song, itunes_data)

        # Verify enhanced data
        assert enhanced["title"] == "Original Title"  # Keeps original
        assert enhanced["artist"] == "Original Artist"  # Keeps original
        assert enhanced["album"] == "Enhanced Album"  # Uses iTunes data
        assert enhanced["genre"] == "Rock"  # Uses iTunes data
        assert enhanced["duration"] == 180  # Converted from ms to seconds

        # Verify iTunes-specific fields
        assert enhanced["itunes_track_id"] == 12345
        assert enhanced["itunes_artist_id"] == 67890
        assert enhanced["itunes_collection_id"] == 54321
        assert enhanced["track_time_millis"] == 180000
        assert enhanced["itunes_explicit"] is False
        assert enhanced["itunes_preview_url"] == "https://example.com/preview.mp3"

        # Verify release information
        assert enhanced["release_date"] == "2023-01-15T00:00:00Z"
        assert enhanced["year"] == 2023

        # Verify artwork URLs are stored as JSON
        import json

        artwork_urls = json.loads(enhanced["itunes_artwork_urls"])
        assert "https://example.com/art30.jpg" in artwork_urls
        assert "https://example.com/art600.jpg" in artwork_urls

        # Verify raw metadata is stored
        raw_metadata = json.loads(enhanced["itunes_raw_metadata"])
        assert raw_metadata["trackId"] == 12345

    def test_enhance_with_missing_fields(self):
        """Test enhancement when iTunes data has missing fields"""
        mock_song = Mock()
        mock_song.id = "test-song-456"
        mock_song.title = "Song Title"
        mock_song.artist = "Song Artist"
        mock_song.album = "Song Album"
        mock_song.genre = "Song Genre"
        mock_song.duration = 200

        # Minimal iTunes data
        itunes_data = {
            "trackId": 12345,
            "trackName": "iTunes Title",
            # Missing most fields
        }

        enhanced = enhance_song_with_itunes_data(mock_song, itunes_data)

        # Should keep original data when iTunes data is missing
        assert enhanced["title"] == "Song Title"
        assert enhanced["artist"] == "Song Artist"
        assert enhanced["album"] == "Song Album"
        assert enhanced["genre"] == "Song Genre"
        assert enhanced["duration"] == 200

        # Should include iTunes track ID
        assert enhanced["itunes_track_id"] == 12345

    def test_enhance_with_empty_itunes_data(self):
        """Test enhancement with empty iTunes data"""
        mock_song = Mock()
        mock_song.id = "test-song-789"
        mock_song.title = "Song Title"
        mock_song.artist = "Song Artist"
        mock_song.album = None
        mock_song.genre = None
        mock_song.duration = None

        enhanced = enhance_song_with_itunes_data(mock_song, {})

        # Should work with empty data
        assert enhanced["title"] == "Song Title"
        assert enhanced["artist"] == "Song Artist"
        assert enhanced.get("itunes_track_id") is None

    def test_enhance_handles_errors_gracefully(self):
        """Test that enhancement handles errors gracefully"""
        mock_song = Mock()
        mock_song.id = "test-song-error"
        # Simulate an error by making song.title raise an exception
        mock_song.title = None
        mock_song.artist = None

        # Should return empty dict on error
        enhanced = enhance_song_with_itunes_data(mock_song, {"trackId": 123})
        assert enhanced == {}


class TestValidateItunesMatch:
    """Test iTunes match validation function"""

    def test_good_match(self):
        """Test validation of a good iTunes match"""
        mock_song = Mock()
        mock_song.title = "Bohemian Rhapsody"
        mock_song.artist = "Queen"

        itunes_data = {"trackName": "Bohemian Rhapsody", "artistName": "Queen"}

        is_match, reason = validate_itunes_match(mock_song, itunes_data)
        assert is_match is True
        assert "Good match" in reason

    def test_partial_match(self):
        """Test validation of a partial match"""
        mock_song = Mock()
        mock_song.title = "Hey Jude"
        mock_song.artist = "The Beatles"

        itunes_data = {"trackName": "Hey Jude (Remastered)", "artistName": "Beatles"}

        is_match, reason = validate_itunes_match(mock_song, itunes_data)
        # Should still match due to title substring and artist similarity
        assert is_match is True

    def test_poor_match(self):
        """Test validation of a poor match"""
        mock_song = Mock()
        mock_song.title = "Yellow Submarine"
        mock_song.artist = "The Beatles"

        itunes_data = {"trackName": "Yesterday", "artistName": "Paul McCartney"}

        is_match, reason = validate_itunes_match(mock_song, itunes_data)
        assert is_match is False
        assert "Poor match" in reason


class TestSearchItunesForSong:
    """Test iTunes search strategies"""

    @patch("scripts.utils.itunes_utils.search_itunes")
    def test_search_with_album_strategy(self, mock_search):
        """Test search with artist + title + album strategy"""
        mock_song = Mock()
        mock_song.id = "test-search-123"
        mock_song.title = "Test Song"
        mock_song.artist = "Test Artist"
        mock_song.album = "Test Album"

        mock_search.return_value = [
            {"trackName": "Test Song", "artistName": "Test Artist"}
        ]

        result = search_itunes_for_song(mock_song)

        # Should call search_itunes with all three parameters
        mock_search.assert_called_with(
            "Test Artist", "Test Song", "Test Album", limit=1
        )
        assert result is not None
        assert result["trackName"] == "Test Song"

    @patch("scripts.utils.itunes_utils.search_itunes")
    def test_search_fallback_strategies(self, mock_search):
        """Test fallback to broader search strategies"""
        mock_song = Mock()
        mock_song.id = "test-search-456"
        mock_song.title = "Test Song"
        mock_song.artist = "Test Artist"
        mock_song.album = "Test Album"

        # First call (with album) returns no results
        # Second call (without album) returns results
        mock_search.side_effect = [
            [],  # First call: no results
            [
                {"trackName": "Test Song", "artistName": "Test Artist"}
            ],  # Second call: results
        ]

        result = search_itunes_for_song(mock_song)

        # Should have tried both strategies
        assert mock_search.call_count == 2
        assert result is not None

    @patch("scripts.utils.itunes_utils.search_itunes")
    def test_search_with_unknown_artist(self, mock_search):
        """Test search with Unknown Artist"""
        mock_song = Mock()
        mock_song.id = "test-search-789"
        mock_song.title = "Test Song"
        mock_song.artist = "Unknown Artist"
        mock_song.album = None

        mock_search.return_value = [{"trackName": "Test Song"}]

        result = search_itunes_for_song(mock_song)

        # Should search with empty artist string
        mock_search.assert_called_with("", "Test Song", limit=5)
        assert result is not None
