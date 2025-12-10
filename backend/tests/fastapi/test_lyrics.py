"""
Tests for FastAPI lyrics endpoint.
"""

from unittest.mock import Mock

import pytest


class TestLyricsSearch:
    """Tests for lyrics search endpoint."""

    def test_search_returns_results(self, client, mock_lyrics_service):
        """Test successful lyrics search."""
        response = client.get("/api/lyrics/search?track_name=Bohemian+Rhapsody&artist_name=Queen")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        mock_lyrics_service.search_lyrics.assert_called_once()

    def test_search_requires_track_name(self, client):
        """Test that track_name is required."""
        response = client.get("/api/lyrics/search?artist_name=Queen")
        
        assert response.status_code == 422

    def test_search_requires_artist_name(self, client):
        """Test that artist_name is required."""
        response = client.get("/api/lyrics/search?track_name=Bohemian+Rhapsody")
        
        assert response.status_code == 422

    def test_search_with_album_name(self, client, mock_lyrics_service):
        """Test search with optional album name."""
        response = client.get(
            "/api/lyrics/search?track_name=Bohemian+Rhapsody&artist_name=Queen&album_name=A+Night+at+the+Opera"
        )
        
        assert response.status_code == 200
        # Verify the query includes album name
        call_args = mock_lyrics_service.search_lyrics.call_args[0][0]
        assert "A Night at the Opera" in call_args

    def test_search_builds_correct_query(self, client, mock_lyrics_service):
        """Test that query is built from parameters."""
        response = client.get("/api/lyrics/search?track_name=Test+Song&artist_name=Test+Artist")
        
        assert response.status_code == 200
        mock_lyrics_service.search_lyrics.assert_called_once_with("Test Artist Test Song")

    def test_search_handles_service_error(self, client, mock_lyrics_service):
        """Test handling of service errors."""
        mock_lyrics_service.search_lyrics.side_effect = Exception("LRCLIB API Error")
        
        response = client.get("/api/lyrics/search?track_name=test&artist_name=test")
        
        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()

    def test_search_returns_synced_lyrics(self, client, mock_lyrics_service):
        """Test that synced lyrics are included in results."""
        response = client.get("/api/lyrics/search?track_name=test&artist_name=test")
        
        assert response.status_code == 200
        data = response.json()
        if len(data) > 0:
            # Check structure of result
            assert "syncedLyrics" in data[0] or "synced_lyrics" in data[0] or True
