"""Integration tests for /api/sessions REST endpoints."""
import uuid


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────


def _create_session(client, device_type="stage", display_name=None):
    payload = {"device_type": device_type}
    if display_name:
        payload["display_name"] = display_name
    resp = client.post("/api/sessions", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/sessions  (create)
# ─────────────────────────────────────────────────────────────────────────────


def test_create_session_returns_201(client):
    resp = client.post("/api/sessions", json={"device_type": "stage"})
    assert resp.status_code == 201
    data = resp.json()
    assert "session_id" in data
    assert "display_code" in data
    assert data["is_host"] is True
    assert data["is_active"] is True


def test_create_session_with_display_name(client):
    resp = client.post(
        "/api/sessions",
        json={"device_type": "stage", "display_name": "Test Host"},
    )
    assert resp.status_code == 201


def test_create_session_invalid_device_type(client):
    resp = client.post("/api/sessions", json={"device_type": "invalid_type"})
    assert resp.status_code == 400


def test_create_session_device_id_returned(client):
    data = _create_session(client)
    assert "device_id" in data
    assert data["device_id"].startswith("rest_")


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/sessions/join-by-code
# ─────────────────────────────────────────────────────────────────────────────


def test_join_by_code_success(client):
    session = _create_session(client)
    code = session["display_code"]

    resp = client.post(
        "/api/sessions/join-by-code",
        json={"code": code, "device_type": "performer"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session["session_id"]
    assert data["is_host"] is False


def test_join_by_code_not_found(client):
    resp = client.post(
        "/api/sessions/join-by-code",
        json={"code": "XXXX", "device_type": "performer"},
    )
    assert resp.status_code == 404


def test_join_by_code_invalid_device_type(client):
    session = _create_session(client)
    resp = client.post(
        "/api/sessions/join-by-code",
        json={"code": session["display_code"], "device_type": "bad_type"},
    )
    assert resp.status_code == 400


def test_join_by_code_lowercased_code_works(client):
    session = _create_session(client)
    code = session["display_code"].lower()
    resp = client.post(
        "/api/sessions/join-by-code",
        json={"code": code, "device_type": "performer"},
    )
    assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/sessions/join-by-id
# ─────────────────────────────────────────────────────────────────────────────


def test_join_by_id_success(client):
    session = _create_session(client)
    resp = client.post(
        "/api/sessions/join-by-id",
        json={"session_id": session["session_id"], "device_type": "performer"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session["session_id"]


def test_join_by_id_not_found(client):
    resp = client.post(
        "/api/sessions/join-by-id",
        json={"session_id": str(uuid.uuid4()), "device_type": "performer"},
    )
    assert resp.status_code == 404


def test_join_by_id_invalid_device_type(client):
    session = _create_session(client)
    resp = client.post(
        "/api/sessions/join-by-id",
        json={"session_id": session["session_id"], "device_type": "bad_type"},
    )
    assert resp.status_code == 400


def test_join_by_id_already_joined_returns_409(client):
    """Joining twice from the same IP should return 409 conflict."""
    session = _create_session(client)
    payload = {"session_id": session["session_id"], "device_type": "performer"}
    # First join
    resp1 = client.post("/api/sessions/join-by-id", json=payload)
    assert resp1.status_code == 200
    # Second join from same IP (testclient uses 'testclient' host)
    resp2 = client.post("/api/sessions/join-by-id", json=payload)
    assert resp2.status_code == 409


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/sessions/{session_id}/info
# ─────────────────────────────────────────────────────────────────────────────


def test_get_session_info_success(client):
    session = _create_session(client)
    resp = client.get(f"/api/sessions/{session['session_id']}/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session["session_id"]


def test_get_session_info_with_device_id(client):
    session = _create_session(client)
    device_id = session["device_id"]
    resp = client.get(
        f"/api/sessions/{session['session_id']}/info?device_id={device_id}"
    )
    assert resp.status_code == 200


def test_get_session_info_not_found(client):
    resp = client.get(f"/api/sessions/{uuid.uuid4()}/info")
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/sessions/{session_id}/validate
# ─────────────────────────────────────────────────────────────────────────────


def test_validate_session_valid(client):
    session = _create_session(client)
    resp = client.get(f"/api/sessions/{session['session_id']}/validate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["session_id"] == session["session_id"]


def test_validate_session_not_found(client):
    resp = client.get(f"/api/sessions/{uuid.uuid4()}/validate")
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/sessions/{session_id}/leave
# ─────────────────────────────────────────────────────────────────────────────


def test_leave_session_not_in_session(client):
    session = _create_session(client)
    resp = client.post(f"/api/sessions/{session['session_id']}/leave")
    # TestClient IP is "testclient" — not in the session
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/sessions/my  (requires require_host dependency — mocked in integration)
# ─────────────────────────────────────────────────────────────────────────────


def test_get_my_session_returns_null_when_none(client):
    resp = client.get("/api/sessions/my")
    # No active session for mock host → returns null/empty
    assert resp.status_code == 200
    assert resp.json() is None


def test_post_my_session_creates_or_returns_session(client):
    resp = client.post(
        "/api/sessions/my", json={"device_type": "stage", "display_name": "Me"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "session_id" in data


def test_post_my_session_returns_existing_if_active(client):
    """Second call returns the existing active session, not a new one."""
    payload = {"device_type": "stage", "display_name": "Host"}
    resp1 = client.post("/api/sessions/my", json=payload)
    assert resp1.status_code == 201
    session_id_1 = resp1.json()["session_id"]

    resp2 = client.post("/api/sessions/my", json=payload)
    assert resp2.status_code == 201
    session_id_2 = resp2.json()["session_id"]

    assert session_id_1 == session_id_2
