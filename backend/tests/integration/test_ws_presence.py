# backend/tests/integration/test_ws_presence.py
"""
Presence over `/ws/session/{session_id}`: each device reports whether its page is
on screen, and the stage learns - per roster seat, never per device id - whose
phone is open.
"""

import os
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.conftest import create_test_app

import app.api.karaoke_queue as _queue_api
import app.api.sessions as _sessions_api
import app.db.models as models
from app.api.dependencies import get_db
from app.db.models import Base


@pytest.fixture(scope="function")
def presence_setup():
    """SQLite-backed app with a session, a stage device and one linked phone."""
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
    app.dependency_overrides[_queue_api.get_db] = _get_db

    # WebSocket handlers bypass DI and use SessionLocal directly
    import app.db.database as _db_module

    original_SessionLocal = _db_module.SessionLocal
    _db_module.SessionLocal = TestingSession

    db = TestingSession()
    session_id = str(uuid.uuid4())[:4].upper()
    stage_device = f"rest_{uuid.uuid4().hex[:12]}"
    phone_device = f"rest_{uuid.uuid4().hex[:12]}"
    db.add(
        models.KaraokeSession(
            session_id=session_id,
            display_code=session_id,
            host_device_id=stage_device,
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
    )
    db.flush()
    db.add(
        models.SessionDevice(
            session_id=session_id, device_id=stage_device, device_type="stage"
        )
    )
    db.add(
        models.SessionDevice(
            session_id=session_id, device_id=phone_device, device_type="performer"
        )
    )
    sarah = models.SessionPerformer(
        session_id=session_id,
        name="Sarah",
        normalized_name="sarah",
        seat=0,
        device_id=phone_device,
    )
    # A walk-up the host typed in: no phone, so never part of presence.
    walk_up = models.SessionPerformer(
        session_id=session_id, name="Dave", normalized_name="dave", seat=1
    )
    db.add_all([sarah, walk_up])
    db.commit()

    ctx = {
        "session_id": session_id,
        "stage_device": stage_device,
        "phone_device": phone_device,
        "sarah_id": sarah.id,
    }

    try:
        with TestClient(app) as client:
            yield client, ctx
    finally:
        db.close()
        _db_module.SessionLocal = original_SessionLocal
        engine.dispose()
        try:
            os.unlink(db_path)
        except Exception:
            pass


def _until(websocket, message_type, max_messages=8):
    """Read until `message_type` arrives and return it."""
    seen = []
    for _ in range(max_messages):
        message = websocket.receive_json()
        if message.get("type") == message_type:
            return message
        seen.append(message.get("type"))
    raise AssertionError(f"never received {message_type}; saw {seen}")


@contextmanager
def _member(client, ctx, device_key):
    """Open a socket as one of the session's devices; yields (socket, greeting)."""
    with client.websocket_connect(f"/ws/session/{ctx['session_id']}") as websocket:
        websocket.send_json({"type": "authenticate", "device_id": ctx[device_key]})
        greeting = _until(websocket, "session_connected")
        yield websocket, greeting


def _report(websocket, visible, on_controls=False):
    websocket.send_json(
        {"type": "presence", "visible": visible, "on_controls": on_controls}
    )


def test_greeting_carries_presence_for_linked_seats_only(presence_setup):
    client, ctx = presence_setup
    with _member(client, ctx, "stage_device") as (_, greeting):
        assert greeting["presence"] == [
            {
                "performerId": ctx["sarah_id"],
                "connected": False,
                "visible": False,
                "onControls": False,
            }
        ]


def test_phone_report_is_acknowledged_with_its_seat(presence_setup):
    client, ctx = presence_setup
    with _member(client, ctx, "phone_device") as (phone, _):
        _report(phone, visible=True)
        ack = _until(phone, "presence_acknowledged")
        assert ack["performer_id"] == ctx["sarah_id"]


def test_stage_without_a_seat_is_acknowledged_with_none(presence_setup):
    client, ctx = presence_setup
    with _member(client, ctx, "stage_device") as (stage, _):
        _report(stage, visible=True)
        assert _until(stage, "presence_acknowledged")["performer_id"] is None


def test_stage_hears_phone_open_hide_and_leave(presence_setup):
    client, ctx = presence_setup
    with _member(client, ctx, "stage_device") as (stage, _):
        with _member(client, ctx, "phone_device") as (phone, _):
            _report(phone, visible=True, on_controls=True)
            update = _until(stage, "presence_updated")
            assert update["performers"] == [
                {
                    "performerId": ctx["sarah_id"],
                    "connected": True,
                    "visible": True,
                    "onControls": True,
                }
            ]

            _report(phone, visible=False, on_controls=True)
            update = _until(stage, "presence_updated")
            assert update["performers"][0]["connected"] is True
            assert update["performers"][0]["visible"] is False
            assert update["performers"][0]["onControls"] is False

        # The phone's socket closed.
        update = _until(stage, "presence_updated")
        assert update["performers"][0]["connected"] is False


def test_unchanged_report_is_not_rebroadcast(presence_setup):
    """A repeat report gets its ack but no room-wide update."""
    client, ctx = presence_setup
    with _member(client, ctx, "phone_device") as (phone, _):
        _report(phone, visible=True)
        _until(phone, "presence_updated")
        _report(phone, visible=True)
        _until(phone, "presence_acknowledged")
        # The next thing the phone hears is the reply to this, not an update.
        phone.send_json({"type": "join_queue_room"})
        assert phone.receive_json()["type"] == "queue_joined"


def test_broadcast_never_carries_device_ids(presence_setup):
    client, ctx = presence_setup
    with _member(client, ctx, "stage_device") as (stage, _):
        with _member(client, ctx, "phone_device") as (phone, _):
            _report(phone, visible=True)
            update = _until(stage, "presence_updated")
            assert ctx["phone_device"] not in str(update)
            assert ctx["stage_device"] not in str(update)


def test_malformed_report_is_rejected(presence_setup):
    client, ctx = presence_setup
    with _member(client, ctx, "phone_device") as (phone, _):
        phone.send_json({"type": "presence"})
        denied = _until(phone, "permission_denied")
        assert denied["action"] == "presence"


def test_current_item_carries_its_performer(presence_setup):
    """The phone matches `current.performerId` against its own seat."""
    client, ctx = presence_setup

    import app.db.database as _db_module

    db = _db_module.SessionLocal()
    try:
        song = models.DbSong(
            id=f"song_{uuid.uuid4()}", title="Song", artist="Artist", duration=180
        )
        db.add(song)
        db.flush()
        item = models.KaraokeQueueItem(
            session_id=ctx["session_id"],
            song_id=song.id,
            singer_name="Sarah",
            position=1,
            performer_id=ctx["sarah_id"],
        )
        db.add(item)
        db.flush()
        db.add(
            models.SessionPlaybackState(
                session_id=ctx["session_id"], current_queue_item_id=item.id
            )
        )
        db.commit()
    finally:
        db.close()

    # Over the WebSocket: request_queue_update replies to the asker alone.
    with _member(client, ctx, "phone_device") as (phone, _):
        phone.send_json({"type": "request_queue_update"})
        state = _until(phone, "queue_updated")
        assert state["current"]["performerId"] == ctx["sarah_id"]

    # And over REST, so the two serialisers stay in step.
    response = client.get(
        f"/api/karaoke-queue?session_code={ctx['session_id']}",
        headers={
            "X-Session-ID": ctx["session_id"],
            "X-Device-ID": ctx["phone_device"],
        },
    )
    assert response.status_code == 200
    assert response.json()["current"]["performerId"] == ctx["sarah_id"]
