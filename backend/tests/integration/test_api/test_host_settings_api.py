"""Integration tests for /api/host-settings REST endpoints."""


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
