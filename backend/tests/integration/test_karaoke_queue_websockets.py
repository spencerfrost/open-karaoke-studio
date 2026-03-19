# backend/tests/integration/test_karaoke_queue_websockets.py

import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db.models as models
import app.api.karaoke_queue as _queue_api
import app.api.sessions as _sessions_api
from app.api.dependencies import get_current_user, get_db
from app.db.models import Base
from tests.conftest import create_test_app

from unittest.mock import MagicMock


def _make_mock_user():
    u = MagicMock()
    u.id = 1
    u.username = "testuser"
    u.is_admin = True
    u.is_host = True
    return u


@pytest.fixture(scope="function")
def test_setup():
    """Set up test database tables and factories using SQLite."""
    import tempfile, os

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_url = f"sqlite:///{db_path}"

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
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
    app.dependency_overrides[_queue_api.get_db] = _get_db
    app.dependency_overrides[_sessions_api.get_db] = _get_db
    app.dependency_overrides[get_current_user] = _make_mock_user

    setup_session = TestingSession()
    # Patch SessionLocal globally so WebSocket handlers (which bypass DI) use SQLite
    import app.db.database as _db_module
    original_SessionLocal = _db_module.SessionLocal
    _db_module.SessionLocal = TestingSession

    def session_factory(session_id: str, host_device_id: str):
        session = models.KaraokeSession(
            session_id=session_id,
            display_code=str(uuid.uuid4())[:4].upper(),
            host_device_id=host_device_id,
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        setup_session.add(session)
        setup_session.commit()
        setup_session.refresh(session)
        return session

    def song_factory():
        song = models.DbSong(
            id=f"song_{uuid.uuid4()}",
            title="Test Song",
            artist="Test Artist",
            duration=180,
        )
        setup_session.add(song)
        setup_session.commit()
        setup_session.refresh(song)
        return song

    try:
        with TestClient(app) as client:
            yield client, session_factory, song_factory
    finally:
        setup_session.close()
        _db_module.SessionLocal = original_SessionLocal
        engine.dispose()
        try:
            os.unlink(db_path)
        except Exception:
            pass


def test_websocket_queue_update_is_session_specific(test_setup):
    """
    Verify that queue data is isolated per session.
    Each session's WebSocket only returns that session's queue items.
    """
    client, session_factory, song_factory = test_setup

    session_id_1 = f"session_{uuid.uuid4()}"
    session_id_2 = f"session_{uuid.uuid4()}"
    host_device_id_1 = f"host_{uuid.uuid4()}"
    host_device_id_2 = f"host_{uuid.uuid4()}"

    session_factory(session_id_1, host_device_id_1)
    session_factory(session_id_2, host_device_id_2)

    song = song_factory()

    # Add a song to session 1's queue via REST API
    response = client.post(
        f"/api/karaoke-queue?session_code={session_id_1}",
        json={"singer": "Test Singer", "songId": song.id},
    )
    assert response.status_code == 201

    # Add a song to session 2's queue via REST API
    response = client.post(
        f"/api/karaoke-queue?session_code={session_id_2}",
        json={"singer": "Another Singer", "songId": song.id},
    )
    assert response.status_code == 201

    # Connect WebSockets and request queue updates - verify isolation
    with client.websocket_connect(
        f"/ws/session/{session_id_1}"
    ) as websocket1, client.websocket_connect(
        f"/ws/session/{session_id_2}"
    ) as websocket2:

        # Get initial connection messages
        message1 = websocket1.receive_json()
        assert message1["type"] == "session_connected"

        message2 = websocket2.receive_json()
        assert message2["type"] == "session_connected"

        # Request queue update for session 1
        websocket1.send_json({"type": "request_queue_update"})
        message1_queue = websocket1.receive_json()
        assert message1_queue["type"] == "queue_updated"
        assert message1_queue["current"] is None
        assert len(message1_queue["upcoming"]) == 1
        assert len(message1_queue["items"]) == 1
        assert message1_queue["items"][0]["songId"] == song.id
        assert message1_queue["items"][0]["singer"] == "Test Singer"

        # Request queue update for session 2
        websocket2.send_json({"type": "request_queue_update"})
        message2_queue = websocket2.receive_json()
        assert message2_queue["type"] == "queue_updated"
        assert message2_queue["current"] is None
        assert len(message2_queue["upcoming"]) == 1
        assert len(message2_queue["items"]) == 1
        assert message2_queue["items"][0]["songId"] == song.id
        assert message2_queue["items"][0]["singer"] == "Another Singer"


def test_queue_rest_state_exposes_current_and_upcoming(test_setup):
    """Verify REST queue endpoint returns explicit current/upcoming state."""
    client, session_factory, song_factory = test_setup

    session_id = f"session_{uuid.uuid4()}"
    host_device_id = f"host_{uuid.uuid4()}"
    session_factory(session_id, host_device_id)

    song = song_factory()

    add_response = client.post(
        f"/api/karaoke-queue?session_code={session_id}",
        json={"singer": "Test Singer", "songId": song.id},
    )
    assert add_response.status_code == 201
    queue_item_id = add_response.json()["id"]

    queue_response = client.get(f"/api/karaoke-queue?session_code={session_id}")
    assert queue_response.status_code == 200
    queue_payload = queue_response.json()

    assert queue_payload["current"] is None
    assert len(queue_payload["upcoming"]) == 1
    assert len(queue_payload["items"]) == 1
    assert queue_payload["upcoming"][0]["songId"] == song.id

    play_response = client.post(
        f"/api/karaoke-queue/{queue_item_id}/play?session_code={session_id}",
    )
    assert play_response.status_code == 200

    queue_response = client.get(f"/api/karaoke-queue?session_code={session_id}")
    assert queue_response.status_code == 200
    queue_payload = queue_response.json()

    assert queue_payload["current"] is not None
    assert queue_payload["current"]["songId"] == song.id
    assert queue_payload["current"]["position"] == 0
    assert queue_payload["upcoming"] == []
    assert len(queue_payload["items"]) == 1

    # Add another song after current is loaded; it should appear in upcoming only
    next_song = song_factory()
    second_add_response = client.post(
        f"/api/karaoke-queue?session_code={session_id}",
        json={"singer": "Next Singer", "songId": next_song.id},
    )
    assert second_add_response.status_code == 201

    queue_response = client.get(f"/api/karaoke-queue?session_code={session_id}")
    assert queue_response.status_code == 200
    queue_payload = queue_response.json()

    assert queue_payload["current"] is not None
    assert queue_payload["current"]["songId"] == song.id
    assert len(queue_payload["upcoming"]) == 1
    assert queue_payload["upcoming"][0]["songId"] == next_song.id
    assert queue_payload["upcoming"][0]["position"] == 1
    assert all(
        item["id"] != queue_payload["current"]["id"]
        for item in queue_payload["upcoming"]
    )


def test_playback_state_persists_across_websocket_reconnect(test_setup):
    """Verify persisted playback state is restored when reconnecting to unified session websocket."""
    client, session_factory, song_factory = test_setup

    session_id = f"session_{uuid.uuid4()}"
    host_device_id = f"host_{uuid.uuid4()}"
    session_factory(session_id, host_device_id)

    song = song_factory()

    add_response = client.post(
        f"/api/karaoke-queue?session_code={session_id}",
        json={"singer": "Test Singer", "songId": song.id},
    )
    assert add_response.status_code == 201
    queue_item_id = add_response.json()["id"]

    load_response = client.post(
        f"/api/karaoke-queue/{queue_item_id}/play?session_code={session_id}"
    )
    assert load_response.status_code == 200

    # Connect as host so player state commands are accepted
    ws_url = f"/ws/session/{session_id}?device_id={host_device_id}"
    with client.websocket_connect(ws_url) as websocket:
        connected_message = websocket.receive_json()
        assert connected_message["type"] == "session_connected"
        assert connected_message["performance_state"]["current_song_id"] == song.id

        websocket.send_json(
            {
                "type": "update_player_state",
                "isPlaying": False,
                "currentTime": 42.5,
                "duration": 180,
            }
        )
        websocket.send_json({"type": "playback_play"})
        # Synchronize: request_queue_update returns a response, ensuring
        # the preceding messages have been processed before we disconnect.
        websocket.send_json({"type": "request_queue_update"})
        _ = websocket.receive_json()  # queue_updated response

    with client.websocket_connect(ws_url) as websocket:
        connected_message = websocket.receive_json()
        assert connected_message["type"] == "session_connected"

        state = connected_message["performance_state"]
        assert state["current_song_id"] == song.id
        assert state["is_playing"] is True
        assert state["current_time"] == 42.5
        assert state["duration"] == 180
