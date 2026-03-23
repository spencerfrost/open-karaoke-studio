"""Tests for the new AcoustID metadata review endpoints."""
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def override_auth(fastapi_app):
    """Override auth dependency to bypass login for all tests in this module."""
    from app.api.dependencies import get_current_user
    from app.db.models.user import User

    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.username = "admin"
    mock_user.is_admin = True

    fastapi_app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    fastapi_app.dependency_overrides.pop(get_current_user, None)


def _make_song(song_id="song-123", status="no_match"):
    song = MagicMock()
    song.id = song_id
    song.title = "Test Song"
    song.artist = "Test Artist"
    song.acoustid_fingerprint_status = status
    song.to_dict.return_value = {
        "id": song_id,
        "title": "Test Song",
        "artist": "Test Artist",
        "status": "processed",
        "acoustidFingerprintStatus": status,
    }
    return song


class TestGetSongsByFingerprintStatus:
    def test_returns_songs_for_valid_status(self, client):
        song = _make_song()
        with patch("app.api.songs.SongRepository") as MockRepo:
            MockRepo.return_value.fetch_all.return_value = [song]
            response = client.get("/api/songs/by-fingerprint-status?status=no_match")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["id"] == "song-123"

    def test_returns_400_for_invalid_status(self, client):
        response = client.get("/api/songs/by-fingerprint-status?status=bogus")
        assert response.status_code == 400

    def test_returns_empty_list_when_no_songs(self, client):
        with patch("app.api.songs.SongRepository") as MockRepo:
            MockRepo.return_value.fetch_all.return_value = []
            response = client.get("/api/songs/by-fingerprint-status?status=failed")
        assert response.status_code == 200
        assert response.json() == []


class TestFingerprintSingleSong:
    def test_returns_202_and_dispatches_task(self, client):
        song = _make_song()
        with (
            patch("app.api.songs.SongRepository") as MockRepo,
            patch("app.jobs.celery_app.celery") as mock_celery,
        ):
            MockRepo.return_value.fetch.return_value = song
            mock_task = MagicMock()
            mock_task.id = "task-abc"
            mock_celery.send_task.return_value = mock_task

            response = client.post("/api/songs/song-123/fingerprint")

        assert response.status_code == 202
        assert response.json()["status"] == "dispatched"

    def test_returns_404_for_unknown_song(self, client):
        with patch("app.api.songs.SongRepository") as MockRepo:
            MockRepo.return_value.fetch.return_value = None
            response = client.post("/api/songs/unknown-id/fingerprint")
        assert response.status_code == 404


class TestReplaceSongYouTube:
    def test_returns_404_for_unknown_song(self, client):
        with patch("app.api.songs.SongRepository") as MockRepo:
            MockRepo.return_value.fetch.return_value = None
            response = client.post(
                "/api/songs/unknown-id/replace-youtube",
                json={"video_id": "abc123"},
            )
        assert response.status_code == 404

    def test_returns_409_when_song_already_processing(self, client):
        song = _make_song()
        active_job = MagicMock()
        active_job.song_id = "song-123"

        with (
            patch("app.api.songs.SongRepository") as MockRepo,
            patch("app.repositories.JobRepository") as MockJobRepo,
        ):
            MockRepo.return_value.fetch.return_value = song
            MockJobRepo.return_value.get_jobs_by_status.return_value = [active_job]
            response = client.post(
                "/api/songs/song-123/replace-youtube",
                json={"video_id": "abc123"},
            )
        assert response.status_code == 409

    def test_returns_202_on_success(self, client):
        song = _make_song()

        with (
            patch("app.api.songs.SongRepository") as MockRepo,
            patch("app.repositories.JobRepository") as MockJobRepo,
            patch("app.api.songs.FileService"),
            patch("app.services.youtube_service.YouTubeService") as MockYT,
        ):
            MockRepo.return_value.fetch.return_value = song
            MockJobRepo.return_value.get_jobs_by_status.return_value = []

            def _fake_download(**kwargs):
                return "job-xyz"

            MockYT.return_value.download_and_process_async.side_effect = _fake_download

            response = client.post(
                "/api/songs/song-123/replace-youtube",
                json={"video_id": "abc123", "title": "New Title", "artist": "New Artist"},
            )
        assert response.status_code == 202
        assert response.json()["status"] == "pending"


class TestReplaceSongUpload:
    def test_returns_404_for_unknown_song(self, client):
        with patch("app.api.songs.SongRepository") as MockRepo:
            MockRepo.return_value.fetch.return_value = None
            response = client.post(
                "/api/songs/unknown-id/replace-upload",
                files={"audio_file": ("test.mp3", BytesIO(b"audio"), "audio/mpeg")},
            )
        assert response.status_code == 404

    def test_returns_400_for_non_audio_file(self, client):
        song = _make_song()
        with patch("app.api.songs.SongRepository") as MockRepo:
            MockRepo.return_value.fetch.return_value = song
            response = client.post(
                "/api/songs/song-123/replace-upload",
                files={"audio_file": ("test.txt", BytesIO(b"not audio"), "text/plain")},
            )
        assert response.status_code == 400

    def test_returns_409_when_song_already_processing(self, client):
        song = _make_song()
        active_job = MagicMock()
        active_job.song_id = "song-123"

        with (
            patch("app.api.songs.SongRepository") as MockRepo,
            patch("app.repositories.JobRepository") as MockJobRepo,
        ):
            MockRepo.return_value.fetch.return_value = song
            MockJobRepo.return_value.get_jobs_by_status.return_value = [active_job]
            response = client.post(
                "/api/songs/song-123/replace-upload",
                files={"audio_file": ("test.mp3", BytesIO(b"audio"), "audio/mpeg")},
            )
        assert response.status_code == 409

    def test_returns_202_on_success(self, client, tmp_path):
        song = _make_song()
        mock_song_dir = tmp_path / "song-123"
        mock_song_dir.mkdir()

        with (
            patch("app.api.songs.SongRepository") as MockRepo,
            patch("app.repositories.JobRepository") as MockJobRepo,
            patch("app.api.songs.FileService") as MockFS,
            patch("app.jobs.celery_app.celery") as mock_celery,
        ):
            MockRepo.return_value.fetch.return_value = song
            MockJobRepo.return_value.get_jobs_by_status.return_value = []
            MockFS.return_value.get_song_directory.return_value = mock_song_dir

            mock_task = MagicMock()
            mock_task.id = "task-xyz"
            mock_celery.send_task.return_value = mock_task

            response = client.post(
                "/api/songs/song-123/replace-upload",
                files={"audio_file": ("test.mp3", BytesIO(b"fake audio data"), "audio/mpeg")},
            )

        assert response.status_code == 202
        assert response.json()["status"] == "pending"
        assert (mock_song_dir / "original.mp3").exists()
