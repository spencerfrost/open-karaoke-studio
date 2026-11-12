"""
Tests for /api/host-settings, including the demo guard and the
Float session_duration_hours (needed for 15-minute demo sessions).
"""

from tests.api.conftest import _get_mock_user

from app.api.dependencies import get_current_user
from app.db.models import HostSettings, User


class TestHostSettingsFloatDuration:
    def test_get_returns_fractional_duration(self, client, db):
        """A 0.25h (15-min) duration round-trips through the API as a float."""
        # The mock host user has id=1; seed its settings directly.
        db.add(
            HostSettings(
                user_id=1,
                session_duration_hours=0.25,
            )
        )
        db.commit()

        response = client.get("/api/host-settings")
        assert response.status_code == 200
        assert response.json()["session_duration_hours"] == 0.25

    def test_update_accepts_fractional_duration(self, client):
        response = client.put(
            "/api/host-settings", json={"session_duration_hours": 0.5}
        )
        assert response.status_code == 200
        assert response.json()["session_duration_hours"] == 0.5


class TestHostSettingsDemoGuard:
    def test_demo_account_cannot_update(self, client, db, fastapi_app):
        """Demo accounts can't change host settings (e.g. widen session length)."""
        demo = User(username="demo-host")
        demo.set_password("secret")
        demo.is_host = True
        demo.is_demo = True
        db.add(demo)
        db.commit()
        db.refresh(demo)

        fastapi_app.dependency_overrides[get_current_user] = lambda: demo
        try:
            response = client.put(
                "/api/host-settings", json={"session_duration_hours": 24}
            )
            assert response.status_code == 403
        finally:
            fastapi_app.dependency_overrides[get_current_user] = _get_mock_user


def test_get_host_settings_creates_defaults(client):
    """GET /api/host-settings returns defaults when no settings exist."""
    resp = client.get("/api/host-settings")
    assert resp.status_code == 200
    assert "session_duration_hours" in resp.json()


def test_get_host_settings_idempotent(client):
    """Calling GET twice returns the same settings."""
    r1 = client.get("/api/host-settings")
    r2 = client.get("/api/host-settings")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["session_duration_hours"] == r2.json()["session_duration_hours"]


def test_update_host_settings_session_duration(client):
    """PUT /api/host-settings can set session_duration_hours."""
    resp = client.put("/api/host-settings", json={"session_duration_hours": 4})
    assert resp.status_code == 200
    assert resp.json()["session_duration_hours"] == 4


def test_update_host_settings_empty_body_leaves_value_unchanged(client):
    """PUT with no fields set is a no-op rather than a reset."""
    client.put("/api/host-settings", json={"session_duration_hours": 6})
    resp = client.put("/api/host-settings", json={})
    assert resp.status_code == 200
    assert resp.json()["session_duration_hours"] == 6


def test_update_host_settings_rejects_out_of_range_duration(client):
    """session_duration_hours is bounded to (0, 24]."""
    assert (
        client.put("/api/host-settings", json={"session_duration_hours": 0}).status_code
        == 422
    )
    assert (
        client.put(
            "/api/host-settings", json={"session_duration_hours": 25}
        ).status_code
        == 422
    )
