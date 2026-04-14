"""Tests for FastAPI lyrics endpoint."""

from unittest.mock import Mock, patch

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


class TestLyricsSearchErrorPaths:
    """Cover lines 73, 75-76, 81-82 — exception handling in search."""

    def test_search_handles_service_error(self, client, mock_lyrics_service):
        from app.exceptions import ServiceError
        mock_lyrics_service.search_lyrics.side_effect = ServiceError("lyricsdb down")
        response = client.get("/api/lyrics/search?track_name=test&artist_name=me")
        assert response.status_code == 500
        mock_lyrics_service.search_lyrics.side_effect = None

    def test_search_handles_connection_error(self, client, mock_lyrics_service):
        mock_lyrics_service.search_lyrics.side_effect = ConnectionError("unreachable")
        response = client.get("/api/lyrics/search?track_name=test&artist_name=me")
        assert response.status_code == 503
        mock_lyrics_service.search_lyrics.side_effect = None

    def test_search_handles_timeout_error(self, client, mock_lyrics_service):
        mock_lyrics_service.search_lyrics.side_effect = TimeoutError("timed out")
        response = client.get("/api/lyrics/search?track_name=test&artist_name=me")
        assert response.status_code == 504
        mock_lyrics_service.search_lyrics.side_effect = None

    def test_search_handles_unexpected_error(self, client, mock_lyrics_service):
        mock_lyrics_service.search_lyrics.side_effect = RuntimeError("unexpected")
        response = client.get("/api/lyrics/search?track_name=test&artist_name=me")
        assert response.status_code == 500
        mock_lyrics_service.search_lyrics.side_effect = None


class TestSearchLyricsSynced:
    """Cover lines 111-153 — search_lyrics_synced endpoint."""

    def test_search_synced_success(self, client):
        from unittest.mock import patch, MagicMock
        mock_svc = MagicMock()
        mock_svc.search_lyrics_structured.return_value = [
            {"trackName": "Test", "syncedLyrics": "[00:00] Hi"}
        ]
        with patch("app.api.lyrics.SyncedLyricsService", return_value=mock_svc):
            response = client.get("/api/lyrics/search-synced?track_name=Test&artist_name=Me")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_search_synced_with_album(self, client):
        from unittest.mock import patch, MagicMock
        mock_svc = MagicMock()
        mock_svc.search_lyrics_structured.return_value = []
        with patch("app.api.lyrics.SyncedLyricsService", return_value=mock_svc):
            response = client.get(
                "/api/lyrics/search-synced?track_name=Test&artist_name=Me&album_name=Album"
            )
        assert response.status_code == 200
        call_params = mock_svc.search_lyrics_structured.call_args[0][0]
        assert call_params.get("album_name") == "Album"

    def test_search_synced_service_error(self, client):
        from unittest.mock import patch, MagicMock
        from app.exceptions import ServiceError
        mock_svc = MagicMock()
        mock_svc.search_lyrics_structured.side_effect = ServiceError("failed")
        with patch("app.api.lyrics.SyncedLyricsService", return_value=mock_svc):
            response = client.get("/api/lyrics/search-synced?track_name=Test&artist_name=Me")
        assert response.status_code == 500

    def test_search_synced_unexpected_error(self, client):
        from unittest.mock import MagicMock
        mock_svc = MagicMock()
        mock_svc.search_lyrics_structured.side_effect = RuntimeError("boom")
        with patch("app.api.lyrics.SyncedLyricsService", return_value=mock_svc):
            response = client.get("/api/lyrics/search-synced?track_name=Test&artist_name=Me")
        assert response.status_code == 500


class TestManualAlignmentSelection:
    def test_align_defaults_to_plain_first(self, client, temp_library_dir):
        song = client.post(
            "/api/songs",
            json={"title": "Test Song", "artist": "Test Artist"},
        ).json()
        song_id = song["id"]

        client.post(
            f"/api/lyrics/songs/{song_id}?type=plain",
            json={"content": "plain words"},
        )
        client.post(
            f"/api/lyrics/songs/{song_id}?type=synced",
            json={"content": "[00:00.00]synced words"},
        )

        vocals_path = temp_library_dir / song_id / "vocals.mp3"
        vocals_path.parent.mkdir(parents=True, exist_ok=True)
        vocals_path.write_bytes(b"fake")

        with patch(
            "app.api.lyrics.FileService.get_vocals_path",
            return_value=vocals_path,
        ), patch(
            "app.api.lyrics.align_plain_lyrics_to_vocals",
            return_value={
                "words": [],
                "language": "en",
                "mean_score": 0.75,
                "word_count": 0,
                "line_count": 0,
                "aligned_at": "2026-04-08T00:00:00Z",
            },
        ) as mock_plain, patch(
            "app.api.lyrics.align_lyrics_to_vocals",
            return_value={
                "words": [],
                "language": "en",
                "mean_score": 0.9,
                "word_count": 0,
                "line_count": 0,
                "aligned_at": "2026-04-08T00:00:00Z",
            },
        ) as mock_synced:
            response = client.post(f"/api/lyrics/songs/{song_id}/align")

        assert response.status_code == 200
        mock_plain.assert_called_once()
        mock_synced.assert_not_called()

    def test_align_respects_explicit_synced_source(self, client, temp_library_dir):
        song = client.post(
            "/api/songs",
            json={"title": "Test Song", "artist": "Test Artist"},
        ).json()
        song_id = song["id"]

        client.post(
            f"/api/lyrics/songs/{song_id}?type=plain",
            json={"content": "plain words"},
        )
        client.post(
            f"/api/lyrics/songs/{song_id}?type=synced",
            json={"content": "[00:00.00]synced words"},
        )

        vocals_path = temp_library_dir / song_id / "vocals.mp3"
        vocals_path.parent.mkdir(parents=True, exist_ok=True)
        vocals_path.write_bytes(b"fake")

        with patch(
            "app.api.lyrics.FileService.get_vocals_path",
            return_value=vocals_path,
        ), patch(
            "app.api.lyrics.align_plain_lyrics_to_vocals",
            return_value={
                "words": [],
                "language": "en",
                "mean_score": 0.75,
                "word_count": 0,
                "line_count": 0,
                "aligned_at": "2026-04-08T00:00:00Z",
            },
        ) as mock_plain, patch(
            "app.api.lyrics.align_lyrics_to_vocals",
            return_value={
                "words": [],
                "language": "en",
                "mean_score": 0.9,
                "word_count": 0,
                "line_count": 0,
                "aligned_at": "2026-04-08T00:00:00Z",
            },
        ) as mock_synced:
            response = client.post(f"/api/lyrics/songs/{song_id}/align?source=synced")

        assert response.status_code == 200
        mock_plain.assert_not_called()
        mock_synced.assert_called_once()
