"""Tests for the session playlist endpoints (app/api/session_playlist.py).

TestClient runs background tasks before the request returns, so a POST has
already generated the playlist by the time the test polls it. Only the
YouTube Music account is mocked.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest

from app.db.models import DbSong, Job, JobStatus, KaraokeSession, PerformanceHistory
from app.repositories.job_repository import JobRepository
from app.utils.clock import utc_now

SESSION_ID = "PLAY"


@pytest.fixture
def youtube_music():
    with patch("app.api.session_playlist.YoutubeMusicService") as service_class:
        service = service_class.return_value
        service.create_playlist.return_value = (
            "https://music.youtube.com/playlist?list=PL123",
            "PL123",
        )
        yield service


@pytest.fixture
def karaoke_session(db):
    db.add(
        KaraokeSession(
            session_id=SESSION_ID,
            display_code=SESSION_ID,
            host_device_id="rest_play",
            host_user_id=1,
            expires_at=utc_now() + timedelta(hours=8),
        )
    )
    db.commit()


def _perform(db, song_id, video_id, minutes_ago):
    db.add(DbSong(id=song_id, title=song_id, artist="Artist", video_id=video_id))
    db.add(
        PerformanceHistory(
            song_id=song_id,
            singer_name="Sam",
            session_id=SESSION_ID,
            performed_at=utc_now() - timedelta(minutes=minutes_ago),
        )
    )
    db.commit()


def test_unknown_session_is_404(client, youtube_music):
    response = client.post("/api/sessions/NOPE/playlist")

    assert response.status_code == 404
    youtube_music.create_playlist.assert_not_called()


def test_playlist_not_started_is_404(client):
    response = client.get(f"/api/sessions/{SESSION_ID}/playlist")

    assert response.status_code == 404


def test_builds_playlist_in_performance_order(
    client, db, karaoke_session, youtube_music
):
    _perform(db, "second", "vid-2", minutes_ago=10)
    _perform(db, "first", "vid-1", minutes_ago=20)
    _perform(db, "uploaded", None, minutes_ago=5)

    response = client.post(f"/api/sessions/{SESSION_ID}/playlist")

    assert response.status_code == 202
    assert response.json()["status"] == "pending"
    _, _, video_ids = youtube_music.create_playlist.call_args.args
    assert video_ids == ["vid-1", "vid-2"]

    polled = client.get(f"/api/sessions/{SESSION_ID}/playlist").json()
    assert polled["status"] == "ready"
    assert polled["youtube_music_url"] == (
        "https://music.youtube.com/playlist?list=PL123"
    )
    assert polled["youtube_music_playlist_id"] == "PL123"
    assert polled["song_count"] == 2
    assert polled["completed_at"] is not None


def test_second_request_returns_the_first_playlist(
    client, db, karaoke_session, youtube_music
):
    _perform(db, "song", "vid-1", minutes_ago=1)
    client.post(f"/api/sessions/{SESSION_ID}/playlist")

    response = client.post(f"/api/sessions/{SESSION_ID}/playlist")

    assert response.json()["status"] == "ready"
    youtube_music.create_playlist.assert_called_once()


def test_fails_when_no_song_has_a_video(client, db, karaoke_session, youtube_music):
    _perform(db, "uploaded", None, minutes_ago=1)

    client.post(f"/api/sessions/{SESSION_ID}/playlist")

    polled = client.get(f"/api/sessions/{SESSION_ID}/playlist").json()
    assert polled["status"] == "failed"
    assert polled["error_message"] == "No songs with video IDs found in this session"
    youtube_music.create_playlist.assert_not_called()


def test_fails_with_the_youtube_music_error(client, db, karaoke_session, youtube_music):
    _perform(db, "song", "vid-1", minutes_ago=1)
    youtube_music.create_playlist.side_effect = RuntimeError("not signed in")

    client.post(f"/api/sessions/{SESSION_ID}/playlist")

    polled = client.get(f"/api/sessions/{SESSION_ID}/playlist").json()
    assert polled["status"] == "failed"
    assert polled["error_message"] == "not signed in"


def test_unreadable_status_message_still_reports_status(client, karaoke_session):
    JobRepository().create(
        Job(
            id=f"playlist-{SESSION_ID}",
            filename=f"playlist-{SESSION_ID}",
            status=JobStatus.PROCESSING,
            status_message="Creating playlist...",
            engine_type="playlist_generation",
            created_at=utc_now(),
        )
    )

    polled = client.get(f"/api/sessions/{SESSION_ID}/playlist").json()

    assert polled["status"] == "processing"
    assert polled["youtube_music_url"] is None
    assert polled["song_count"] == 0


def test_a_recycled_codes_old_playlist_is_not_handed_over(
    client, db, karaoke_session, youtube_music
):
    """Codes are reused after a purge; last month's playlist under it isn't this one's."""
    JobRepository().create(
        Job(
            id=f"playlist-{SESSION_ID}",
            filename=f"playlist-{SESSION_ID}",
            status=JobStatus.COMPLETED,
            status_message='{"youtube_music_url": "https://old", "song_count": 9}',
            engine_type="playlist_generation",
            created_at=utc_now() - timedelta(days=30),
        )
    )

    assert client.get(f"/api/sessions/{SESSION_ID}/playlist").status_code == 404

    _perform(db, "song", "vid-1", minutes_ago=1)
    client.post(f"/api/sessions/{SESSION_ID}/playlist")

    polled = client.get(f"/api/sessions/{SESSION_ID}/playlist").json()
    assert (
        polled["youtube_music_url"] == "https://music.youtube.com/playlist?list=PL123"
    )
    assert polled["song_count"] == 1
