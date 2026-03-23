"""
Tests for FastAPI YouTube endpoints.
"""

from unittest.mock import Mock, patch

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


class TestYouTubeSearchErrorPaths:
    """Cover lines 97, 99, 101, 103-104, 109-110 — exception handling in search."""

    def test_search_handles_validation_error(self, client, mock_youtube_service):
        from app.exceptions import ValidationError
        mock_youtube_service.search_videos.side_effect = ValidationError("bad query")
        response = client.get("/api/youtube/search?query=test")
        assert response.status_code == 400
        mock_youtube_service.search_videos.side_effect = None

    def test_search_handles_network_error(self, client, mock_youtube_service):
        from app.exceptions import NetworkError
        mock_youtube_service.search_videos.side_effect = NetworkError("unreachable")
        response = client.get("/api/youtube/search?query=test")
        assert response.status_code == 503
        mock_youtube_service.search_videos.side_effect = None

    def test_search_handles_service_error(self, client, mock_youtube_service):
        from app.exceptions import ServiceError
        mock_youtube_service.search_videos.side_effect = ServiceError("yt down")
        response = client.get("/api/youtube/search?query=test")
        assert response.status_code == 500
        mock_youtube_service.search_videos.side_effect = None

    def test_search_handles_connection_error(self, client, mock_youtube_service):
        mock_youtube_service.search_videos.side_effect = ConnectionError("conn refused")
        response = client.get("/api/youtube/search?query=test")
        assert response.status_code == 503
        mock_youtube_service.search_videos.side_effect = None

    def test_search_handles_timeout_error(self, client, mock_youtube_service):
        mock_youtube_service.search_videos.side_effect = TimeoutError("timed out")
        response = client.get("/api/youtube/search?query=test")
        assert response.status_code == 504
        mock_youtube_service.search_videos.side_effect = None


class TestYouTubeDownloadErrorPaths:
    """Cover lines 170-176 — exception handling in download."""

    def test_download_handles_validation_error(self, client, mock_youtube_service):
        from app.exceptions import ValidationError
        mock_youtube_service.download_and_process_async.side_effect = ValidationError("bad id")
        response = client.post("/api/youtube/download", json={"video_id": "abc", "song_id": "s1"})
        assert response.status_code == 400
        mock_youtube_service.download_and_process_async.side_effect = None

    def test_download_handles_service_error(self, client, mock_youtube_service):
        from app.exceptions import ServiceError
        mock_youtube_service.download_and_process_async.side_effect = ServiceError("dl failed")
        response = client.post("/api/youtube/download", json={"video_id": "abc", "song_id": "s1"})
        assert response.status_code == 500
        mock_youtube_service.download_and_process_async.side_effect = None

    def test_download_handles_invalid_engine_type(self, client):
        """Cover field_validator for engine_type."""
        response = client.post("/api/youtube/download", json={
            "video_id": "abc", "song_id": "s1", "engine_type": "invalid_engine"
        })
        assert response.status_code == 422

    def test_download_whitespace_title_normalized_to_none(self, client, mock_youtube_service):
        """Cover validate_optional_strings — whitespace → None."""
        response = client.post("/api/youtube/download", json={
            "video_id": "abc", "song_id": "s1", "title": "   ", "artist": ""
        })
        # Should succeed (whitespace title normalized to None)
        assert response.status_code == 202


class TestYouTubePreview:
    """Tests for YouTube audio preview redirect endpoint."""

    def test_redirects_to_stream_url(self, client):
        stream_url = "https://cdn.example.com/audio.webm"
        with patch("app.api.youtube.YouTubeService") as mock_cls:
            mock_cls.return_value.get_audio_preview_url.return_value = stream_url
            response = client.get(
                "/api/youtube/preview/dQw4w9WgXcQ", follow_redirects=False
            )
        assert response.status_code == 302
        assert response.headers["location"] == stream_url

    def test_validation_error_returns_400(self, client):
        from app.exceptions import ValidationError
        with patch("app.api.youtube.YouTubeService") as mock_cls:
            mock_cls.return_value.get_audio_preview_url.side_effect = ValidationError("bad id")
            response = client.get("/api/youtube/preview/bad-id")
        assert response.status_code == 400

    def test_service_error_returns_500(self, client):
        from app.exceptions import ServiceError
        with patch("app.api.youtube.YouTubeService") as mock_cls:
            mock_cls.return_value.get_audio_preview_url.side_effect = ServiceError("yt-dlp fail")
            response = client.get("/api/youtube/preview/abc")
        assert response.status_code == 500

    def test_unexpected_error_returns_500(self, client):
        with patch("app.api.youtube.YouTubeService") as mock_cls:
            mock_cls.return_value.get_audio_preview_url.side_effect = RuntimeError("boom")
            response = client.get("/api/youtube/preview/abc")
        assert response.status_code == 500
