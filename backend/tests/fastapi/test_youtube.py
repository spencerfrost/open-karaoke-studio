"""
Tests for FastAPI YouTube endpoints.
"""

from unittest.mock import Mock

import pytest


class TestYouTubeSearch:
    """Tests for YouTube search endpoint."""

    def test_search_returns_results(self, client, mock_youtube_service):
        """Test successful YouTube search."""
        response = client.get("/api/youtube/search?query=rick+astley&maxResults=5")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert len(data["data"]) > 0
        mock_youtube_service.search_videos.assert_called_once_with("rick astley", 5)

    def test_search_requires_query(self, client):
        """Test that search requires a query parameter."""
        response = client.get("/api/youtube/search")
        
        assert response.status_code == 422  # Validation error

    def test_search_validates_max_results(self, client):
        """Test max_results validation."""
        # Too high
        response = client.get("/api/youtube/search?query=test&maxResults=100")
        assert response.status_code == 422

        # Too low
        response = client.get("/api/youtube/search?query=test&maxResults=0")
        assert response.status_code == 422

    def test_search_handles_service_error(self, client, mock_youtube_service):
        """Test handling of service errors."""
        mock_youtube_service.search_videos.side_effect = Exception("API Error")
        
        response = client.get("/api/youtube/search?query=test")
        
        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()


class TestYouTubeDownload:
    """Tests for YouTube download endpoint."""

    def test_download_creates_job(self, client, mock_youtube_service):
        """Test successful download job creation."""
        response = client.post(
            "/api/youtube/download",
            json={
                "video_id": "dQw4w9WgXcQ",
                "song_id": "song-123",
                "title": "Never Gonna Give You Up",
                "artist": "Rick Astley"
            }
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert data["data"]["jobId"] == "job-123"
        assert data["data"]["status"] == "pending"

    def test_download_requires_video_id(self, client):
        """Test that video_id is required."""
        response = client.post(
            "/api/youtube/download",
            json={"song_id": "song-123"}
        )
        
        assert response.status_code == 422

    def test_download_requires_song_id(self, client):
        """Test that song_id is required."""
        response = client.post(
            "/api/youtube/download",
            json={"video_id": "dQw4w9WgXcQ"}
        )
        
        assert response.status_code == 422

    def test_download_handles_empty_strings(self, client):
        """Test validation of empty string fields."""
        response = client.post(
            "/api/youtube/download",
            json={
                "video_id": "",
                "song_id": "song-123"
            }
        )
        
        assert response.status_code == 422

    def test_download_optional_fields(self, client, mock_youtube_service):
        """Test that title and artist are optional."""
        response = client.post(
            "/api/youtube/download",
            json={
                "video_id": "dQw4w9WgXcQ",
                "song_id": "song-123"
            }
        )
        
        assert response.status_code == 202
        mock_youtube_service.download_and_process_async.assert_called_once()
