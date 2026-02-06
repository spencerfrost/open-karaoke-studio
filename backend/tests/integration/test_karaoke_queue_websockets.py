# backend/tests/integration/test_karaoke_queue_websockets.py

import pytest
from fastapi.testclient import TestClient
import uuid
from datetime import datetime, timedelta


@pytest.fixture(scope="function")
def test_setup():
    """Set up test database tables and factories."""
    # Import database and models - they will use DATABASE_URL from conftest
    from app.db.database import engine, SessionLocal
    from app.db.models import Base
    import app.db.models as models
    from app.main import app
    
    # Ensure all models are registered
    _ = (models.KaraokeSession, models.DbSong, models.KaraokeQueueItem,
         models.SessionDevice, models.User, models.DbJob)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create a session for setup/teardown
    setup_session = SessionLocal()
    
    # Session factory
    def session_factory(session_id: str, host_device_id: str):
        session = models.KaraokeSession(
            session_id=session_id,
            display_code=str(uuid.uuid4())[:4].upper(),
            host_device_id=host_device_id,
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        setup_session.add(session)
        setup_session.commit()
        setup_session.refresh(session)
        return session
    
    # Song factory
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
        # Close session
        setup_session.close()
        
        # Drop all tables for next test
        Base.metadata.drop_all(engine)


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
    with client.websocket_connect(f"/ws/session/{session_id_1}") as websocket1, \
         client.websocket_connect(f"/ws/session/{session_id_2}") as websocket2:

        # Get initial connection messages
        message1 = websocket1.receive_json()
        assert message1["type"] == "session_connected"

        message2 = websocket2.receive_json()
        assert message2["type"] == "session_connected"

        # Request queue update for session 1
        websocket1.send_json({"type": "request_queue_update"})
        message1_queue = websocket1.receive_json()
        assert message1_queue["type"] == "queue_updated"
        assert len(message1_queue["items"]) == 1
        assert message1_queue["items"][0]["songId"] == song.id
        assert message1_queue["items"][0]["singer"] == "Test Singer"

        # Request queue update for session 2
        websocket2.send_json({"type": "request_queue_update"})
        message2_queue = websocket2.receive_json()
        assert message2_queue["type"] == "queue_updated"
        assert len(message2_queue["items"]) == 1
        assert message2_queue["items"][0]["songId"] == song.id
        assert message2_queue["items"][0]["singer"] == "Another Singer"
