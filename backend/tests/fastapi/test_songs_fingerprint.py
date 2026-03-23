"""Tests for songs fingerprint and replace endpoints."""
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.api.dependencies import get_current_user


SONG_ID = "test-song-abc"


@pytest.fixture(autouse=True)
def override_auth(fastapi_app):
    """Bypass authentication for all tests in this module."""
    fastapi_app.dependency_overrides[get_current_user] = lambda: Mock()
    yield
    fastapi_app.dependency_overrides.pop(get_current_user, None)


def make_mock_song(song_id=SONG_ID):
    song = Mock()
    song.id = song_id
    song.title = "Test Song"
    song.artist = "Test Artist"
    song.to_dict.return_value = {"id": song_id, "title": "Test Song", "artist": "Test Artist"}
    return song


class TestGetSongsByFingerprintStatus:
    def test_valid_status_returns_list(self, client):
        with patch("app.api.songs.SongRepository") as mock_repo_cls:
            mock_repo_cls.return_value.fetch_all.return_value = []
            response = client.get("/api/songs/by-fingerprint-status?status=not_checked")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_invalid_status_returns_400(self, client):
        response = client.get("/api/songs/by-fingerprint-status?status=garbage")
        assert response.status_code == 400

    def test_pagination_params_accepted(self, client):
        with patch("app.api.songs.SongRepository") as mock_repo_cls:
            mock_repo_cls.return_value.fetch_all.return_value = []
            response = client.get(
                "/api/songs/by-fingerprint-status?status=matched&limit=10&offset=5"
            )
        assert response.status_code == 200


class TestFingerprintSingleSong:
    def test_dispatches_task(self, client):
        mock_task = Mock(id="task-abc")
        with (
            patch("app.api.songs.SongRepository") as mock_repo_cls,
            patch("app.jobs.celery_app.celery") as mock_celery,
        ):
            mock_repo_cls.return_value.fetch.return_value = make_mock_song()
            mock_celery.send_task.return_value = mock_task
            response = client.post(f"/api/songs/{SONG_ID}/fingerprint")
        assert response.status_code == 202
        data = response.json()
        assert data["taskId"] == "task-abc"
        assert data["status"] == "dispatched"

    def test_song_not_found_returns_404(self, client):
        with patch("app.api.songs.SongRepository") as mock_repo_cls:
            mock_repo_cls.return_value.fetch.return_value = None
            response = client.post(f"/api/songs/{SONG_ID}/fingerprint")
        assert response.status_code == 404


class TestReplaceSongYouTube:
    PAYLOAD = {"video_id": "abc123", "engine_type": "three_track"}

    def test_happy_path(self, client):
        with (
            patch("app.api.songs.SongRepository") as mock_repo_cls,
            patch("app.repositories.JobRepository") as mock_job_repo_cls,
            patch("app.api.songs.FileService") as mock_fs_cls,
            patch("app.services.youtube_service.YouTubeService") as mock_yt_cls,
        ):
            mock_repo_cls.return_value.fetch.return_value = make_mock_song()
            mock_repo_cls.return_value.update.return_value = None
            mock_job_repo_cls.return_value.get_jobs_by_status.return_value = []
            mock_fs_cls.return_value.delete_song_files.return_value = None
            mock_yt_cls.return_value.download_and_process_async = Mock(return_value="job-123")
            response = client.post(f"/api/songs/{SONG_ID}/replace-youtube", json=self.PAYLOAD)
        assert response.status_code == 202
        data = response.json()
        assert data["jobId"] == "job-123"
        assert data["status"] == "pending"

    def test_song_not_found(self, client):
        with patch("app.api.songs.SongRepository") as mock_repo_cls:
            mock_repo_cls.return_value.fetch.return_value = None
            response = client.post(f"/api/songs/{SONG_ID}/replace-youtube", json=self.PAYLOAD)
        assert response.status_code == 404

    def test_active_job_returns_409(self, client):
        active_job = Mock(song_id=SONG_ID)
        with (
            patch("app.api.songs.SongRepository") as mock_repo_cls,
            patch("app.repositories.JobRepository") as mock_job_repo_cls,
        ):
            mock_repo_cls.return_value.fetch.return_value = make_mock_song()
            mock_job_repo_cls.return_value.get_jobs_by_status.return_value = [active_job]
            response = client.post(f"/api/songs/{SONG_ID}/replace-youtube", json=self.PAYLOAD)
        assert response.status_code == 409

    def test_invalid_engine_type_returns_422(self, client):
        response = client.post(
            f"/api/songs/{SONG_ID}/replace-youtube",
            json={"video_id": "abc", "engine_type": "invalid"},
        )
        assert response.status_code == 422


class TestReplaceSongUpload:
    def test_happy_path(self, client):
        mock_path = MagicMock()
        mock_path.__truediv__ = lambda self, other: mock_path
        mock_path.write_bytes = Mock()
        mock_task = Mock(id="task-xyz")
        with (
            patch("app.api.songs.SongRepository") as mock_repo_cls,
            patch("app.repositories.JobRepository") as mock_job_repo_cls,
            patch("app.api.songs.FileService") as mock_fs_cls,
            patch("app.jobs.celery_app.celery") as mock_celery,
        ):
            mock_repo_cls.return_value.fetch.return_value = make_mock_song()
            mock_repo_cls.return_value.update.return_value = None
            mock_job_repo_cls.return_value.get_jobs_by_status.return_value = []
            mock_job_repo_cls.return_value.create.return_value = None
            mock_job_repo_cls.return_value.update.return_value = None
            mock_fs_cls.return_value.get_song_directory.return_value = mock_path
            mock_celery.send_task.return_value = mock_task
            response = client.post(
                f"/api/songs/{SONG_ID}/replace-upload",
                files={"audio_file": ("test.mp3", b"audio data", "audio/mpeg")},
            )
        assert response.status_code == 202
        assert "jobId" in response.json()

    def test_song_not_found(self, client):
        with patch("app.api.songs.SongRepository") as mock_repo_cls:
            mock_repo_cls.return_value.fetch.return_value = None
            response = client.post(
                f"/api/songs/{SONG_ID}/replace-upload",
                files={"audio_file": ("test.mp3", b"data", "audio/mpeg")},
            )
        assert response.status_code == 404

    def test_non_audio_content_type(self, client):
        with patch("app.api.songs.SongRepository") as mock_repo_cls:
            mock_repo_cls.return_value.fetch.return_value = make_mock_song()
            response = client.post(
                f"/api/songs/{SONG_ID}/replace-upload",
                files={"audio_file": ("test.bin", b"data", "application/octet-stream")},
            )
        assert response.status_code == 400

    def test_invalid_engine_type(self, client):
        with (
            patch("app.api.songs.SongRepository") as mock_repo_cls,
            patch("app.repositories.JobRepository") as mock_job_repo_cls,
        ):
            mock_repo_cls.return_value.fetch.return_value = make_mock_song()
            mock_job_repo_cls.return_value.get_jobs_by_status.return_value = []
            response = client.post(
                f"/api/songs/{SONG_ID}/replace-upload",
                data={"engine_type": "bad"},
                files={"audio_file": ("test.mp3", b"data", "audio/mpeg")},
            )
        assert response.status_code == 400

    def test_active_job_returns_409(self, client):
        active_job = Mock(song_id=SONG_ID)
        with (
            patch("app.api.songs.SongRepository") as mock_repo_cls,
            patch("app.repositories.JobRepository") as mock_job_repo_cls,
        ):
            mock_repo_cls.return_value.fetch.return_value = make_mock_song()
            mock_job_repo_cls.return_value.get_jobs_by_status.return_value = [active_job]
            response = client.post(
                f"/api/songs/{SONG_ID}/replace-upload",
                files={"audio_file": ("test.mp3", b"data", "audio/mpeg")},
            )
        assert response.status_code == 409
