"""
Tests for FastAPI YouTube Music endpoints.
"""

import pytest
from unittest.mock import Mock


class TestYouTubeMusicSearch:
    """Tests for YouTube Music search endpoint."""

    def test_search_returns_results(self, client, mock_youtube_music_service, mock_db_session):
        """Test successful YouTube Music search."""
        response = client.get("/api/youtube-music/search?q=bohemian+rhapsody&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["error"] is None
        mock_youtube_music_service.search_songs.assert_called_once_with("bohemian rhapsody", limit=10)

    def test_search_requires_query(self, client):
        """Test that search requires a query parameter."""
        response = client.get("/api/youtube-music/search")
        
        assert response.status_code == 422  # Validation error

    def test_search_default_limit(self, client, mock_youtube_music_service, mock_db_session):
        """Test default limit is applied."""
        response = client.get("/api/youtube-music/search?q=test")
        
        assert response.status_code == 200
        mock_youtube_music_service.search_songs.assert_called_once_with("test", limit=10)

    def test_search_validates_limit(self, client):
        """Test limit validation."""
        # Too high
        response = client.get("/api/youtube-music/search?q=test&limit=100")
        assert response.status_code == 422

        # Too low
        response = client.get("/api/youtube-music/search?q=test&limit=0")
        assert response.status_code == 422

    def test_search_adds_exists_in_library_flag(self, client, mock_youtube_music_service, mock_db_session):
        """Test that existsInLibrary flag is added to results."""
        response = client.get("/api/youtube-music/search?q=test")
        
        assert response.status_code == 200
        data = response.json()
        for result in data["results"]:
            assert "existsInLibrary" in result

    def test_search_handles_service_error(self, client, mock_youtube_music_service, mock_db_session):
        """Test handling of service errors."""
        mock_youtube_music_service.search_songs.side_effect = Exception("API Error")
        
        response = client.get("/api/youtube-music/search?q=test")
        
        assert response.status_code == 200  # Returns empty results on error
        data = response.json()
        assert data["results"] == []
        assert "API Error" in data["error"]


class TestYouTubeMusicArtist:
    """Tests for YouTube Music artist endpoint."""

    def test_get_artist_returns_data(self, client, mock_youtube_music_service, mock_db_session):
        """Test successful artist lookup."""
        response = client.get("/api/youtube-music/artist/UCEPMVbUzImPl4p8k4LkGevA")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["error"] is None
        mock_youtube_music_service.get_artist.assert_called_once()

    def test_get_artist_with_custom_limit(self, client, mock_youtube_music_service, mock_db_session):
        """Test artist endpoint with custom limit."""
        response = client.get("/api/youtube-music/artist/UCEPMVbUzImPl4p8k4LkGevA?limit=20")
        
        assert response.status_code == 200
        mock_youtube_music_service.get_artist.assert_called_once_with(
            "UCEPMVbUzImPl4p8k4LkGevA", 
            top_songs_limit=20
        )

    def test_get_artist_handles_error(self, client, mock_youtube_music_service, mock_db_session):
        """Test error handling for artist lookup."""
        mock_youtube_music_service.get_artist.side_effect = Exception("Not found")
        
        response = client.get("/api/youtube-music/artist/invalid-id")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"] is None
        assert "Not found" in data["error"]


class TestYouTubeMusicAlbum:
    """Tests for YouTube Music album tracks endpoint."""

    def test_get_album_tracks_returns_data(self, client, mock_youtube_music_service, mock_db_session):
        """Test successful album tracks lookup."""
        response = client.get("/api/youtube-music/album/MPREb_test123/tracks")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["error"] is None
        mock_youtube_music_service.get_album_tracks.assert_called_once_with("MPREb_test123")

    def test_get_album_tracks_handles_error(self, client, mock_youtube_music_service, mock_db_session):
        """Test error handling for album tracks lookup."""
        mock_youtube_music_service.get_album_tracks.side_effect = Exception("Album not found")
        
        response = client.get("/api/youtube-music/album/invalid-id/tracks")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"] is None
        assert "Album not found" in data["error"]
