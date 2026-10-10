# backend/tests/integration/test_ws_host_authority.py
"""
Regression tests for WebSocket host authority.

Guards the bug where `device_id` was declared on the inner handler but never forwarded by
the registered route, so `is_session_owner` was False for every connection ever made (774/774 in
production logs). Host authority now derives from the authenticated user via the
`authenticate` message, so these tests assert that contract directly.

They also guard membership: the opening `authenticate` must carry the device id of an active
member of the session, and a wrong code is indistinguishable from a wrong device.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from tests.conftest import create_test_app

import app.db.models as models
from app.db.database import SessionLocal
from app.services.auth_service import create_access_token


@pytest.fixture(scope="function")
def ws_setup():
    """App with factories that seed the shared test database."""
    app = create_test_app()
    setup_session = SessionLocal()

    def user_factory(username: str) -> models.User:
        user = models.User(username=username, is_host=True, is_admin=False)
        user.set_password("irrelevant-for-these-tests")
        setup_session.add(user)
        setup_session.commit()
        setup_session.refresh(user)
        return user

    def session_factory(
        host_user_id, session_id: Optional[str] = None
    ) -> models.KaraokeSession:
        session_id = session_id or str(uuid.uuid4())[:4].upper()
        session = models.KaraokeSession(
            session_id=session_id,
            display_code=session_id,
            host_device_id=f"rest_{uuid.uuid4().hex[:12]}",
            host_user_id=host_user_id,
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        setup_session.add(session)
        setup_session.commit()
        setup_session.refresh(session)
        return session

    def device_factory(session_id: str, is_active: bool = True) -> str:
        device = models.SessionDevice(
            session_id=session_id,
            device_id=f"rest_{uuid.uuid4().hex[:12]}",
            device_type="performer",
            is_active=is_active,
        )
        setup_session.add(device)
        setup_session.commit()
        return device.device_id

    try:
        with TestClient(app) as client:
            yield client, user_factory, session_factory, device_factory
    finally:
        setup_session.close()


def _greeting(websocket):
    """Read messages until the session_connected greeting; return (greeting, seen before)."""
    seen = []
    for _ in range(5):
        message = websocket.receive_json()
        if message.get("type") == "session_connected":
            return message, seen
        seen.append(message)
    raise AssertionError("never received session_connected")


def _assert_rejected(client, session_id, device_id):
    """The server answers not_a_member and closes with 1008."""
    with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
        websocket.send_json({"type": "authenticate", "device_id": device_id})
        assert websocket.receive_json() == {
            "type": "auth_failed",
            "reason": "not_a_member",
        }
        with pytest.raises(WebSocketDisconnect) as closed:
            websocket.receive_json()
    assert closed.value.code == 1008


def _collect_until(websocket, sentinel_type, max_messages=8):
    """
    Read until `sentinel_type` arrives and return every message seen.

    Host-only actions are silent on success, so tests follow them with a message that
    always replies. Reading blocks forever otherwise.
    """
    seen = []
    for _ in range(max_messages):
        message = websocket.receive_json()
        seen.append(message)
        if message.get("type") == sentinel_type:
            return seen
    raise AssertionError(
        f"never received {sentinel_type}; saw {[m.get('type') for m in seen]}"
    )


def test_member_device_connects_unprivileged(ws_setup):
    """A member device without a token gets in, with no host authority."""
    client, user_factory, session_factory, device_factory = ws_setup
    host = user_factory("host")
    session = session_factory(host_user_id=host.id)
    device_id = device_factory(session.session_id)

    with client.websocket_connect(f"/ws/session/{session.session_id}") as websocket:
        websocket.send_json({"type": "authenticate", "device_id": device_id})
        greeting, _ = _greeting(websocket)

    assert greeting["is_session_owner"] is False


def test_unknown_device_is_rejected(ws_setup):
    client, user_factory, session_factory, _device_factory = ws_setup
    session = session_factory(host_user_id=user_factory("host").id)

    _assert_rejected(client, session.session_id, "rest_notarealone")


def test_unknown_code_looks_the_same_as_unknown_device(ws_setup):
    """A wrong code gets the exact same answer, so the socket can't confirm live codes."""
    client, *_ = ws_setup

    _assert_rejected(client, "ZZZZ", "rest_notarealone")


def test_device_from_another_session_is_rejected(ws_setup):
    client, user_factory, session_factory, device_factory = ws_setup
    host = user_factory("host")
    session = session_factory(host_user_id=host.id)
    other = session_factory(host_user_id=host.id)

    _assert_rejected(client, session.session_id, device_factory(other.session_id))


def test_device_that_left_is_rejected(ws_setup):
    client, user_factory, session_factory, device_factory = ws_setup
    session = session_factory(host_user_id=user_factory("host").id)

    _assert_rejected(
        client,
        session.session_id,
        device_factory(session.session_id, is_active=False),
    )


def test_missing_device_id_is_rejected(ws_setup):
    """A token alone is not membership - the host's devices carry device ids too."""
    client, user_factory, session_factory, _device_factory = ws_setup
    host = user_factory("host")
    session = session_factory(host_user_id=host.id)

    with client.websocket_connect(f"/ws/session/{session.session_id}") as websocket:
        websocket.send_json(
            {"type": "authenticate", "token": create_access_token(host)}
        )
        assert websocket.receive_json()["reason"] == "not_a_member"


def test_first_message_must_be_authenticate(ws_setup):
    """Anything sent before authenticating gets the connection dropped, not answered."""
    client, user_factory, session_factory, _device_factory = ws_setup
    session = session_factory(host_user_id=user_factory("host").id)

    with client.websocket_connect(f"/ws/session/{session.session_id}") as websocket:
        websocket.send_json({"type": "request_queue_update"})
        assert websocket.receive_json()["reason"] == "not_a_member"


def test_host_token_grants_host_authority(ws_setup):
    """The session owner's JWT elevates the connection. This is the 774/774 regression."""
    client, user_factory, session_factory, device_factory = ws_setup
    host = user_factory("host")
    session = session_factory(host_user_id=host.id)

    with client.websocket_connect(f"/ws/session/{session.session_id}") as websocket:
        websocket.send_json(
            {
                "type": "authenticate",
                "device_id": device_factory(session.session_id),
                "token": create_access_token(host),
            }
        )
        greeting, before = _greeting(websocket)

    assert greeting["is_session_owner"] is True
    assert before == []


def test_non_owner_token_does_not_grant_host_authority(ws_setup):
    """A valid token for someone who does not own the session confers nothing."""
    client, user_factory, session_factory, device_factory = ws_setup
    host = user_factory("host")
    stranger = user_factory("stranger")
    session = session_factory(host_user_id=host.id)

    with client.websocket_connect(f"/ws/session/{session.session_id}") as websocket:
        websocket.send_json(
            {
                "type": "authenticate",
                "device_id": device_factory(session.session_id),
                "token": create_access_token(stranger),
            }
        )
        greeting, before = _greeting(websocket)

    assert greeting["is_session_owner"] is False
    assert before == []


def test_garbage_token_is_reported_but_membership_stands(ws_setup):
    """A bad token is reported, and the member device still gets in as a non-owner."""
    client, user_factory, session_factory, device_factory = ws_setup
    session = session_factory(host_user_id=user_factory("host").id)

    with client.websocket_connect(f"/ws/session/{session.session_id}") as websocket:
        websocket.send_json(
            {
                "type": "authenticate",
                "device_id": device_factory(session.session_id),
                "token": "not-a-jwt",
            }
        )
        greeting, before = _greeting(websocket)

    assert before == [{"type": "auth_failed", "reason": "invalid_token"}]
    assert greeting["is_session_owner"] is False


def test_session_without_owner_has_no_host(ws_setup):
    """A session with a null host_user_id cannot grant host authority to anyone."""
    client, user_factory, session_factory, device_factory = ws_setup
    host = user_factory("host")
    session = session_factory(host_user_id=None)

    with client.websocket_connect(f"/ws/session/{session.session_id}") as websocket:
        websocket.send_json(
            {
                "type": "authenticate",
                "device_id": device_factory(session.session_id),
                "token": create_access_token(host),
            }
        )
        greeting, before = _greeting(websocket)

    assert before == [{"type": "auth_failed", "reason": "session_has_no_host"}]
    assert greeting["is_session_owner"] is False


def test_host_only_action_rejected_for_non_owner(ws_setup):
    """Playback control is refused for a member that hasn't proven it owns the session."""
    client, user_factory, session_factory, device_factory = ws_setup
    session = session_factory(host_user_id=user_factory("host").id)

    with client.websocket_connect(f"/ws/session/{session.session_id}") as websocket:
        websocket.send_json(
            {"type": "authenticate", "device_id": device_factory(session.session_id)}
        )
        _greeting(websocket)
        websocket.send_json({"type": "playback_play"})
        # join_performance always replies, giving the read loop a terminating sentinel
        websocket.send_json({"type": "join_performance"})
        seen = _collect_until(websocket, "performance_state")

    denied = [m for m in seen if m.get("type") == "permission_denied"]
    assert denied, "expected permission_denied for a non-owner"
    assert denied[0]["action"] == "playback_play"


def test_host_only_action_allowed_for_owner(ws_setup):
    """With the owner's token, the same action is accepted rather than denied."""
    client, user_factory, session_factory, device_factory = ws_setup
    host = user_factory("host")
    session = session_factory(host_user_id=host.id)

    with client.websocket_connect(f"/ws/session/{session.session_id}") as websocket:
        websocket.send_json(
            {
                "type": "authenticate",
                "device_id": device_factory(session.session_id),
                "token": create_access_token(host),
            }
        )
        assert _greeting(websocket)[0]["is_session_owner"] is True

        websocket.send_json({"type": "playback_play"})
        websocket.send_json({"type": "join_performance"})
        seen = _collect_until(websocket, "performance_state")

    assert not any(
        m.get("type") == "permission_denied" for m in seen
    ), "authenticated host must not be refused playback control"
