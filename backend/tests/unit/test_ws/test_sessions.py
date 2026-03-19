"""Unit tests for WebSocket session management endpoint."""
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocketDisconnect

from app.ws.sessions import websocket_session_endpoint


FAKE_SESSION = {
    "session_id": "sess-abc",
    "display_code": "XYZW",
    "host_device_id": "host-device",
    "is_active": True,
    "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    "expires_at": datetime(2026, 12, 31, tzinfo=timezone.utc),
    "connected_devices": {},
}


@pytest.fixture
def manager():
    m = MagicMock()
    m.connect = AsyncMock()
    m.disconnect = MagicMock()
    m.send_personal_message = AsyncMock()
    m.broadcast_to_room = AsyncMock()
    m.join_room = AsyncMock()
    m.leave_room = AsyncMock()
    m.join_session = MagicMock()
    m.leave_session = MagicMock()
    m.get_session_room_name = MagicMock(return_value="room:sess-abc")
    m.create_session = MagicMock(return_value=FAKE_SESSION)
    m.find_session_by_code = MagicMock(return_value=None)
    m.find_session_by_id = MagicMock(return_value=None)
    m.get_session_for_device = MagicMock(return_value=None)
    m.force_close_session_connections = AsyncMock()
    return m


@pytest.fixture
def websocket():
    ws = MagicMock()
    ws.receive_text = AsyncMock()
    return ws


def _messages(*msgs):
    """Build a side_effect list ending in WebSocketDisconnect."""
    return [json.dumps(m) for m in msgs] + [WebSocketDisconnect()]


@pytest.mark.asyncio
async def test_connect_called_on_entry(websocket, manager):
    websocket.receive_text.side_effect = _messages()
    await websocket_session_endpoint(websocket, manager)
    # connect is called once with the websocket and an auto-generated device_id string
    manager.connect.assert_called_once()
    assert manager.connect.call_args[0][0] is websocket
    assert isinstance(manager.connect.call_args[0][1], str)


@pytest.mark.asyncio
async def test_disconnect_called_on_exit(websocket, manager):
    websocket.receive_text.side_effect = _messages()
    await websocket_session_endpoint(websocket, manager)
    manager.disconnect.assert_called_once_with(websocket)


@pytest.mark.asyncio
async def test_create_session_sends_session_created(websocket, manager):
    websocket.receive_text.side_effect = _messages({"type": "create_session"})
    await websocket_session_endpoint(websocket, manager)

    manager.send_personal_message.assert_called_once()
    sent = manager.send_personal_message.call_args[0][0]
    assert sent["type"] == "session_created"
    assert sent["session_id"] == "sess-abc"
    assert sent["display_code"] == "XYZW"
    assert sent["is_host"] is True


@pytest.mark.asyncio
async def test_create_session_joins_room(websocket, manager):
    websocket.receive_text.side_effect = _messages({"type": "create_session"})
    await websocket_session_endpoint(websocket, manager)
    manager.join_room.assert_called_once()


@pytest.mark.asyncio
async def test_join_by_code_invalid_code_sends_error(websocket, manager):
    websocket.receive_text.side_effect = _messages(
        {"type": "join_session_by_code", "display_code": "X"}  # too short
    )
    await websocket_session_endpoint(websocket, manager)
    sent = manager.send_personal_message.call_args[0][0]
    assert sent["type"] == "session_error"
    assert "Invalid display code" in sent["error"]


@pytest.mark.asyncio
async def test_join_by_code_not_found_sends_error(websocket, manager):
    manager.find_session_by_code.return_value = None
    websocket.receive_text.side_effect = _messages(
        {"type": "join_session_by_code", "display_code": "ABCD"}
    )
    await websocket_session_endpoint(websocket, manager)
    sent = manager.send_personal_message.call_args[0][0]
    assert sent["type"] == "session_error"
    assert "Session not found" in sent["error"]


@pytest.mark.asyncio
async def test_join_by_code_success(websocket, manager):
    fake_session = {
        **FAKE_SESSION,
        "connected_devices": {
            "device-1": {"is_active": True},
        },
    }
    manager.find_session_by_code.return_value = fake_session
    websocket.receive_text.side_effect = _messages(
        {"type": "join_session_by_code", "display_code": "XYZW"}
    )
    await websocket_session_endpoint(websocket, manager)

    sent = manager.send_personal_message.call_args[0][0]
    assert sent["type"] == "session_joined"
    assert sent["session_id"] == "sess-abc"
    manager.join_room.assert_called_once()
    manager.broadcast_to_room.assert_called_once()


@pytest.mark.asyncio
async def test_join_by_id_not_found_sends_error(websocket, manager):
    manager.find_session_by_id.return_value = None
    websocket.receive_text.side_effect = _messages(
        {"type": "join_session_by_id", "session_id": "nonexistent"}
    )
    await websocket_session_endpoint(websocket, manager)
    sent = manager.send_personal_message.call_args[0][0]
    assert sent["type"] == "session_error"


@pytest.mark.asyncio
async def test_join_by_id_success(websocket, manager):
    fake_session = {**FAKE_SESSION, "connected_devices": {}}
    manager.find_session_by_id.return_value = fake_session
    websocket.receive_text.side_effect = _messages(
        {"type": "join_session_by_id", "session_id": "sess-abc"}
    )
    await websocket_session_endpoint(websocket, manager)
    sent = manager.send_personal_message.call_args[0][0]
    assert sent["type"] == "session_joined"


@pytest.mark.asyncio
async def test_leave_session_when_not_in_session(websocket, manager):
    manager.get_session_for_device.return_value = None
    websocket.receive_text.side_effect = _messages({"type": "leave_session"})
    # Should not raise
    await websocket_session_endpoint(websocket, manager)
    manager.leave_session.assert_not_called()


@pytest.mark.asyncio
async def test_leave_session_as_non_host(websocket, manager):
    fake_session = {
        **FAKE_SESSION,
        "host_device_id": "some-other-host",
        "connected_devices": {"other-dev": {"is_active": True}},
    }
    manager.get_session_for_device.return_value = fake_session
    websocket.receive_text.side_effect = _messages({"type": "leave_session"})
    await websocket_session_endpoint(websocket, manager)

    # leave_session is called from message handler AND disconnect handler (both fire)
    assert manager.leave_session.called
    sent = manager.send_personal_message.call_args[0][0]
    assert sent["type"] == "session_left"


@pytest.mark.asyncio
async def test_leave_session_as_host_force_closes(websocket, manager):
    # Make the device_id match host_device_id by patching secrets
    with patch("app.ws.sessions.secrets.token_urlsafe", return_value="hosttoken"):
        fake_session = {
            **FAKE_SESSION,
            "host_device_id": "device_hosttoken",
            "connected_devices": {},
        }
        manager.get_session_for_device.return_value = fake_session
        websocket.receive_text.side_effect = _messages({"type": "leave_session"})
        await websocket_session_endpoint(websocket, manager)

    # force_close is called from message handler AND disconnect handler
    assert manager.force_close_session_connections.called


@pytest.mark.asyncio
async def test_get_session_info_when_not_in_session(websocket, manager):
    manager.get_session_for_device.return_value = None
    websocket.receive_text.side_effect = _messages({"type": "get_session_info"})
    await websocket_session_endpoint(websocket, manager)
    sent = manager.send_personal_message.call_args[0][0]
    assert sent["type"] == "session_info"
    assert sent["in_session"] is False


@pytest.mark.asyncio
async def test_get_session_info_when_in_session(websocket, manager):
    from datetime import datetime, timezone
    fake_session = {
        **FAKE_SESSION,
        "connected_devices": {
            "dev-1": {
                "device_id": "dev-1",
                "device_type": "performer",
                "joined_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "is_active": True,
            }
        },
    }
    manager.get_session_for_device.return_value = fake_session
    websocket.receive_text.side_effect = _messages({"type": "get_session_info"})
    await websocket_session_endpoint(websocket, manager)
    sent = manager.send_personal_message.call_args[0][0]
    assert sent["type"] == "session_info"
    assert sent["in_session"] is True
    assert sent["device_count"] == 1


@pytest.mark.asyncio
async def test_disconnect_as_non_host_broadcasts_device_disconnected(websocket, manager):
    fake_session = {
        **FAKE_SESSION,
        "host_device_id": "someone-else",
        "connected_devices": {},
    }
    manager.get_session_for_device.return_value = fake_session
    # Disconnect immediately (no messages processed)
    websocket.receive_text.side_effect = WebSocketDisconnect()
    await websocket_session_endpoint(websocket, manager)

    manager.leave_session.assert_called_once()
    manager.broadcast_to_room.assert_called_once()
    broadcast_msg = manager.broadcast_to_room.call_args[0][1]
    assert broadcast_msg["type"] == "device_disconnected"
