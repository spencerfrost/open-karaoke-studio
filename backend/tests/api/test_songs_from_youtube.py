"""POST /api/songs/from-youtube: add a song and queue its download in one request."""

from unittest.mock import AsyncMock, patch

import pytest
from tests.api.test_demo_quota import override_requester  # noqa: F401 (fixture)
from tests.api.test_demo_quota import (
    _make_demo_user,
    _make_jobs,
    _make_session,
)

from app.api.dependencies import RequesterContext
from app.db.database import SessionLocal
from app.db.models import DbSong
from app.services.demo_service import DEMO_SESSION_DOWNLOAD_LIMIT
from app.utils.owner_tag import session_owner_tag

BODY = {
    "video_id": "HgzGwKwLmgM",
    "title": "Don't Stop Me Now",
    "artists": [{"name": "Queen", "id": "UC-queen"}],
    "album": "Jazz",
    "duration": 210,
}


@pytest.fixture
def youtube_service():
    with (
        patch("app.services.youtube_service.YouTubeService") as service_cls,
        patch("app.services.song_intake_service.FileService"),
    ):
        service = service_cls.return_value
        service.download_and_process_async.return_value = "job-123"
        yield service


@pytest.fixture
def broadcast():
    with patch("app.api.songs.broadcast_job_created", new_callable=AsyncMock) as mock:
        yield mock


def _songs():
    with SessionLocal() as session:
        return [
            (s.id, s.title, s.artist, s.status, s.video_id)
            for s in session.query(DbSong).all()
        ]


def _add_song(**fields):
    with SessionLocal() as session:
        song = DbSong(id=fields.pop("id"), **fields)
        session.add(song)
        session.commit()


class TestAddSong:
    def test_creates_the_song_and_queues_it(self, client, youtube_service, broadcast):
        response = client.post("/api/songs/from-youtube", json=BODY)

        assert response.status_code == 202
        data = response.json()
        assert data["jobId"] == "job-123"
        assert data["restarted"] is False

        [(song_id, title, artist, status, video_id)] = _songs()
        assert song_id == data["songId"]
        assert (title, artist, video_id) == (
            "Don't Stop Me Now",
            "Queen",
            "HgzGwKwLmgM",
        )

        kwargs = youtube_service.download_and_process_async.call_args.kwargs
        assert kwargs["song_id"] == song_id
        assert kwargs["video_id_or_url"] == "HgzGwKwLmgM"
        assert kwargs["engine_type"] == "three_track"

    def test_broadcasts_the_job(self, client, youtube_service, broadcast):
        song_id = client.post("/api/songs/from-youtube", json=BODY).json()["songId"]

        _, job = broadcast.call_args.args
        assert job["id"] == "job-123"
        assert job["song_id"] == song_id
        assert job["status"] == "pending"
        assert job["step"] == "download"

    def test_keeps_every_artist(self, client, youtube_service, broadcast):
        body = {**BODY, "title": "Empire State of Mind"}
        body["artists"] = [{"name": "JAY-Z"}, {"name": "Alicia Keys", "id": "UC-ak"}]

        song_id = client.post("/api/songs/from-youtube", json=body).json()["songId"]

        with SessionLocal() as session:
            song = session.get(DbSong, song_id)
            assert song.artist == "JAY-Z feat. Alicia Keys"
            credited = [
                (
                    sa.artist_rel.display_name,
                    sa.role,
                    sa.artist_rel.youtube_music_artist_id,
                )
                for sa in sorted(song.song_artists, key=lambda sa: sa.display_order)
            ]
        assert credited == [
            ("JAY-Z", "primary", None),
            ("Alicia Keys", "featured", "UC-ak"),
        ]

    def test_a_plain_video_keeps_no_channel_id(
        self, client, youtube_service, broadcast
    ):
        body = {**BODY, "source": "youtube"}

        song_id = client.post("/api/songs/from-youtube", json=body).json()["songId"]

        with SessionLocal() as session:
            [credit] = session.get(DbSong, song_id).song_artists
            assert credit.artist_rel.youtube_music_artist_id is None

    def test_rejects_a_missing_artist(self, client, youtube_service, broadcast):
        response = client.post(
            "/api/songs/from-youtube", json={**BODY, "artists": [{"name": "  "}]}
        )
        assert response.status_code == 422
        assert _songs() == []


class TestExistingCopies:
    def test_restarts_the_failed_copy(self, client, youtube_service, broadcast):
        _add_song(
            id="failed-1",
            title="Don't Stop Me Now",
            artist="Queen",
            status="error",
            error_message="CUDA out of memory.",
            video_id="HgzGwKwLmgM",
        )

        response = client.post("/api/songs/from-youtube", json=BODY)

        assert response.status_code == 202
        assert response.json() == {
            "songId": "failed-1",
            "jobId": "job-123",
            "restarted": True,
        }
        # No duplicate: the failed row is processing again
        assert _songs() == [
            ("failed-1", "Don't Stop Me Now", "Queen", "processing", "HgzGwKwLmgM")
        ]
        assert broadcast.call_args.args[1]["song_id"] == "failed-1"

    def test_restarts_a_failed_copy_from_the_chosen_video(
        self, client, youtube_service, broadcast
    ):
        _add_song(
            id="failed-1",
            title="don't stop me now",
            artist="QUEEN",
            status="error",
            video_id="oldVideo",
        )

        client.post("/api/songs/from-youtube", json=BODY)

        assert _songs()[0][4] == "HgzGwKwLmgM"
        kwargs = youtube_service.download_and_process_async.call_args.kwargs
        assert kwargs["video_id_or_url"] == "HgzGwKwLmgM"

    @pytest.mark.parametrize("status", ["processed", "processing"])
    def test_working_copy_is_a_409(self, client, youtube_service, broadcast, status):
        _add_song(
            id="working-1",
            title="Don't Stop Me Now",
            artist="Queen",
            status=status,
            video_id="HgzGwKwLmgM",
        )

        response = client.post("/api/songs/from-youtube", json=BODY)

        assert response.status_code == 409
        youtube_service.download_and_process_async.assert_not_called()
        broadcast.assert_not_called()
        assert len(_songs()) == 1


class TestDemoQuota:
    def test_checks_the_quota_once(self, client, youtube_service, broadcast):
        with patch(
            "app.services.song_intake_service.enforce_demo_download_quota",
            return_value=(None, None),
        ) as enforce:
            client.post("/api/songs/from-youtube", json=BODY)
        assert enforce.call_count == 1

    def test_over_cap_adds_nothing(
        self, client, db, youtube_service, broadcast, override_requester
    ):
        demo = _make_demo_user(db)
        _make_session(db, demo.id, "SESS")
        _make_jobs(db, "SESS", DEMO_SESSION_DOWNLOAD_LIMIT)
        override_requester(RequesterContext(session_id="SESS"))

        response = client.post("/api/songs/from-youtube", json=BODY)

        assert response.status_code == 429
        assert _songs() == []
        youtube_service.download_and_process_async.assert_not_called()

    def test_under_cap_attributes_the_job_to_the_session(
        self, client, db, youtube_service, broadcast, override_requester
    ):
        demo = _make_demo_user(db)
        _make_session(db, demo.id, "SESS")
        override_requester(RequesterContext(session_id="SESS"))

        response = client.post("/api/songs/from-youtube", json=BODY)

        assert response.status_code == 202
        kwargs = youtube_service.download_and_process_async.call_args.kwargs
        assert kwargs["session_id"] == "SESS"
        assert broadcast.call_args.args[1]["owner_tag"] == session_owner_tag("SESS")
