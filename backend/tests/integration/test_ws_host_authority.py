# backend/tests/integration/test_ws_host_authority.py
"""
Regression tests for WebSocket host authority.

Guards the bug where `device_id` was declared on the inner handler but never forwarded by
the registered route, so `is_host` was False for every connection ever made (774/774 in
production logs). Host authority now derives from the authenticated user via the
`authenticate` message, so these tests assert that contract directly.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

import app.api.sessions as _sessions_api
import app.db.models as models
import pytest
from app.api.dependencies import get_db
from app.db.models import Base
from app.services.auth_service import create_access_token
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.conftest import create_test_app


@pytest.fixture(scope="function")
def ws_setup():
    """SQLite-backed app with factories for users and sessions."""
    import os
    import tempfile

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def _get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_test_app()
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[_sessions_api.get_db] = _get_db

    setup_session = TestingSession()

    # WebSocket handlers bypass DI and use SessionLocal directly
    import app.db.database as _db_module

    original_SessionLocal = _db_module.SessionLocal
    _db_module.SessionLocal = TestingSession

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

    try:
        with TestClient(app) as client:
            yield client, user_factory, session_factory
    finally:
        setup_session.close()
        _db_module.SessionLocal = original_SessionLocal
        engine.dispose()
        try:
            os.unlink(db_path)
        except Exception:
            pass


def _greeting(websocket):
    """Read messages until the session_connected greeting arrives."""
    for _ in range(5):
        message = websocket.receive_json()
        if message.get("type") == "session_connected":
            return message
    raise AssertionError("never received session_connected")


def _authenticate(websocket, token):
    """Send an authenticate message and return the server's reply."""
    websocket.send_json({"type": "authenticate", "token": token})
    for _ in range(5):
        message = websocket.receive_json()
        if message.get("type") in ("authenticated", "auth_failed"):
            return message
    raise AssertionError("never received an authentication reply")


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


def test_connection_starts_unprivileged(ws_setup):
    """A fresh connection holds no host authority until it authenticates."""
    client, user_factory, session_factory = ws_setup
    host = user_factory("host")
    session = session_factory(host_user_id=host.id)

    with client.websocket_connect(f"/ws/session/{session.session_id}") as websocket:
        assert _greeting(websocket)["is_host"] is False


def test_host_token_grants_host_authority(ws_setup):
    """The session owner's JWT elevates the connection. This is the 774/774 regression."""
    client, user_factory, session_factory = ws_setup
    host = user_factory("host")
    session = session_factory(host_user_id=host.id)

    with client.websocket_connect(f"/ws/session/{session.session_id}") as websocket:
        _greeting(websocket)
        reply = _authenticate(websocket, create_access_token(host))

    assert reply["type"] == "authenticated"
    assert reply["is_host"] is True


def test_non_owner_token_does_not_grant_host_authority(ws_setup):
    """A valid token for someone who does not own the session confers nothing."""
    client, user_factory, session_factory = ws_setup
    host = user_factory("host")
    stranger = user_factory("stranger")
    session = session_factory(host_user_id=host.id)

    with client.websocket_connect(f"/ws/session/{session.session_id}") as websocket:
        _greeting(websocket)
        reply = _authenticate(websocket, create_access_token(stranger))

    assert reply["type"] == "authenticated"
    assert reply["is_host"] is False


def test_garbage_token_is_rejected(ws_setup):
    """An unparseable token fails auth rather than silently passing."""
    client, user_factory, session_factory = ws_setup
    host = user_factory("host")
    session = session_factory(host_user_id=host.id)

    with client.websocket_connect(f"/ws/session/{session.session_id}") as websocket:
        _greeting(websocket)
        reply = _authenticate(websocket, "not-a-jwt")

    assert reply["type"] == "auth_failed"
    assert reply["reason"] == "invalid_token"


def test_session_without_owner_has_no_host(ws_setup):
    """A session with a null host_user_id cannot grant host authority to anyone."""
    client, user_factory, session_factory = ws_setup
    host = user_factory("host")
    session = session_factory(host_user_id=None)

    with client.websocket_connect(f"/ws/session/{session.session_id}") as websocket:
        _greeting(websocket)
        reply = _authenticate(websocket, create_access_token(host))

    assert reply["type"] == "auth_failed"
    assert reply["reason"] == "session_has_no_host"


def test_host_only_action_rejected_before_authentication(ws_setup):
    """Playback control is refused until the connection proves it owns the session."""
    client, user_factory, session_factory = ws_setup
    host = user_factory("host")
    session = session_factory(host_user_id=host.id)

    with client.websocket_connect(f"/ws/session/{session.session_id}") as websocket:
        _greeting(websocket)
        websocket.send_json({"type": "playback_play"})
        # join_performance always replies, giving the read loop a terminating sentinel
        websocket.send_json({"type": "join_performance"})
        seen = _collect_until(websocket, "performance_state")

    denied = [m for m in seen if m.get("type") == "permission_denied"]
    assert denied, "expected permission_denied for an unauthenticated client"
    assert denied[0]["action"] == "playback_play"


def test_host_only_action_allowed_after_authentication(ws_setup):
    """After authenticating, the same action is accepted rather than denied."""
    client, user_factory, session_factory = ws_setup
    host = user_factory("host")
    session = session_factory(host_user_id=host.id)

    with client.websocket_connect(f"/ws/session/{session.session_id}") as websocket:
        _greeting(websocket)
        assert _authenticate(websocket, create_access_token(host))["is_host"] is True

        websocket.send_json({"type": "playback_play"})
        websocket.send_json({"type": "join_performance"})
        seen = _collect_until(websocket, "performance_state")

    assert not any(
        m.get("type") == "permission_denied" for m in seen
    ), "authenticated host must not be refused playback control"
