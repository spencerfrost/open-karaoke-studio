"""
Tests for host settings endpoints, including the demo guard and the
Float session_duration_hours (needed for 15-minute demo sessions).
"""

from app.api.dependencies import get_current_user
from app.db.models import HostSettings, User


class TestHostSettingsFloatDuration:
    def test_get_returns_fractional_duration(self, client, user_db):
        """A 0.25h (15-min) duration round-trips through the API as a float."""
        # The mock host user has id=1; seed its settings directly.
        user_db.add(
            HostSettings(
                user_id=1,
                session_duration_hours=0.25,
            )
        )
        user_db.commit()

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
    def test_demo_account_cannot_update(self, client, user_db, fastapi_app):
        """Demo accounts can't change host settings (e.g. widen session length)."""
        demo = User(username="demo-host")
        demo.set_password("secret")
        demo.is_host = True
        demo.is_demo = True
        user_db.add(demo)
        user_db.commit()
        user_db.refresh(demo)

        fastapi_app.dependency_overrides[get_current_user] = lambda: demo
        try:
            response = client.put(
                "/api/host-settings", json={"session_duration_hours": 24}
            )
            assert response.status_code == 403
        finally:
            from tests.fastapi.conftest import _get_mock_user

            fastapi_app.dependency_overrides[get_current_user] = _get_mock_user
