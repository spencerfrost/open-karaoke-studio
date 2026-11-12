"""
End-to-end tests of who may reach what, with no identity overrides.

The other endpoint tests sign in a mock admin, which passes every gate. These
run the real dependencies on real accounts, tokens and session devices, for the
paths a stranger could take: no credentials at all, a self-registered account,
a public demo host, or a member of a different session.
"""

from datetime import timedelta

import pytest

from app.db.models import KaraokeSession, PerformanceHistory, SessionDevice, User
from app.services.auth_service import create_access_token
from app.utils.clock import utc_now


def _account(db, username, **roles):
    user = User(username=username, display_name=username, **roles)
    user.set_password("password123")
    db.add(user)
    db.commit()
    return user


def _bearer(user):
    return {"Authorization": f"Bearer {create_access_token(user)}"}


def _device(session_id, device_id):
    return {"X-Session-ID": session_id, "X-Device-ID": device_id}


def _hosted_session(db, session_id, host, device_id="phone"):
    db.add(
        KaraokeSession(
            session_id=session_id,
            display_code=session_id,
            host_device_id=f"rest_{session_id.lower()}",
            host_user_id=host.id,
            expires_at=utc_now() + timedelta(hours=8),
        )
    )
    db.add(
        SessionDevice(
            session_id=session_id,
            device_id=device_id,
            device_type="performer",
            display_name="Sam",
        )
    )
    db.commit()


@pytest.fixture
def host(db):
    return _account(db, "host", is_host=True)


@pytest.fixture
def stranger(db):
    """A self-registered account: registration is open to anyone."""
    return _account(db, "stranger")


@pytest.fixture
def demo_host(db):
    """A public demo account: POST /api/demo/start hands these to anyone."""
    return _account(db, "demo", is_host=True, is_demo=True)


class TestAnonymousReads:
    """The library and its third-party proxies need an account or a session."""

    @pytest.mark.parametrize(
        "path",
        [
            "/api/songs",
            "/api/songs/search?q=queen",
            "/api/songs/artists",
            "/api/songs/shows",
            "/api/songs/by-artist/1",
            "/api/songs/by-show/Hamilton",
            "/api/songs/some-song-id",
            "/api/lyrics/languages",
            "/api/lyrics/search?track_name=a&artist_name=b",
            "/api/lyrics/search-synced?track_name=a&artist_name=b",
            "/api/lyrics/songs/some-song-id",
            "/api/lyrics/songs/some-song-id/alignment",
            "/api/youtube/search?query=queen",
            "/api/youtube-music/search?q=queen",
            "/api/youtube-music/suggestions?q=que",
            "/api/youtube-music/artist/UC123",
            "/api/sessions/ABCD/info",
            "/api/sessions/ABCD/playlist",
        ],
    )
    def test_no_credentials_is_403(self, unauthenticated_client, path):
        assert unauthenticated_client.get(path).status_code == 403

    def test_a_session_member_can_browse_the_library(
        self, unauthenticated_client, db, host
    ):
        _hosted_session(db, "ABCD", host)

        response = unauthenticated_client.get(
            "/api/songs", headers=_device("ABCD", "phone")
        )

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "path",
        [
            "/api/songs/some-song-id/thumbnail",
            "/api/songs/some-song-id/download/vocals",
            "/api/albums/1/cover",
            "/api/artists/1/image",
        ],
    )
    def test_media_urls_stay_reachable_without_headers(
        self, unauthenticated_client, path
    ):
        """<img> and <audio> can't send credentials; these 404, not 403."""
        assert unauthenticated_client.get(path).status_code == 404


class TestAccountsDontOpenOtherSessions:
    """Holding an account is not membership - that would skip join-by-code."""

    @pytest.mark.parametrize("who", ["stranger", "demo_host"])
    def test_queue(self, unauthenticated_client, db, host, who, request):
        _hosted_session(db, "ABCD", host)
        intruder = request.getfixturevalue(who)

        response = unauthenticated_client.get(
            "/api/karaoke-queue?session_code=ABCD", headers=_bearer(intruder)
        )

        assert response.status_code == 403

    @pytest.mark.parametrize("who", ["stranger", "demo_host"])
    def test_roster(self, unauthenticated_client, db, host, who, request):
        _hosted_session(db, "ABCD", host)
        intruder = request.getfixturevalue(who)

        response = unauthenticated_client.get(
            "/api/sessions/ABCD/performers", headers=_bearer(intruder)
        )

        assert response.status_code == 403

    def test_a_member_of_another_session_is_refused(
        self, unauthenticated_client, db, host
    ):
        _hosted_session(db, "ABCD", host)
        _hosted_session(db, "WXYZ", host, device_id="other-phone")

        response = unauthenticated_client.get(
            "/api/karaoke-queue?session_code=ABCD",
            headers=_device("WXYZ", "other-phone"),
        )

        assert response.status_code == 403

    def test_the_host_reaches_their_own_session(self, unauthenticated_client, db, host):
        _hosted_session(db, "ABCD", host)

        response = unauthenticated_client.get(
            "/api/karaoke-queue?session_code=ABCD", headers=_bearer(host)
        )

        assert response.status_code == 200


class TestSessionInfo:
    def test_a_member_sees_the_roster_and_itself(
        self, unauthenticated_client, db, host
    ):
        _hosted_session(db, "ABCD", host)

        response = unauthenticated_client.get(
            "/api/sessions/ABCD/info", headers=_device("ABCD", "phone")
        )

        assert response.status_code == 200
        body = response.json()
        assert body["is_host"] is False
        assert [d["is_self"] for d in body["connected_devices"]] == [True]

    def test_the_host_is_told_so_by_their_account(
        self, unauthenticated_client, db, host
    ):
        _hosted_session(db, "ABCD", host)

        response = unauthenticated_client.get(
            "/api/sessions/ABCD/info", headers=_bearer(host)
        )

        assert response.status_code == 200
        assert response.json()["is_host"] is True

    def test_a_device_id_query_param_proves_nothing(
        self, unauthenticated_client, db, host
    ):
        _hosted_session(db, "ABCD", host)

        response = unauthenticated_client.get(
            "/api/sessions/ABCD/info?device_id=rest_abcd"
        )

        assert response.status_code == 403

    @pytest.mark.parametrize("who", ["stranger", "demo_host"])
    def test_another_account_is_refused(
        self, unauthenticated_client, db, host, who, request
    ):
        _hosted_session(db, "ABCD", host)
        intruder = request.getfixturevalue(who)

        response = unauthenticated_client.get(
            "/api/sessions/ABCD/info", headers=_bearer(intruder)
        )

        assert response.status_code == 403


class TestSessionPlaylist:
    @pytest.mark.parametrize("who", ["host", "demo_host"])
    def test_only_the_sessions_own_host_may_create_it(
        self, unauthenticated_client, db, who, request
    ):
        owner = _account(db, "owner", is_host=True)
        _hosted_session(db, "ABCD", owner)
        other = request.getfixturevalue(who)

        response = unauthenticated_client.post(
            "/api/sessions/ABCD/playlist", headers=_bearer(other)
        )

        assert response.status_code == 404

    def test_a_plain_account_may_not(self, unauthenticated_client, db, host, stranger):
        _hosted_session(db, "ABCD", host)

        response = unauthenticated_client.post(
            "/api/sessions/ABCD/playlist", headers=_bearer(stranger)
        )

        assert response.status_code == 403

    def test_a_guest_may_not(self, unauthenticated_client, db, host):
        _hosted_session(db, "ABCD", host)

        response = unauthenticated_client.post(
            "/api/sessions/ABCD/playlist", headers=_device("ABCD", "phone")
        )

        # No bearer token at all: require_host's 401.
        assert response.status_code == 401


class TestHostWideEndpoints:
    """A host account isn't trusted with other sessions: demo hosts are public."""

    @pytest.mark.parametrize(
        "method, path",
        [
            ("get", "/api/jobs"),
            ("get", "/api/jobs/status"),
            ("get", "/api/jobs/some-job"),
            ("post", "/api/jobs/some-job/cancel"),
            ("get", "/api/lyrics/reports"),
            ("post", "/api/lyrics/reports/1/resolve"),
            ("post", "/api/lyrics/reports/1/undo"),
            ("get", "/api/lyrics/batch/align"),
            ("get", "/api/songs/duplicates"),
            ("get", "/api/songs/library-audit"),
            ("get", "/api/songs/metadata-audit"),
            ("get", "/api/songs/by-fingerprint-status?status=pending"),
        ],
    )
    def test_admin_only(self, unauthenticated_client, demo_host, method, path):
        response = getattr(unauthenticated_client, method)(
            path, headers=_bearer(demo_host)
        )

        assert response.status_code == 403

    def test_performance_history_shows_a_host_only_their_sessions(
        self, unauthenticated_client, db, host, demo_host
    ):
        _hosted_session(db, "ABCD", host)
        _hosted_session(db, "DEMO", demo_host, device_id="demo-phone")
        for session_id, singer in (("ABCD", "Real Guest"), ("DEMO", "Visitor")):
            db.add(
                PerformanceHistory(
                    session_id=session_id, singer_name=singer, performed_at=utc_now()
                )
            )
        db.commit()

        response = unauthenticated_client.get(
            "/api/performance-history", headers=_bearer(demo_host)
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert [i["singer_name"] for i in body["items"]] == ["Visitor"]

    def test_performance_history_shows_an_admin_everything(
        self, unauthenticated_client, db, host
    ):
        admin = _account(db, "admin", is_admin=True)
        _hosted_session(db, "ABCD", host)
        db.add(
            PerformanceHistory(
                session_id="ABCD", singer_name="Real Guest", performed_at=utc_now()
            )
        )
        db.commit()

        response = unauthenticated_client.get(
            "/api/performance-history", headers=_bearer(admin)
        )

        assert response.json()["total"] == 1


def test_a_plain_account_cannot_start_a_session(unauthenticated_client, stranger):
    response = unauthenticated_client.post("/api/sessions", headers=_bearer(stranger))

    assert response.status_code == 403
