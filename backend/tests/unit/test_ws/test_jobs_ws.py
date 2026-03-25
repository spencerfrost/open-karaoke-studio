"""Unit tests for WebSocket jobs endpoint."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocketDisconnect

from app.ws.jobs import (
    broadcast_all_jobs,
    broadcast_job_cancelled,
    broadcast_job_completed,
    broadcast_job_created,
    broadcast_job_failed,
    broadcast_job_update,
    get_current_jobs_list,
    websocket_jobs_endpoint,
)


def _make_ws():
    ws = MagicMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    return ws


def _make_manager():
    m = MagicMock()
    m.connect = AsyncMock()
    m.disconnect = MagicMock()
    m.join_room = AsyncMock()
    m.leave_room = AsyncMock()
    m.broadcast_to_room = AsyncMock()
    return m


# ---------------------------------------------------------------------------
# get_current_jobs_list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_jobs_list_returns_list():
    mock_job = MagicMock()
    mock_job.to_dict.return_value = {"id": "job-1", "status": "completed"}
    with patch("app.ws.jobs.JobsService") as MockService:
        MockService.return_value.get_all_jobs.return_value = [mock_job]
        result = await get_current_jobs_list()
    assert isinstance(result, list)
    assert result[0]["id"] == "job-1"


@pytest.mark.asyncio
async def test_get_current_jobs_list_falls_back_on_error():
    with patch("app.ws.jobs.JobsService") as MockService:
        MockService.return_value.get_all_jobs.side_effect = Exception("DB down")
        result = await get_current_jobs_list()
    # Falls back to mock data
    assert isinstance(result, list)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# websocket_jobs_endpoint
# ---------------------------------------------------------------------------


def _msg(*msgs):
    return [json.dumps(m) for m in msgs] + [WebSocketDisconnect()]


@pytest.mark.asyncio
async def test_endpoint_sends_connected_on_join():
    ws = _make_ws()
    manager = _make_manager()
    ws.receive_text.side_effect = _msg()
    await websocket_jobs_endpoint(ws, manager)
    ws.send_text.assert_called_once()
    sent = json.loads(ws.send_text.call_args[0][0])
    assert sent["type"] == "connected"


@pytest.mark.asyncio
async def test_endpoint_disconnects_on_exit():
    ws = _make_ws()
    manager = _make_manager()
    ws.receive_text.side_effect = _msg()
    await websocket_jobs_endpoint(ws, manager)
    manager.disconnect.assert_called_once_with(ws)


@pytest.mark.asyncio
async def test_endpoint_subscribe_to_jobs():
    ws = _make_ws()
    manager = _make_manager()
    ws.receive_text.side_effect = _msg({"type": "subscribe_to_jobs"})

    with patch("app.ws.jobs.get_current_jobs_list", return_value=[]):
        await websocket_jobs_endpoint(ws, manager)

    # 3 sends: connected + subscribed + jobs_list
    assert ws.send_text.call_count == 3
    messages = [json.loads(c[0][0]) for c in ws.send_text.call_args_list]
    types = [m["type"] for m in messages]
    assert "subscribed" in types
    assert "jobs_list" in types


@pytest.mark.asyncio
async def test_endpoint_unsubscribe_from_jobs():
    ws = _make_ws()
    manager = _make_manager()
    ws.receive_text.side_effect = _msg({"type": "unsubscribe_from_jobs"})
    await websocket_jobs_endpoint(ws, manager)
    manager.leave_room.assert_called_once()
    messages = [json.loads(c[0][0]) for c in ws.send_text.call_args_list]
    assert any(m["type"] == "unsubscribed" for m in messages)


@pytest.mark.asyncio
async def test_endpoint_request_jobs_list():
    ws = _make_ws()
    manager = _make_manager()
    ws.receive_text.side_effect = _msg({"type": "request_jobs_list"})
    with patch("app.ws.jobs.get_current_jobs_list", return_value=[{"id": "j1"}]):
        await websocket_jobs_endpoint(ws, manager)
    messages = [json.loads(c[0][0]) for c in ws.send_text.call_args_list]
    assert any(m["type"] == "jobs_list" for m in messages)


@pytest.mark.asyncio
async def test_endpoint_unknown_message_type_sends_error():
    ws = _make_ws()
    manager = _make_manager()
    ws.receive_text.side_effect = _msg({"type": "totally_unknown"})
    await websocket_jobs_endpoint(ws, manager)
    messages = [json.loads(c[0][0]) for c in ws.send_text.call_args_list]
    assert any(m["type"] == "error" for m in messages)


# ---------------------------------------------------------------------------
# broadcast helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcast_job_update():
    manager = _make_manager()
    await broadcast_job_update(manager, {"id": "j1"})
    manager.broadcast_to_room.assert_called_once()
    msg = manager.broadcast_to_room.call_args[0][1]
    assert msg["type"] == "job_updated"


@pytest.mark.asyncio
async def test_broadcast_job_created():
    manager = _make_manager()
    await broadcast_job_created(manager, {"id": "j1"})
    msg = manager.broadcast_to_room.call_args[0][1]
    assert msg["type"] == "job_created"


@pytest.mark.asyncio
async def test_broadcast_job_completed():
    manager = _make_manager()
    await broadcast_job_completed(manager, {"id": "j1"})
    msg = manager.broadcast_to_room.call_args[0][1]
    assert msg["type"] == "job_completed"


@pytest.mark.asyncio
async def test_broadcast_job_failed():
    manager = _make_manager()
    await broadcast_job_failed(manager, {"id": "j1"})
    msg = manager.broadcast_to_room.call_args[0][1]
    assert msg["type"] == "job_failed"


@pytest.mark.asyncio
async def test_broadcast_job_cancelled():
    manager = _make_manager()
    await broadcast_job_cancelled(manager, {"id": "j1"})
    msg = manager.broadcast_to_room.call_args[0][1]
    assert msg["type"] == "job_cancelled"


@pytest.mark.asyncio
async def test_broadcast_all_jobs():
    manager = _make_manager()
    await broadcast_all_jobs(manager, [{"id": "j1"}, {"id": "j2"}])
    msg = manager.broadcast_to_room.call_args[0][1]
    assert msg["type"] == "jobs_list"
    assert len(msg["jobs"]) == 2
