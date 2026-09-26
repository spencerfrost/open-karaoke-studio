"""
Tests for demo download quota enforcement in POST /api/youtube/download.

Quotas: 3 downloads per demo session, 20/day across all demo sessions.
Non-demo requesters are never counted and keep their behavior unchanged.
"""

from datetime import datetime, timedelta

import pytest
from app.api.dependencies import RequesterContext, require_host_or_session_member
from app.db.models import DbJob, DbSong, KaraokeSession, User


@pytest.fixture
def override_requester(fastapi_app):
    """Override the download auth dependency for the duration of a test."""

    def _apply(context: RequesterContext):
        fastapi_app.dependency_overrides[require_host_or_session_member] = (
            lambda: context
        )

    yield _apply

    from tests.fastapi.conftest import _get_mock_requester

    fastapi_app.dependency_overrides[require_host_or_session_member] = (
        _get_mock_requester
    )


def _make_demo_user(user_db, username="demo-pool-1"):
    user = User(username=username, display_name="Demo Host")
    user.set_password("secret")
    user.is_host = True
    user.is_demo = True
    user_db.add(user)
    user_db.commit()
    user_db.refresh(user)
    return user


def _make_session(user_db, host_user_id, session_id="AAAA"):
    session = KaraokeSession(
        session_id=session_id,
        display_code=session_id,
        host_device_id="demo_device",
        host_user_id=host_user_id,
        expires_at=datetime.utcnow() + timedelta(minutes=15),
        is_active=True,
    )
    user_db.add(session)
    user_db.commit()
    return session


def _make_jobs(user_db, session_id, count, created_at=None):
    for i in range(count):
        user_db.add(
            DbJob(
                id=f"{session_id}-job-{i}-{datetime.utcnow().timestamp()}",
                filename="original.mp3",
                status="completed",
                session_id=session_id,
                created_at=created_at or datetime.utcnow(),
            )
        )
    user_db.commit()


def _download(client):
    return client.post(
        "/api/youtube/download",
        json={
            "video_id": "dQw4w9WgXcQ",
            "song_id": "song-xyz",
            "title": "T",
            "artist": "A",
        },
    )


def _create_song(client):
    return client.post(
        "/api/songs",
        json={"title": "T", "artist": "A", "source": "youtube", "video_id": "vid"},
    )


class TestDemoSessionCap:
    def test_guest_under_cap_succeeds_with_attribution(
        self, client, user_db, mock_youtube_service, override_requester
    ):
        demo = _make_demo_user(user_db)
        _make_session(user_db, demo.id, "SESS")
        _make_jobs(user_db, "SESS", 2)

        override_requester(RequesterContext(session_id="SESS"))
        response = _download(client)

        assert response.status_code == 202
        _, kwargs = mock_youtube_service.download_and_process_async.call_args
        assert kwargs["session_id"] == "SESS"
        assert kwargs["user_id"] is None

    def test_guest_at_cap_returns_429(
        self, client, user_db, mock_youtube_service, override_requester
    ):
        demo = _make_demo_user(user_db)
        _make_session(user_db, demo.id, "SESS")
        _make_jobs(user_db, "SESS", 3)

        override_requester(RequesterContext(session_id="SESS"))
        response = _download(client)

        assert response.status_code == 429
        assert "3 new songs" in response.json()["detail"]
        mock_youtube_service.download_and_process_async.assert_not_called()


class TestDemoDailyCap:
    def test_daily_cap_across_pool_returns_429(
        self, client, user_db, mock_youtube_service, override_requester
    ):
        demo = _make_demo_user(user_db)
        # Spread 20 recent jobs across two demo-hosted sessions.
        _make_session(user_db, demo.id, "S1")
        _make_session(user_db, demo.id, "S2")
        _make_jobs(user_db, "S1", 1)  # target session under its own 3-cap
        _make_jobs(user_db, "S2", 19)

        override_requester(RequesterContext(session_id="S1"))
        response = _download(client)

        assert response.status_code == 429
        assert "daily" in response.json()["detail"].lower()

    def test_old_jobs_do_not_count_toward_daily_cap(
        self, client, user_db, mock_youtube_service, override_requester
    ):
        demo = _make_demo_user(user_db)
        _make_session(user_db, demo.id, "S1")
        _make_session(user_db, demo.id, "S2")
        _make_jobs(user_db, "S1", 1)
        _make_jobs(
            user_db, "S2", 19, created_at=datetime.utcnow() - timedelta(hours=25)
        )

        override_requester(RequesterContext(session_id="S1"))
        response = _download(client)

        assert response.status_code == 202


class TestDemoJwtRequester:
    def test_demo_jwt_with_active_session_attributes_user(
        self, client, user_db, mock_youtube_service, override_requester
    ):
        demo = _make_demo_user(user_db)
        _make_session(user_db, demo.id, "SESS")

        override_requester(RequesterContext(user=demo))
        response = _download(client)

        assert response.status_code == 202
        _, kwargs = mock_youtube_service.download_and_process_async.call_args
        assert kwargs["session_id"] == "SESS"
        assert kwargs["user_id"] == demo.id

    def test_demo_jwt_without_session_returns_403(
        self, client, user_db, mock_youtube_service, override_requester
    ):
        demo = _make_demo_user(user_db)

        override_requester(RequesterContext(user=demo))
        response = _download(client)

        assert response.status_code == 403
        assert "ended" in response.json()["detail"].lower()


class TestNonDemoUnaffected:
    def test_non_demo_host_never_counted(
        self, client, user_db, mock_youtube_service, override_requester
    ):
        host = User(username="realhost", display_name="Real Host")
        host.set_password("secret")
        host.is_host = True
        user_db.add(host)
        user_db.commit()
        user_db.refresh(host)
        _make_session(user_db, host.id, "REAL")
        _make_jobs(user_db, "REAL", 5)  # well over the demo cap

        override_requester(RequesterContext(session_id="REAL"))
        response = _download(client)

        assert response.status_code == 202
        _, kwargs = mock_youtube_service.download_and_process_async.call_args
        assert kwargs["session_id"] == "REAL"


@pytest.fixture
def override_songs_db(fastapi_app):
    """songs.py defines its own local get_db; the shared conftest only overrides
    dependencies.get_db, so create_song would otherwise hit the real database."""
    import app.api.songs as songs_api
    from tests.fastapi.conftest import _get_test_db

    fastapi_app.dependency_overrides[songs_api.get_db] = _get_test_db
    yield
    fastapi_app.dependency_overrides.pop(songs_api.get_db, None)


class TestCreateSongQuota:
    """The add-song flow calls POST /api/songs before POST /download, so the
    quota is enforced at song creation too — otherwise an over-quota demo user
    would leave orphaned, track-less songs in the library."""

    def test_over_cap_create_song_rejected_and_not_persisted(
        self, client, user_db, override_requester, override_songs_db
    ):
        demo = _make_demo_user(user_db)
        _make_session(user_db, demo.id, "SESS")
        _make_jobs(user_db, "SESS", 3)

        override_requester(RequesterContext(session_id="SESS"))
        response = _create_song(client)

        assert response.status_code == 429
        assert "3 new songs" in response.json()["detail"]
        # No orphaned song row was created.
        assert user_db.query(DbSong).count() == 0

    def test_under_cap_create_song_allowed(
        self, client, user_db, override_requester, override_songs_db
    ):
        demo = _make_demo_user(user_db)
        _make_session(user_db, demo.id, "SESS")
        _make_jobs(user_db, "SESS", 1)

        override_requester(RequesterContext(session_id="SESS"))
        response = _create_song(client)

        assert response.status_code == 201
