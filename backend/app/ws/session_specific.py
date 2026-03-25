"""
Session-specific WebSocket endpoints for Open Karaoke Studio

Handles WebSocket connections that are scoped to specific karaoke sessions.
The unified session endpoint covers performance controls, player state, and queue management.
"""

import asyncio
import json
import logging
import secrets
from typing import Dict, Optional

from fastapi import Query, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


from app.db.database import get_db_session
from app.db.models import SessionPlaybackState

from .connection_manager import SessionConnectionManager
from .queue import get_current_queue_state

# Session-based performance state - separate state for each session
session_performance_states = {}

# Session-level locks to prevent race conditions during disconnect/cleanup
session_cleanup_locks = {}

# Pending host-disconnect termination tasks (cancelled on host reconnect)
# Grace period: 30 seconds before session is destroyed after host disconnects
HOST_DISCONNECT_GRACE_SECONDS = 30
session_termination_tasks: Dict[str, asyncio.Task] = {}


def get_session_cleanup_lock(session_id: str) -> asyncio.Lock:
    """Get or create cleanup lock for a specific session."""
    if session_id not in session_cleanup_locks:
        session_cleanup_locks[session_id] = asyncio.Lock()
    return session_cleanup_locks[session_id]


def get_session_performance_state(session_id: str):
    """Get or create performance state for a specific session."""
    if session_id not in session_performance_states:
        session_performance_states[session_id] = {
            "vocal_volume": 1.0,
            "backing_vocal_volume": 1.0,
            "instrumental_volume": 1.0,
            "lyrics_size": "medium",
            "lyrics_offset": 0,
            "current_time": 0,
            "duration": 0,
            "is_playing": False,
            "current_song_id": None,
            "is_ready": False,
            "playback_speed": 1.0,
        }
    return session_performance_states[session_id]


def hydrate_session_performance_state_from_db(session_id: str):
    """Hydrate in-memory performance state from persisted playback state."""
    with get_db_session() as db:
        playback_state = (
            db.query(SessionPlaybackState)
            .filter(SessionPlaybackState.session_id == session_id)
            .first()
        )

        if not playback_state:
            return

        session_state = get_session_performance_state(session_id)
        session_state["is_playing"] = playback_state.is_playing
        session_state["current_time"] = playback_state.current_time
        session_state["duration"] = playback_state.duration
        session_state["current_song_id"] = playback_state.current_song_id
        session_state["is_ready"] = playback_state.is_ready


def persist_session_playback_state(
    session_id: str,
    *,
    is_playing: Optional[bool] = None,
    current_time: Optional[float] = None,
    duration: Optional[float] = None,
    current_song_id: Optional[str] = None,
    is_ready: Optional[bool] = None,
) -> None:
    """Persist playback state updates for a session."""
    with get_db_session() as db:
        playback_state = (
            db.query(SessionPlaybackState)
            .filter(SessionPlaybackState.session_id == session_id)
            .first()
        )

        if not playback_state:
            playback_state = SessionPlaybackState(session_id=session_id)
            db.add(playback_state)
            db.flush()

        if is_playing is not None:
            playback_state.is_playing = is_playing
        if current_time is not None:
            playback_state.current_time = current_time
        if duration is not None:
            playback_state.duration = duration
        if current_song_id is not None:
            playback_state.current_song_id = current_song_id
        if is_ready is not None:
            playback_state.is_ready = is_ready

        db.commit()


def cleanup_session_performance_state(session_id: str):
    """Clean up performance state for a specific session when it ends."""
    if session_id in session_performance_states:
        del session_performance_states[session_id]
        logger.info(f"🧹 Cleaned up performance state for session {session_id}")

    # Also clean up the lock
    if session_id in session_cleanup_locks:
        del session_cleanup_locks[session_id]
        logger.info(f"🔓 Cleaned up lock for session {session_id}")


async def websocket_unified_session_endpoint(
    websocket: WebSocket,
    session_id: str,
    manager: SessionConnectionManager,
    device_id: Optional[str] = Query(None),
):
    """
    Unified session WebSocket endpoint.
    Handles all session-related communication: performance controls, player state, and queue management.
    Only devices in the specified session can access this endpoint.
    """
    # Verify session exists in database and check if this is the host
    with get_db_session() as db:
        from app.db.models import KaraokeSession

        db_session = (
            db.query(KaraokeSession)
            .filter(
                KaraokeSession.session_id == session_id,
                KaraokeSession.is_active == True,
            )
            .first()
        )

        if not db_session:
            await websocket.close(code=1008, reason="Session not found or inactive")
            return

        if db_session.is_expired():
            await websocket.close(code=1008, reason="Session has expired")
            return

        host_device_id = db_session.host_device_id

        # Determine if this connection is the host based on device_id query param
        is_host = device_id is not None and device_id == host_device_id

    # Generate ephemeral WebSocket connection ID
    ws_connection_id = f"device_{secrets.token_urlsafe(8)}"
    await manager.connect(websocket, ws_connection_id)

    # Add device to session (in-memory for WebSocket management)
    manager.join_session(session_id, ws_connection_id, "unified")

    # Join unified session room (covers both performance and queue)
    session_room = manager.get_session_room_name(session_id)
    await manager.join_room(websocket, session_room)

    logger.info(
        f"Session {session_id} unified client connected: {ws_connection_id} (is_host: {is_host})"
    )

    # If this is the host reconnecting within the grace period, cancel pending termination
    if is_host and session_id in session_termination_tasks:
        pending_task = session_termination_tasks.pop(session_id)
        pending_task.cancel()
        logger.info(
            f"🔄 Host reconnected to session {session_id} - cancelling pending termination"
        )

    try:
        # Hydrate in-memory state from persisted playback state before greeting client
        hydrate_session_performance_state_from_db(session_id)

        # Send current state to new connection
        session_state = get_session_performance_state(session_id)
        await websocket.send_text(
            json.dumps(
                {
                    "type": "session_connected",
                    "session_id": session_id,
                    "device_id": ws_connection_id,
                    "is_host": is_host,
                    "performance_state": session_state,
                }
            )
        )

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")

            # === PERFORMANCE & PLAYER STATE MESSAGES ===
            if message_type == "join_performance":
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "performance_state",
                            "state": get_session_performance_state(session_id),
                        }
                    )
                )

            elif message_type == "update_performance_control":
                control_name = message.get("control")
                value = message.get("value")
                session_state = get_session_performance_state(session_id)

                if control_name and control_name in session_state:
                    session_state[control_name] = value

                    # Broadcast to all devices in this session
                    await manager.broadcast_to_room(
                        session_room,
                        {
                            "type": "control_updated",
                            "control": control_name,
                            "value": value,
                        },
                        exclude=websocket,
                    )

            elif message_type == "update_player_state":
                if not is_host:
                    await websocket.send_text(
                        json.dumps({"type": "permission_denied", "action": message_type, "reason": "Host-only action"})
                    )
                    continue

                is_playing = message.get("isPlaying")
                current_time = message.get("currentTime")
                duration = message.get("duration")
                session_state = get_session_performance_state(session_id)

                if is_playing is not None:
                    session_state["is_playing"] = is_playing
                if current_time is not None:
                    session_state["current_time"] = current_time
                if duration is not None:
                    session_state["duration"] = duration

                persist_session_playback_state(
                    session_id,
                    is_playing=is_playing,
                    current_time=current_time,
                    duration=duration,
                )

                # Broadcast player state to all devices in session
                await manager.broadcast_to_room(
                    session_room,
                    {"type": "performance_state", "state": session_state},
                    exclude=websocket,
                )

            elif message_type in [
                "playback_play",
                "playback_pause",
                "reset_player_state",
                "song_loaded",
                "song_ready",
            ]:
                if not is_host:
                    await websocket.send_text(
                        json.dumps({"type": "permission_denied", "action": message_type, "reason": "Host-only action"})
                    )
                    continue

                session_state = get_session_performance_state(session_id)
                if message_type == "playback_play":
                    session_state["is_playing"] = True
                    persist_session_playback_state(session_id, is_playing=True)
                elif message_type == "playback_pause":
                    session_state["is_playing"] = False
                    persist_session_playback_state(session_id, is_playing=False)
                elif message_type == "reset_player_state":
                    session_state["current_time"] = 0
                    session_state["is_playing"] = False
                    persist_session_playback_state(
                        session_id,
                        current_time=0,
                        is_playing=False,
                    )
                elif message_type in ["song_loaded", "song_ready"]:
                    # Update song info from message
                    song_id = message.get("songId")
                    duration = message.get("duration", 0)
                    if song_id:
                        session_state["current_song_id"] = song_id
                    if duration > 0:
                        session_state["duration"] = duration
                    session_state["current_time"] = message.get("currentTime", 0)
                    session_state["is_playing"] = message.get("isPlaying", False)
                    session_state["is_ready"] = message.get(
                        "isReady", message_type == "song_ready"
                    )

                    persist_session_playback_state(
                        session_id,
                        current_song_id=song_id,
                        duration=duration,
                        current_time=session_state["current_time"],
                        is_playing=session_state["is_playing"],
                        is_ready=session_state["is_ready"],
                    )

                # Broadcast to all devices in this session
                await manager.broadcast_to_room(
                    session_room,
                    {"type": message_type, "state": session_state},
                    exclude=websocket,
                )

            # === QUEUE MANAGEMENT MESSAGES ===
            elif message_type == "join_queue_room":
                await websocket.send_text(
                    json.dumps({"type": "queue_joined", "room": session_room})
                )

            elif message_type == "request_queue_update":
                queue_state = await get_current_queue_state(session_id)
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "queue_updated",
                            "current": queue_state.get("current"),
                            "upcoming": queue_state.get("upcoming", []),
                            "items": queue_state.get("items", []),
                        }
                    )
                )

            elif message_type == "toggle_fullscreen":
                # Broadcast fullscreen toggle to all other devices in session (host will act on it)
                await manager.broadcast_to_room(
                    session_room,
                    {"type": "toggle_fullscreen"},
                    exclude=websocket,
                )

            elif message_type == "queue_changed":
                # Broadcast queue changes to all devices in session
                await manager.broadcast_to_room(
                    session_room,
                    {"type": "queue_updated", "trigger": "external_change"},
                    exclude=websocket,
                )

    except WebSocketDisconnect:
        logger.info(
            f"Session {session_id} unified client disconnected: {ws_connection_id} (is_host: {is_host})"
        )

        manager.disconnect(websocket)
        manager.leave_session(ws_connection_id, session_id)

        # If host disconnected, start a grace period before terminating the session.
        # This allows the host to survive a page refresh or brief network interruption
        # without destroying the session for all connected performers.
        if is_host:
            async def terminate_session_after_grace():
                try:
                    await asyncio.sleep(HOST_DISCONNECT_GRACE_SECONDS)

                    # Use lock to prevent race conditions during cleanup
                    cleanup_lock = get_session_cleanup_lock(session_id)
                    async with cleanup_lock:
                        logger.warning(
                            f"🛑 Host grace period expired for session {session_id} - terminating session"
                        )

                        # Broadcast session_ended to all connected devices
                        await manager.broadcast_to_room(
                            session_room,
                            {"type": "session_ended", "reason": "Host disconnected"},
                        )

                        # Give the broadcast a moment to be delivered
                        await asyncio.sleep(0.2)

                        # Delete the session from the database to recycle the session code
                        try:
                            with get_db_session() as db:
                                from app.db.models import KaraokeSession

                                session = (
                                    db.query(KaraokeSession)
                                    .filter(KaraokeSession.session_id == session_id)
                                    .first()
                                )
                                if session:
                                    db.delete(session)
                                    db.commit()
                                    logger.info(
                                        f"🗑️  Session {session_id} deleted from database (code recycled)"
                                    )
                        except Exception as e:
                            logger.error(f"❌ Failed to delete session from database: {e}")

                        # Force close all other connections in this session
                        if session_room in manager.rooms:
                            connections_to_close = list(manager.rooms[session_room])
                            for conn in connections_to_close:
                                try:
                                    await conn.close(code=1000, reason="Session ended by host")
                                    logger.debug(
                                        f"🔌 Force closed connection {id(conn)} for session {session_id}"
                                    )
                                except Exception as e:
                                    logger.error(
                                        f"❌ Failed to close connection {id(conn)}: {e}"
                                    )
                            manager.rooms[session_room] = []

                        # Clean up performance state for this session
                        cleanup_session_performance_state(session_id)

                        # Remove the termination task entry
                        session_termination_tasks.pop(session_id, None)

                except asyncio.CancelledError:
                    logger.info(
                        f"✅ Host reconnected within grace period - session {session_id} preserved"
                    )
                    session_termination_tasks.pop(session_id, None)

            logger.warning(
                f"⏳ Host disconnected from session {session_id} - "
                f"waiting {HOST_DISCONNECT_GRACE_SECONDS}s for reconnect before terminating"
            )
            task = asyncio.create_task(terminate_session_after_grace())
            session_termination_tasks[session_id] = task


