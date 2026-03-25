"""Integration tests for /api/host-settings REST endpoints."""


def test_get_host_settings_creates_defaults(client):
    """GET /api/host-settings returns defaults when no settings exist."""
    resp = client.get("/api/host-settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "queue_submission_mode" in data
    assert "queue_open" in data


def test_get_host_settings_idempotent(client):
    """Calling GET twice returns the same settings."""
    r1 = client.get("/api/host-settings")
    r2 = client.get("/api/host-settings")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["queue_open"] == r2.json()["queue_open"]


def test_update_host_settings_queue_open(client):
    """PUT /api/host-settings can toggle queue_open."""
    resp = client.put("/api/host-settings", json={"queue_open": False})
    assert resp.status_code == 200
    assert resp.json()["queue_open"] is False

    resp2 = client.put("/api/host-settings", json={"queue_open": True})
    assert resp2.status_code == 200
    assert resp2.json()["queue_open"] is True


def test_update_host_settings_max_songs(client):
    """PUT /api/host-settings can change max_songs_per_singer."""
    resp = client.put("/api/host-settings", json={"max_songs_per_singer": 3})
    assert resp.status_code == 200
    assert resp.json()["max_songs_per_singer"] == 3


def test_update_host_settings_queue_submission_mode(client):
    """PUT /api/host-settings can change queue_submission_mode."""
    resp = client.put("/api/host-settings", json={"queue_submission_mode": "approval"})
    assert resp.status_code == 200


def test_update_host_settings_session_duration(client):
    """PUT /api/host-settings can set session_duration_hours."""
    resp = client.put("/api/host-settings", json={"session_duration_hours": 4})
    assert resp.status_code == 200
    assert resp.json()["session_duration_hours"] == 4


def test_update_host_settings_partial_update(client):
    """PUT with only some fields leaves others unchanged."""
    # Set a known state
    client.put("/api/host-settings", json={"max_songs_per_singer": 5, "queue_open": True})
    # Update only one field
    resp = client.put("/api/host-settings", json={"queue_open": False})
    assert resp.status_code == 200
    assert resp.json()["max_songs_per_singer"] == 5
    assert resp.json()["queue_open"] is False
