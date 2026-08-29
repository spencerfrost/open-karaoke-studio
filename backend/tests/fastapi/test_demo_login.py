"""
Tests for the demo account pool alias login.

The alias (DEMO_LOGIN_USERNAME / DEMO_LOGIN_PASSWORD) resolves to a free
`is_demo` pool account and eagerly starts that account's karaoke session.
"""

from datetime import datetime, timedelta

import pytest
from app.db.models import HostSettings, KaraokeSession, User

ALIAS_USERNAME = "demo"
ALIAS_PASSWORD = "public-demo-pw"


@pytest.fixture(autouse=True)
def _disable_limiter():
    """Login is rate-limited 5/min per IP; these tests exceed that."""
    from app.limiter import limiter

    previous = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = previous


@pytest.fixture
def demo_env(monkeypatch):
    monkeypatch.setenv("DEMO_LOGIN_USERNAME", ALIAS_USERNAME)
    monkeypatch.setenv("DEMO_LOGIN_PASSWORD", ALIAS_PASSWORD)


def _seed_pool(user_db, count=3):
    """Create `count` demo pool accounts, each with demo host settings."""
    created = []
    for i in range(1, count + 1):
        user = User(username=f"demo-pool-{i}", display_name="Demo Host")
        user.set_password(f"pool-secret-{i}")
        user.is_host = True
        user.is_demo = True
        user_db.add(user)
        user_db.commit()
        user_db.refresh(user)
        user_db.add(
            HostSettings(
                user_id=user.id,
                session_duration_hours=0.25,
            )
        )
        user_db.commit()
        created.append(user)
    return created


def _login(client, username, password):
    return client.post(
        "/api/users/login", json={"username": username, "password": password}
    )


class TestDemoFeatureDisabled:
    def test_alias_creds_rejected_when_env_unset(self, client, user_db):
        """Without the env vars, alias creds are just an invalid login."""
        _seed_pool(user_db)
        response = _login(client, ALIAS_USERNAME, ALIAS_PASSWORD)
        assert response.status_code == 401

    def test_normal_login_still_works_when_disabled(self, client, user_db):
        user = User(username="realuser", display_name="Real User")
        user.set_password("realpassword")
        user_db.add(user)
        user_db.commit()

        response = _login(client, "realuser", "realpassword")
        assert response.status_code == 200
        assert response.json()["display_name"] == "Real User"


class TestDemoAliasLogin:
    def test_alias_login_resolves_pool_account_and_starts_session(
        self, client, user_db, demo_env
    ):
        pool = _seed_pool(user_db)
        pool_ids = {u.id for u in pool}

        response = _login(client, ALIAS_USERNAME, ALIAS_PASSWORD)
        assert response.status_code == 200
        data = response.json()
        assert int(data["id"]) in pool_ids
        assert data["is_host"] is True
        assert data["is_admin"] is False
        assert data["token"]

        session = (
            user_db.query(KaraokeSession)
            .filter(KaraokeSession.host_user_id == int(data["id"]))
            .first()
        )
        assert session is not None
        span = session.expires_at - session.created_at
        # 0.25h session ≈ 15 minutes.
        assert abs(span - timedelta(minutes=15)) < timedelta(minutes=1)

    def test_second_login_picks_different_account(self, client, user_db, demo_env):
        _seed_pool(user_db)
        first = _login(client, ALIAS_USERNAME, ALIAS_PASSWORD).json()
        second = _login(client, ALIAS_USERNAME, ALIAS_PASSWORD).json()
        assert first["id"] != second["id"]

    def test_pool_exhausted_returns_503(self, client, user_db, demo_env):
        _seed_pool(user_db, count=2)
        _login(client, ALIAS_USERNAME, ALIAS_PASSWORD)
        _login(client, ALIAS_USERNAME, ALIAS_PASSWORD)
        third = _login(client, ALIAS_USERNAME, ALIAS_PASSWORD)
        assert third.status_code == 503
        assert "busy" in third.json()["detail"].lower()

    def test_expired_session_frees_account(self, client, user_db, demo_env):
        _seed_pool(user_db, count=1)
        first = _login(client, ALIAS_USERNAME, ALIAS_PASSWORD)
        assert first.status_code == 200
        first_id = int(first.json()["id"])

        # A single-account pool is now busy.
        assert _login(client, ALIAS_USERNAME, ALIAS_PASSWORD).status_code == 503

        # Backdate the session past its expiry; the account frees up.
        session = (
            user_db.query(KaraokeSession)
            .filter(KaraokeSession.host_user_id == first_id)
            .first()
        )
        session.expires_at = datetime.utcnow() - timedelta(minutes=1)
        user_db.commit()

        reused = _login(client, ALIAS_USERNAME, ALIAS_PASSWORD)
        assert reused.status_code == 200
        assert int(reused.json()["id"]) == first_id

    def test_alias_username_wrong_password_falls_through(
        self, client, user_db, demo_env
    ):
        """Wrong alias password ⇒ normal login path ⇒ 401, no account consumed."""
        _seed_pool(user_db, count=1)
        response = _login(client, ALIAS_USERNAME, "not-the-alias-password")
        assert response.status_code == 401
        # Pool account remains free.
        assert user_db.query(KaraokeSession).count() == 0

    def test_pool_account_own_password_logs_in_normally(
        self, client, user_db, demo_env
    ):
        """A pool account's individual password logs in without a demo session."""
        _seed_pool(user_db, count=1)
        response = _login(client, "demo-pool-1", "pool-secret-1")
        assert response.status_code == 200
        assert int(response.json()["id"])
        # Normal login does not eagerly create a session.
        assert user_db.query(KaraokeSession).count() == 0
