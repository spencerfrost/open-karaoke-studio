"""Unit tests for SessionConnectionManager."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ws.connection_manager import SessionConnectionManager


@pytest.fixture
def manager():
    return SessionConnectionManager()


def _fake_ws():
    ws = MagicMock()
    ws.send_text = AsyncMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    return ws


# ---------------------------------------------------------------------------
# generate helpers
# ---------------------------------------------------------------------------


def test_generate_session_id_returns_string(manager):
    sid = manager.generate_session_id()
    assert isinstance(sid, str)
    assert len(sid) > 0


def test_generate_display_code_is_four_chars(manager):
    code = manager.generate_display_code()
    assert len(code) == 4


def test_generate_display_code_uses_valid_chars(manager):
    valid = set("23456789ABCDEFGHJKLMNPQRSTUVWXYZ")
    for _ in range(20):
        code = manager.generate_display_code()
        assert all(c in valid for c in code)


# ---------------------------------------------------------------------------
# create_session
# ---------------------------------------------------------------------------


def test_create_session_returns_session_data(manager):
    session = manager.create_session("host-1")
    assert session["host_device_id"] == "host-1"
    assert "session_id" in session
    assert "display_code" in session
    assert session["is_active"] is True
    assert "connected_devices" in session


def test_create_session_stores_in_sessions(manager):
    session = manager.create_session("host-1")
    assert session["session_id"] in manager.sessions


def test_create_session_generates_unique_display_code(manager):
    # Force collision by pre-populating a code
    manager.sessions["existing"] = {"display_code": "AAAA", "is_active": True}
    with patch.object(manager, "generate_display_code", side_effect=["AAAA", "BBBB"]):
        session = manager.create_session("host-1")
    assert session["display_code"] == "BBBB"


# ---------------------------------------------------------------------------
# find_session_by_code / find_session_by_id
# ---------------------------------------------------------------------------


def test_find_session_by_code_returns_active_session(manager):
    session = manager.create_session("host-1")
    code = session["display_code"]
    found = manager.find_session_by_code(code)
    assert found is not None
    assert found["display_code"] == code


def test_find_session_by_code_returns_none_for_unknown_code(manager):
    assert manager.find_session_by_code("ZZZZ") is None


def test_find_session_by_code_returns_none_for_inactive_session(manager):
    session = manager.create_session("host-1")
    session["is_active"] = False
    assert manager.find_session_by_code(session["display_code"]) is None


def test_find_session_by_id_returns_active_session(manager):
    session = manager.create_session("host-1")
    found = manager.find_session_by_id(session["session_id"])
    assert found is not None


def test_find_session_by_id_returns_none_for_unknown_id(manager):
    assert manager.find_session_by_id("nonexistent") is None


def test_find_session_by_id_returns_none_for_inactive_session(manager):
    session = manager.create_session("host-1")
    session["is_active"] = False
    assert manager.find_session_by_id(session["session_id"]) is None


# ---------------------------------------------------------------------------
# join_session / leave_session / get_session_for_device
# ---------------------------------------------------------------------------


def test_join_session_adds_device(manager):
    session = manager.create_session("host-1")
    result = manager.join_session(session["session_id"], "device-2", "performer")
    assert result is True
    assert "device-2" in session["connected_devices"]


def test_join_session_returns_false_for_unknown_session(manager):
    assert manager.join_session("nonexistent", "device-1", "performer") is False


def test_join_session_stores_device_session_mapping(manager):
    session = manager.create_session("host-1")
    manager.join_session(session["session_id"], "device-2", "performer")
    assert "device-2" in manager.device_sessions


def test_leave_session_marks_device_inactive(manager):
    session = manager.create_session("host-1")
    manager.join_session(session["session_id"], "device-2", "performer")
    manager.leave_session("device-2", session["session_id"])
    assert session["connected_devices"]["device-2"]["is_active"] is False


def test_leave_session_removes_from_device_sessions(manager):
    session = manager.create_session("host-1")
    manager.join_session(session["session_id"], "device-2", "performer")
    manager.leave_session("device-2", session["session_id"])
    assert "device-2" not in manager.device_sessions


def test_leave_session_host_marks_session_inactive(manager):
    session = manager.create_session("host-1")
    manager.join_session(session["session_id"], "host-1", "stage")
    manager.leave_session("host-1", session["session_id"])
    assert session["is_active"] is False


def test_leave_session_infers_session_id_from_device_sessions(manager):
    session = manager.create_session("host-1")
    manager.join_session(session["session_id"], "device-2", "performer")
    # Don't pass session_id explicitly
    manager.leave_session("device-2")
    assert "device-2" not in manager.device_sessions


def test_get_session_for_device_returns_session(manager):
    session = manager.create_session("host-1")
    manager.join_session(session["session_id"], "device-2", "performer")
    found = manager.get_session_for_device("device-2")
    assert found is not None
    assert found["session_id"] == session["session_id"]


def test_get_session_for_device_returns_none_for_unknown(manager):
    assert manager.get_session_for_device("unknown-device") is None


# ---------------------------------------------------------------------------
# get_session_room_name
# ---------------------------------------------------------------------------


def test_get_session_room_name_main(manager):
    name = manager.get_session_room_name("sess-123")
    assert name == "session_sess-123"


def test_get_session_room_name_custom_type(manager):
    name = manager.get_session_room_name("sess-123", room_type="audio")
    assert name == "session_sess-123_audio"


# ---------------------------------------------------------------------------
# connect / disconnect
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_accepts_websocket(manager):
    ws = _fake_ws()
    await manager.connect(ws, "device-1")
    ws.accept.assert_called_once()
    assert ws in manager.active_connections


@pytest.mark.asyncio
async def test_connect_stores_device_id(manager):
    ws = _fake_ws()
    await manager.connect(ws, "device-1")
    ws_key = f"ws_{id(ws)}"
    assert manager.device_sessions.get(ws_key) == "device-1"


def test_disconnect_removes_from_active_connections(manager):
    ws = _fake_ws()
    manager.active_connections.append(ws)
    manager.disconnect(ws)
    assert ws not in manager.active_connections


def test_disconnect_removes_from_rooms(manager):
    ws = _fake_ws()
    manager.rooms["test-room"] = [ws]
    manager.active_connections.append(ws)
    manager.disconnect(ws)
    assert ws not in manager.rooms["test-room"]


def test_disconnect_noop_for_unknown_websocket(manager):
    ws = _fake_ws()
    # Should not raise
    manager.disconnect(ws)


# ---------------------------------------------------------------------------
# join_room / leave_room
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_join_room_creates_room(manager):
    ws = _fake_ws()
    await manager.join_room(ws, "my-room")
    assert "my-room" in manager.rooms
    assert ws in manager.rooms["my-room"]


@pytest.mark.asyncio
async def test_join_room_does_not_duplicate(manager):
    ws = _fake_ws()
    await manager.join_room(ws, "my-room")
    await manager.join_room(ws, "my-room")
    assert manager.rooms["my-room"].count(ws) == 1


@pytest.mark.asyncio
async def test_leave_room_removes_websocket(manager):
    ws = _fake_ws()
    manager.rooms["my-room"] = [ws]
    await manager.leave_room(ws, "my-room")
    assert ws not in manager.rooms["my-room"]


@pytest.mark.asyncio
async def test_leave_room_noop_for_unknown_room(manager):
    ws = _fake_ws()
    # Should not raise
    await manager.leave_room(ws, "nonexistent-room")


# ---------------------------------------------------------------------------
# send_personal_message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_personal_message_sends_json(manager):
    ws = _fake_ws()
    await manager.send_personal_message({"type": "test", "value": 42}, ws)
    ws.send_text.assert_called_once_with(json.dumps({"type": "test", "value": 42}))


# ---------------------------------------------------------------------------
# broadcast_to_room
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcast_to_room_sends_to_all(manager):
    ws1, ws2 = _fake_ws(), _fake_ws()
    manager.rooms["room-1"] = [ws1, ws2]
    await manager.broadcast_to_room("room-1", {"type": "update"})
    ws1.send_text.assert_called_once()
    ws2.send_text.assert_called_once()


@pytest.mark.asyncio
async def test_broadcast_to_room_excludes_sender(manager):
    ws1, ws2 = _fake_ws(), _fake_ws()
    manager.rooms["room-1"] = [ws1, ws2]
    await manager.broadcast_to_room("room-1", {"type": "update"}, exclude=ws1)
    ws1.send_text.assert_not_called()
    ws2.send_text.assert_called_once()


@pytest.mark.asyncio
async def test_broadcast_to_nonexistent_room_does_not_raise(manager):
    await manager.broadcast_to_room("nonexistent", {"type": "update"})


@pytest.mark.asyncio
async def test_broadcast_cleans_up_failed_connections(manager):
    ws_good = _fake_ws()
    ws_bad = _fake_ws()
    ws_bad.send_text.side_effect = Exception("disconnected")
    manager.rooms["room-1"] = [ws_good, ws_bad]
    manager.active_connections.extend([ws_good, ws_bad])
    await manager.broadcast_to_room("room-1", {"type": "update"})
    assert ws_bad not in manager.active_connections


# ---------------------------------------------------------------------------
# force_close_session_connections
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_force_close_marks_session_inactive(manager):
    session = manager.create_session("host-1")
    sid = session["session_id"]
    room_name = manager.get_session_room_name(sid)
    manager.rooms[room_name] = []
    await manager.force_close_session_connections(sid, "Test close")
    assert manager.sessions[sid]["is_active"] is False


@pytest.mark.asyncio
async def test_force_close_sends_session_ended_broadcast(manager):
    session = manager.create_session("host-1")
    sid = session["session_id"]
    room_name = manager.get_session_room_name(sid)
    ws = _fake_ws()
    manager.rooms[room_name] = [ws]
    await manager.force_close_session_connections(sid, "Host left")
    ws.send_text.assert_called()
    sent = json.loads(ws.send_text.call_args[0][0])
    assert sent["type"] == "session_ended"


@pytest.mark.asyncio
async def test_force_close_nonexistent_session_does_not_raise(manager):
    await manager.force_close_session_connections("nonexistent", "reason")
