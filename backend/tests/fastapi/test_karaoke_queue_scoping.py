"""
Tests for the queue's access scoping: a session guest is confined to their
own session (require_queue_access), and only the owning host - or an admin -
may mutate a session's queue (require_session_owner).
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from app.api.dependencies import (
    RequesterContext,
    get_current_user,
    require_host_or_session_member,
)
from app.db.models import DbSong, KaraokeQueueItem, KaraokeSession
from tests.fastapi.conftest import _get_mock_requester, _TestingSessionLocal

HOST_A_USER_ID = 1
HOST_B_USER_ID = 2


@pytest.fixture
def db():
    session = _TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_session_with_song(db, session_id, host_user_id, song_id):
    session = KaraokeSession(
        session_id=session_id,
        display_code=session_id,
        host_device_id=f"rest_{session_id.lower()}",
        host_user_id=host_user_id,
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


def _as_guest_of(fastapi_app, session_id):
    """Override the request identity to an anonymous member of `session_id`."""
    fastapi_app.dependency_overrides[require_host_or_session_member] = (
        lambda: RequesterContext(session_id=session_id)
    )


def _as_user(fastapi_app, user_id, is_host=True, is_admin=False):
    """Override the request identity to a specific account."""

    def _mock_user():
        mock = MagicMock()
        mock.id = user_id
        mock.is_host = is_host
        mock.is_admin = is_admin
        mock.is_demo = False
        mock.display_name = f"user-{user_id}"
        return mock

    fastapi_app.dependency_overrides[get_current_user] = _mock_user


def _reset_overrides(fastapi_app):
    fastapi_app.dependency_overrides[require_host_or_session_member] = (
        _get_mock_requester
    )
    fastapi_app.dependency_overrides[get_current_user] = (
        lambda: _get_mock_requester().user
    )


def test_guest_cannot_read_another_sessions_queue(client, fastapi_app, db):
    _make_session_with_song(db, "AAAA", HOST_A_USER_ID, "song-a")
    _make_session_with_song(db, "BBBB", HOST_A_USER_ID, "song-b")

    _as_guest_of(fastapi_app, "AAAA")
    try:
        own = client.get("/api/karaoke-queue?session_code=AAAA")
        other = client.get("/api/karaoke-queue?session_code=BBBB")
    finally:
        _reset_overrides(fastapi_app)

    assert own.status_code == 200
    assert other.status_code == 403


def test_guest_cannot_add_to_another_sessions_queue(client, fastapi_app, db):
    _make_session_with_song(db, "AAAA", HOST_A_USER_ID, "song-a")
    _make_session_with_song(db, "BBBB", HOST_A_USER_ID, "song-b")

    _as_guest_of(fastapi_app, "AAAA")
    try:
        response = client.post(
            "/api/karaoke-queue?session_code=BBBB",
            json={"singer": "Intruder", "songId": "song-b"},
        )
    finally:
        _reset_overrides(fastapi_app)

    assert response.status_code == 403


def test_host_cannot_mutate_another_hosts_queue(client, fastapi_app, db):
    _make_session_with_song(db, "AAAA", HOST_A_USER_ID, "song-a")

    add_response = client.post(
        "/api/karaoke-queue?session_code=AAAA",
        json={"singer": "Spencer", "songId": "song-a"},
    )
    item_id = add_response.json()["id"]

    _as_user(fastapi_app, HOST_B_USER_ID, is_host=True, is_admin=False)
    try:
        response = client.delete(f"/api/karaoke-queue/{item_id}?session_code=AAAA")
    finally:
        _reset_overrides(fastapi_app)

    assert response.status_code == 403
    assert db.query(KaraokeQueueItem).filter_by(id=item_id).one_or_none() is not None


def test_owning_host_can_mutate_their_own_queue(client, fastapi_app, db):
    _make_session_with_song(db, "AAAA", HOST_A_USER_ID, "song-a")

    add_response = client.post(
        "/api/karaoke-queue?session_code=AAAA",
        json={"singer": "Spencer", "songId": "song-a"},
    )
    item_id = add_response.json()["id"]

    _as_user(fastapi_app, HOST_A_USER_ID, is_host=True, is_admin=False)
    try:
        response = client.delete(f"/api/karaoke-queue/{item_id}?session_code=AAAA")
    finally:
        _reset_overrides(fastapi_app)

    assert response.status_code == 200
    assert db.query(KaraokeQueueItem).filter_by(id=item_id).one_or_none() is None


def test_admin_can_mutate_any_hosts_queue(client, fastapi_app, db):
    _make_session_with_song(db, "AAAA", HOST_A_USER_ID, "song-a")

    add_response = client.post(
        "/api/karaoke-queue?session_code=AAAA",
        json={"singer": "Spencer", "songId": "song-a"},
    )
    item_id = add_response.json()["id"]

    _as_user(fastapi_app, HOST_B_USER_ID, is_host=False, is_admin=True)
    try:
        response = client.delete(f"/api/karaoke-queue/{item_id}?session_code=AAAA")
    finally:
        _reset_overrides(fastapi_app)

    assert response.status_code == 200
