"""Failed songs: guests can restart them, and the songbook doesn't list them."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.dependencies import require_admin
from app.db.models import DbSong
from tests.integration.conftest import _get_mock_user, _TestingSessionLocal


def _create_song(
    client, *, title, artist, status="processed", video_id: str | None = "vid123"
):
    resp = client.post(
        "/api/songs", json={"title": title, "artist": artist, "video_id": video_id}
    )
    assert resp.status_code in (200, 201)
    song_id = resp.json()["id"]
    with _TestingSessionLocal() as session:
        db_song = session.get(DbSong, song_id)
        db_song.status = status
        if status == "error":
            db_song.error_message = "CUDA out of memory."
        session.commit()
    return song_id


def _status(song_id):
    with _TestingSessionLocal() as session:
        song = session.get(DbSong, song_id)
        return song.status, song.error_message


@pytest.fixture
def youtube_service():
    with (
        patch("app.services.youtube_service.YouTubeService") as service_cls,
        patch("app.api.songs.FileService"),
    ):
        service = service_cls.return_value
        service.download_and_process_async.return_value = "job-123"
        yield service


@pytest.fixture
def admin_forbidden(integration_app):
    """Make admin-only routes refuse, so a 202 proves the route isn't admin-only."""

    def _deny():
        raise HTTPException(status_code=403, detail="Admin required")

    integration_app.dependency_overrides[require_admin] = _deny
    try:
        yield
    finally:
        integration_app.dependency_overrides[require_admin] = _get_mock_user


class TestRetryFailedSong:
    def test_restarts_a_failed_song_from_its_own_source(self, client, youtube_service):
        song_id = _create_song(
            client,
            title="Big Dawgs",
            artist="Hanumankind",
            status="error",
            video_id="JCf7lKL1UQ4",
        )

        resp = client.post(f"/api/songs/{song_id}/retry")

        assert resp.status_code == 202
        assert resp.json() == {"jobId": "job-123", "status": "pending"}
        kwargs = youtube_service.download_and_process_async.call_args.kwargs
        assert kwargs["song_id"] == song_id
        assert kwargs["video_id_or_url"] == "JCf7lKL1UQ4"
        assert (kwargs["artist"], kwargs["title"]) == ("Hanumankind", "Big Dawgs")
        assert _status(song_id) == ("processing", None)

    def test_does_not_need_admin(self, client, youtube_service, admin_forbidden):
        song_id = _create_song(
            client, title="Big Dawgs", artist="Hanumankind", status="error"
        )

        assert client.post(f"/api/songs/{song_id}/retry").status_code == 202

    @pytest.mark.parametrize("status", ["processed", "processing"])
    def test_refuses_a_song_that_has_not_failed(self, client, youtube_service, status):
        song_id = _create_song(
            client, title="Fine Song", artist="Fine Artist", status=status
        )

        resp = client.post(f"/api/songs/{song_id}/retry")

        assert resp.status_code == 409
        youtube_service.download_and_process_async.assert_not_called()
        assert _status(song_id)[0] == status

    def test_refuses_a_song_with_no_youtube_source(self, client, youtube_service):
        song_id = _create_song(
            client, title="Uploaded", artist="Someone", status="error", video_id=None
        )

        assert client.post(f"/api/songs/{song_id}/retry").status_code == 400

    def test_refuses_while_a_job_is_in_flight(self, client, youtube_service):
        song_id = _create_song(
            client, title="Big Dawgs", artist="Hanumankind", status="error"
        )

        with patch("app.repositories.JobRepository") as repo_cls:
            repo_cls.return_value.get_in_flight_jobs.return_value = [
                type("Job", (), {"song_id": song_id})()
            ]
            resp = client.post(f"/api/songs/{song_id}/retry")

        assert resp.status_code == 409
        assert _status(song_id)[0] == "error"

    def test_unknown_song(self, client, youtube_service):
        assert client.post("/api/songs/does-not-exist/retry").status_code == 404


class TestSongbookHidesFailedSongs:
    @pytest.fixture
    def songs(self, client):
        return {
            "working": _create_song(
                client, title="Working Song", artist="Mixed Artist"
            ),
            "failed": _create_song(
                client, title="Failed Song", artist="Mixed Artist", status="error"
            ),
            "only_failed": _create_song(
                client, title="Big Dawgs", artist="Hanumankind", status="error"
            ),
            "in_progress": _create_song(
                client, title="New Song", artist="Mixed Artist", status="processing"
            ),
        }

    def test_song_list(self, client, songs):
        ids = {s["id"] for s in client.get("/api/songs").json()}

        assert {songs["working"], songs["in_progress"]} <= ids
        assert songs["failed"] not in ids
        assert songs["only_failed"] not in ids

    def test_search(self, client, songs):
        ids = {s["id"] for s in client.get("/api/songs/search?q=Song").json()["songs"]}

        assert ids == {songs["working"], songs["in_progress"]}

    def test_search_grouped_by_artist(self, client, songs):
        data = client.get("/api/songs/search?q=Song&group_by_artist=true").json()

        (artist,) = data["artists"]
        assert artist["songCount"] == 2
        assert {s["id"] for s in artist["songs"]} == {
            songs["working"],
            songs["in_progress"],
        }

    def test_artist_list_counts_and_drops(self, client, songs):
        artists = {
            a["name"]: a["songCount"]
            for a in client.get("/api/songs/artists").json()["artists"]
        }

        assert artists["Mixed Artist"] == 2
        assert "Hanumankind" not in artists

    def test_songs_by_artist(self, client, songs):
        data = client.get("/api/songs/by-artist/Mixed%20Artist").json()

        assert {s["id"] for s in data["songs"]} == {
            songs["working"],
            songs["in_progress"],
        }
        assert data["pagination"]["total"] == 2

    def test_shows(self, client, songs):
        with _TestingSessionLocal() as session:
            for key in ("working", "failed", "only_failed"):
                session.get(DbSong, songs[key]).show_name = "Hamilton"
            session.commit()

        shows = client.get("/api/songs/shows").json()["shows"]
        by_show = client.get("/api/songs/by-show/Hamilton").json()

        assert shows == [
            {
                "name": "Hamilton",
                "sortName": "hamilton",
                "songCount": 1,
                "firstLetter": "H",
            }
        ]
        assert [s["id"] for s in by_show["songs"]] == [songs["working"]]

    def test_failed_song_is_still_reachable_directly(self, client, songs):
        resp = client.get(f"/api/songs/{songs['failed']}")

        assert resp.status_code == 200
        assert resp.json()["status"] == "error"
