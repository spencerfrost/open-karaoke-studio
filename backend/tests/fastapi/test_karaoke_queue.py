"""
Tests for the queue's roster wiring (unit 3a): add_to_queue resolves or
creates a performer for the given singer name, and addedAt is a real
timestamp now that karaoke_queue.created_at exists.
"""

from datetime import datetime, timedelta

import pytest
from app.db.models import DbSong, KaraokeQueueItem, KaraokeSession, SessionPerformer
from tests.fastapi.conftest import _TestingSessionLocal

HOST_USER_ID = 1


@pytest.fixture
def db():
    session = _TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_session_with_song(db, session_id="AAAA", song_id="test-song-123"):
    session = KaraokeSession(
        session_id=session_id,
        display_code=session_id,
        host_device_id=f"rest_{session_id.lower()}",
        host_user_id=HOST_USER_ID,
        expires_at=datetime.utcnow() + timedelta(hours=8),
        is_active=True,
    )
    db.add(session)
    db.add(
        DbSong(
            id=song_id,
            title="Test Song",
            artist="Test Artist",
            duration=180,
            source="upload",
        )
    )
    db.commit()
    return session


def test_add_to_queue_creates_a_performer_for_a_new_singer(client, db):
    _make_session_with_song(db)

    response = client.post(
        "/api/karaoke-queue?session_code=AAAA",
        json={"singer": "Spencer", "songId": "test-song-123"},
    )

    assert response.status_code == 201
    item = db.query(KaraokeQueueItem).one()
    performer = db.query(SessionPerformer).one()
    assert item.performer_id == performer.id
    assert performer.normalized_name == "spencer"


def test_add_to_queue_reuses_an_existing_performer(client, db):
    _make_session_with_song(db)
    client.post(
        "/api/karaoke-queue?session_code=AAAA",
        json={"singer": "Spencer", "songId": "test-song-123"},
    )

    response = client.post(
        "/api/karaoke-queue?session_code=AAAA",
        json={"singer": "  spencer  ", "songId": "test-song-123"},
    )

    assert response.status_code == 201
    assert db.query(SessionPerformer).count() == 1
    items = db.query(KaraokeQueueItem).all()
    assert items[0].performer_id == items[1].performer_id


def test_add_to_queue_returns_a_real_added_at_timestamp(client, db):
    _make_session_with_song(db)

    response = client.post(
        "/api/karaoke-queue?session_code=AAAA",
        json={"singer": "Spencer", "songId": "test-song-123"},
    )

    added_at = response.json()["addedAt"]
    assert added_at is not None
    # Regression: addedAt was null in every payload before karaoke_queue.created_at existed.
    datetime.fromisoformat(added_at)


def test_get_queue_reflects_the_same_added_at_as_the_add_response(client, db):
    _make_session_with_song(db)
    add_response = client.post(
        "/api/karaoke-queue?session_code=AAAA",
        json={"singer": "Spencer", "songId": "test-song-123"},
    )

    get_response = client.get("/api/karaoke-queue?session_code=AAAA")

    assert get_response.json()["items"][0]["addedAt"] == add_response.json()["addedAt"]
