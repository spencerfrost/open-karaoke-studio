"""
Tests for POST /api/demo/start.

Each start hands the visitor a free `is_demo` pool account, eagerly starts
that account's karaoke session, and returns a login-shaped payload. No
credential is involved.
"""

import time
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from tests.conftest import create_test_app

from app.db.models import HostSettings, KaraokeSession, User
from app.limiter import limiter
from app.services.auth_service import verify_token
from app.utils.clock import utc_now


@pytest.fixture(autouse=True)
def _disable_limiter():
    """The start endpoint is rate-limited per IP; most tests exceed that."""
    previous = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = previous


def _seed_pool(db, count=3):
    """Create `count` demo pool accounts, each with demo host settings."""
    created = []
    for i in range(1, count + 1):
        user = User(username=f"demo-pool-{i}", display_name="Demo Host")
        user.set_password(f"pool-secret-{i}")
        user.is_host = True
        user.is_demo = True
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(
            HostSettings(
                user_id=user.id,
                session_duration_hours=0.25,
            )
        )
        db.commit()
        created.append(user)
    return created


def _start(client):
    return client.post("/api/demo/start")


class TestDemoStatus:
    def test_disabled_without_pool(self, unauthenticated_client):
        response = unauthenticated_client.get("/api/demo")
        assert response.status_code == 200
        assert response.json() == {"enabled": False}

    def test_enabled_with_pool(self, unauthenticated_client, db):
        _seed_pool(db, count=1)
        assert unauthenticated_client.get("/api/demo").json() == {"enabled": True}


class TestDemoStart:
    def test_start_picks_pool_account_and_starts_session(
        self, unauthenticated_client, db
    ):
        pool = _seed_pool(db)
        pool_ids = {u.id for u in pool}

        response = _start(unauthenticated_client)
        assert response.status_code == 200
        data = response.json()
        assert int(data["id"]) in pool_ids
        assert data["is_host"] is True
        assert data["is_admin"] is False
        assert data["is_demo"] is True
        assert data["token"]

        session = (
            db.query(KaraokeSession)
            .filter(KaraokeSession.host_user_id == int(data["id"]))
            .first()
        )
        assert session is not None
        span = session.expires_at - session.created_at
        # 0.25h session ≈ 15 minutes.
        assert abs(span - timedelta(minutes=15)) < timedelta(minutes=1)

    def test_token_expires_with_the_session(self, unauthenticated_client, db):
        _seed_pool(db, count=1)
        data = _start(unauthenticated_client).json()
        payload = verify_token(data["token"])
        assert payload is not None

        session = (
            db.query(KaraokeSession)
            .filter(KaraokeSession.host_user_id == int(data["id"]))
            .one()
        )
        session_left = (session.expires_at - utc_now()).total_seconds()
        token_left = payload["exp"] - time.time()
        assert 0 < token_left <= 15 * 60
        assert abs(token_left - session_left) < 5

    def test_second_start_picks_different_account(self, unauthenticated_client, db):
        _seed_pool(db)
        first = _start(unauthenticated_client).json()
        second = _start(unauthenticated_client).json()
        assert first["id"] != second["id"]

    def test_pool_exhausted_returns_503(self, unauthenticated_client, db):
        _seed_pool(db, count=2)
        _start(unauthenticated_client)
        _start(unauthenticated_client)
        third = _start(unauthenticated_client)
        assert third.status_code == 503
        assert "busy" in third.json()["detail"].lower()

    def test_no_pool_returns_503(self, unauthenticated_client, db):
        response = _start(unauthenticated_client)
        assert response.status_code == 503
        assert db.query(KaraokeSession).count() == 0

    def test_expired_session_frees_account(self, unauthenticated_client, db):
        _seed_pool(db, count=1)
        first = _start(unauthenticated_client)
        assert first.status_code == 200
        first_id = int(first.json()["id"])

        # A single-account pool is now busy.
        assert _start(unauthenticated_client).status_code == 503

        # Backdate the session past its expiry; the account frees up.
        session = (
            db.query(KaraokeSession)
            .filter(KaraokeSession.host_user_id == first_id)
            .first()
        )
        session.expires_at = utc_now() - timedelta(minutes=1)
        db.commit()

        reused = _start(unauthenticated_client)
        assert reused.status_code == 200
        assert int(reused.json()["id"]) == first_id


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestDemoAccountSessions:
    """A demo account's only session is the one /api/demo/start opened."""

    def test_stage_joins_the_started_session(self, unauthenticated_client, db):
        _seed_pool(db, count=1)
        token = _start(unauthenticated_client).json()["token"]
        started = db.query(KaraokeSession).one()

        response = unauthenticated_client.post(
            "/api/sessions/my", json={"device_type": "stage"}, headers=_auth(token)
        )

        assert response.status_code == 201
        assert response.json()["session_id"] == started.session_id
        assert db.query(KaraokeSession).count() == 1

    def test_guest_joining_the_demo_session_is_told_so(
        self, unauthenticated_client, db
    ):
        _seed_pool(db, count=1)
        _start(unauthenticated_client)
        started = db.query(KaraokeSession).one()

        response = unauthenticated_client.post(
            "/api/sessions/join-by-code",
            json={
                "code": started.display_code,
                "device_type": "performer",
                "display_name": "Guest",
            },
        )

        assert response.status_code == 200
        assert response.json()["is_demo"] is True

    def test_no_new_session_after_the_demo_session_ends(
        self, unauthenticated_client, db
    ):
        _seed_pool(db, count=1)
        token = _start(unauthenticated_client).json()["token"]
        session = db.query(KaraokeSession).one()
        session.expires_at = utc_now() - timedelta(minutes=1)
        db.commit()

        response = unauthenticated_client.post(
            "/api/sessions/my", json={"device_type": "stage"}, headers=_auth(token)
        )

        assert response.status_code == 403
        assert "Try it live" in response.json()["detail"]
        live = db.query(KaraokeSession).filter(KaraokeSession.is_active.is_(True))
        assert live.count() == 0

    def test_cannot_replace_the_demo_session(self, unauthenticated_client, db):
        _seed_pool(db, count=1)
        token = _start(unauthenticated_client).json()["token"]
        started = db.query(KaraokeSession).one()

        response = unauthenticated_client.post(
            "/api/sessions/my",
            json={"device_type": "stage", "on_existing": "replace"},
            headers=_auth(token),
        )

        assert response.status_code == 403
        db.refresh(started)
        assert started.is_active is True
        assert db.query(KaraokeSession).count() == 1

    def test_password_login_cannot_create_a_session(self, unauthenticated_client, db):
        _seed_pool(db, count=1)
        token = unauthenticated_client.post(
            "/api/users/login",
            json={"username": "demo-pool-1", "password": "pool-secret-1"},
        ).json()["token"]

        response = unauthenticated_client.post(
            "/api/sessions/my", json={"device_type": "stage"}, headers=_auth(token)
        )

        assert response.status_code == 403
        assert db.query(KaraokeSession).count() == 0

    def test_plain_session_create_rejected(self, unauthenticated_client, db):
        _seed_pool(db, count=1)
        token = _start(unauthenticated_client).json()["token"]

        response = unauthenticated_client.post(
            "/api/sessions", json={"device_type": "stage"}, headers=_auth(token)
        )

        assert response.status_code == 403
        assert db.query(KaraokeSession).count() == 1


class TestDemoStartRateLimit:
    @pytest.fixture
    def limited_client(self):
        """A test app wired with the limiter the way main.py wires it."""
        app = create_test_app()
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        limiter.enabled = True
        limiter.reset()
        with TestClient(app) as client:
            yield client
        limiter.reset()

    def test_rate_limited_per_ip(self, limited_client, db):
        _seed_pool(db, count=1)
        statuses = [_start(limited_client).status_code for _ in range(6)]
        # Busy responses count too: one success, four 503s, then the limit.
        assert statuses == [200, 503, 503, 503, 503, 429]


class TestLoginAfterAliasRemoval:
    def test_pool_account_own_password_logs_in_without_session(
        self, unauthenticated_client, db
    ):
        """A pool account's own password is a normal login: no demo session."""
        _seed_pool(db, count=1)
        response = unauthenticated_client.post(
            "/api/users/login",
            json={"username": "demo-pool-1", "password": "pool-secret-1"},
        )
        assert response.status_code == 200
        assert response.json()["is_demo"] is True
        assert db.query(KaraokeSession).count() == 0

    def test_normal_login_reports_not_demo(self, unauthenticated_client, db):
        user = User(username="realuser", display_name="Real User")
        user.set_password("realpassword")
        db.add(user)
        db.commit()

        response = unauthenticated_client.post(
            "/api/users/login",
            json={"username": "realuser", "password": "realpassword"},
        )
        assert response.status_code == 200
        assert response.json()["is_demo"] is False
