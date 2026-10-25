"""
Session-specific WebSocket endpoints for Open Karaoke Studio

Handles WebSocket connections that are scoped to specific karaoke sessions.
The unified session endpoint covers performance controls, player state, and queue management.
"""

import asyncio
import json
import logging
import secrets
from typing import Dict, NamedTuple, Optional, Tuple

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


from app.db.database import get_db_session
from app.db.models import KaraokeSession, SessionPlaybackState, User
from app.services.auth_service import verify_token
from app.services.session_service import deactivate_session, find_session_member

from .connection_manager import SessionConnectionManager
from .presence import (
    broadcast_presence_update,
    build_performer_presence,
    find_linked_performer_id,
)
from .queue import get_current_queue_state

# Session-based performance state - separate state for each session
session_performance_states = {}

# Keys any connection may set via `update_performance_control` (performer phones send
# these from /controls). Playback keys (is_playing, current_time, ...) live in the same
# dict but only the session owner may change them, through the player messages.
PERFORMANCE_CONTROLS = frozenset(
    {
        "vocal_volume",
        "backing_vocal_volume",
        "instrumental_volume",
        "lyrics_size",
        "lyrics_offset",
    }
)

# Session-level locks to prevent race conditions during disconnect/cleanup
session_cleanup_locks = {}

# Pending host-disconnect termination tasks (cancelled on host reconnect)
# Grace period: 30 seconds before session is destroyed after host disconnects
HOST_DISCONNECT_GRACE_SECONDS = 30

# How long a new connection has to send its `authenticate` message before it is dropped
AUTH_TIMEOUT_SECONDS = 10
session_termination_tasks: Dict[str, asyncio.Task] = {}


def get_session_cleanup_lock(session_id: str) -> asyncio.Lock:
    """Get or create cleanup lock for a specific session."""
    if session_id not in session_cleanup_locks:
        session_cleanup_locks[session_id] = asyncio.Lock()
    return session_cleanup_locks[session_id]


def resolve_host_claim(token: str, session_id: str) -> Tuple[bool, Optional[str]]:
    """
    Resolve a JWT against the owner of a session.

    Host authority comes from the authenticated user (KaraokeSession.host_user_id), never
    from a device token - device ids are handed out by unauthenticated endpoints and cannot
    be trusted as credentials.

    Returns (is_session_owner, error). `error` is None when the token itself is valid;
    `is_session_owner` is False for a valid token belonging to someone who does not own
    this session.
    """
    payload = verify_token(token)
    if payload is None:
        return False, "invalid_token"

    user_id = payload.get("sub")
    if user_id is None:
        return False, "invalid_token_payload"

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return False, "invalid_token_payload"

    with get_db_session() as db:
        # A signed token is not enough - the account must still exist, so a deleted
        # user's unexpired token cannot retain host authority.
        if db.query(User).filter(User.id == user_id).first() is None:
            return False, "user_not_found"

        session = (
            db.query(KaraokeSession)
            .filter(KaraokeSession.session_id == session_id)
            .first()
        )
        if session is None:
            return False, "session_not_found"
        if session.host_user_id is None:
            return False, "session_has_no_host"

        return user_id == session.host_user_id, None


def get_session_performance_state(session_id: str):
    """Get or create performance state for a specific session."""
    if session_id not in session_performance_states:
        session_performance_states[session_id] = {
            "vocal_volume": 0.0,  # Songs start with the lead vocal off
            "backing_vocal_volume": 1.0,
            "instrumental_volume": 1.0,
            "lyrics_size": "medium",
            "lyrics_offset": 0,
            "current_time": 0,
            "duration": 0,
            "is_playing": False,
            "current_song_id": None,
            "is_ready": False,
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
        logger.debug("🧹 Cleaned up performance state for session %s", session_id)

    # Also clean up the lock
    if session_id in session_cleanup_locks:
        del session_cleanup_locks[session_id]
        logger.debug("🔓 Cleaned up lock for session %s", session_id)


class AuthenticatedConnection(NamedTuple):
    """Who a socket proved itself to be in its opening `authenticate` message."""

    # The session member id minted at join - the same one REST sends as X-Device-ID.
    device_id: str
    is_session_owner: bool


async def _authenticate_connection(
    websocket: WebSocket, session_id: str
) -> Optional[AuthenticatedConnection]:
    """
    Read the connection's opening `authenticate` message and check it.

    The message must carry the `device_id` minted by join-by-code or session creation (the
    same credential REST calls send as X-Device-ID). It may also carry the host's JWT.

    Returns None when the connection is not a member of this live session - a wrong code
    and a wrong device get the same answer, so the socket can't be used to find live codes.
    Otherwise returns the member's device id and whether the connection is the session
    owner. A bad token on a valid device is reported but not fatal: the connection
    continues as a non-owner.
    """
    try:
        raw = await asyncio.wait_for(
            websocket.receive_text(), timeout=AUTH_TIMEOUT_SECONDS
        )
        message = json.loads(raw)
    except (asyncio.TimeoutError, json.JSONDecodeError):
        return None

    if not isinstance(message, dict) or message.get("type") != "authenticate":
        return None

    device_id = message.get("device_id")
    if not isinstance(device_id, str) or not device_id:
        return None

    with get_db_session() as db:
        if find_session_member(db, session_id, device_id) is None:
            return None

    token = message.get("token")
    if not token:
        return AuthenticatedConnection(device_id, False)

    is_session_owner, error = resolve_host_claim(token, session_id)
    if error:
        logger.warning("Session %s host claim failed: %s", session_id, error)
        await websocket.send_text(json.dumps({"type": "auth_failed", "reason": error}))
        return AuthenticatedConnection(device_id, False)
    return AuthenticatedConnection(device_id, is_session_owner)


async def websocket_unified_session_endpoint(
    websocket: WebSocket,
    session_id: str,
    manager: SessionConnectionManager,
):
    """
    Unified session WebSocket endpoint.
    Handles all session-related communication: performance controls, player state, and queue management.

    Only session members get in. The first message must be `authenticate` with the
    device's `device_id` (and, for the host, a JWT) - see _authenticate_connection. Until
    it passes, the socket is not in the room and receives nothing.
    """
    await websocket.accept()

    try:
        connection = await _authenticate_connection(websocket, session_id)
    except WebSocketDisconnect:
        return

    if connection is None:
        await websocket.send_text(
            json.dumps({"type": "auth_failed", "reason": "not_a_member"})
        )
        await websocket.close(code=1008, reason="Not a member of this session")
        return

    is_session_owner = connection.is_session_owner
    member_device_id = connection.device_id

    # Generate ephemeral WebSocket connection ID
    ws_connection_id = f"device_{secrets.token_urlsafe(8)}"
    manager.register(websocket, ws_connection_id)

    # Add device to session (in-memory for WebSocket management)
    manager.join_session(session_id, ws_connection_id, "unified")

    # Join unified session room (covers both performance and queue)
    session_room = manager.get_session_room_name(session_id)
    await manager.join_room(websocket, session_room)

    logger.info(
        "Session %s unified client connected: %s (is_session_owner: %s)",
        session_id,
        ws_connection_id,
        is_session_owner,
    )

    # Host reconnecting within the grace period - cancel pending termination
    if is_session_owner and session_id in session_termination_tasks:
        session_termination_tasks.pop(session_id).cancel()
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
                    "is_session_owner": is_session_owner,
                    "performance_state": session_state,
                    # Same shape as `presence_updated.performers`, so a stage that
                    # connects mid-song knows whose phone is open without waiting
                    # for someone's phone to change.
                    "presence": build_performer_presence(manager, session_id),
                }
            )
        )

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")

            # === PRESENCE ===
            # Sent by every device on open, on each visibility change and on each
            # route change. Recorded against the device this socket authenticated
            # as - a socket can only ever speak for itself.
            if message_type == "presence":
                visible = message.get("visible")
                on_controls = message.get("on_controls", False)
                if not isinstance(visible, bool) or not isinstance(on_controls, bool):
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "permission_denied",
                                "action": message_type,
                                "reason": "Malformed presence report",
                            }
                        )
                    )
                    continue

                changed = manager.set_presence(
                    session_id, member_device_id, ws_connection_id, visible, on_controls
                )

                # Personal reply: which roster seat this device is. The phone
                # compares it with the queue's current item to know its song has
                # started. Looked up per report, so a seat linked after connect
                # is picked up on the next one.
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "presence_acknowledged",
                            "performer_id": find_linked_performer_id(
                                session_id, member_device_id
                            ),
                        }
                    )
                )

                if changed:
                    await broadcast_presence_update(manager, session_id)
                continue

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

                if control_name not in PERFORMANCE_CONTROLS:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "permission_denied",
                                "action": message_type,
                                "reason": f"Not a performance control: {control_name}",
                            }
                        )
                    )
                    continue

                session_state = get_session_performance_state(session_id)
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
                if not is_session_owner:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "permission_denied",
                                "action": message_type,
                                "reason": "Host-only action",
                            }
                        )
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
                if not is_session_owner:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "permission_denied",
                                "action": message_type,
                                "reason": "Host-only action",
                            }
                        )
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

    except WebSocketDisconnect:
        logger.info(
            f"Session {session_id} unified client disconnected: {ws_connection_id} (is_session_owner: {is_session_owner})"
        )

        manager.disconnect(websocket)
        manager.leave_session(ws_connection_id, session_id)

        # If host disconnected, start a grace period before terminating the session.
        # This allows the host to survive a page refresh or brief network interruption
        # without destroying the session for all connected performers.
        if is_session_owner:

            async def terminate_session_after_grace():
                try:
                    await asyncio.sleep(HOST_DISCONNECT_GRACE_SECONDS)

                    # Use lock to prevent race conditions during cleanup
                    cleanup_lock = get_session_cleanup_lock(session_id)
                    async with cleanup_lock:
                        logger.warning(
                            f"🛑 Host grace period expired for session {session_id} - terminating session"
                        )

                        # Deactivate rather than delete: the queue, playback state and
                        # roster have to survive a host whose phone simply locked.
                        try:
                            with get_db_session() as db:
                                deactivate_session(db, session_id)
                        except Exception as e:
                            logger.error(
                                "❌ Failed to deactivate session %s: %s", session_id, e
                            )

                        # Broadcasts session_ended, closes every socket in the room and
                        # clears this session's performance state.
                        await manager.force_close_session_connections(
                            session_id, reason="Host disconnected"
                        )

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

    finally:
        # However the socket ended - a clean close or an error out of the loop -
        # it is no longer anyone's open page. A stale "on screen" would hide the
        # stage's prompt for exactly the phone that needs it.
        if manager.drop_presence(session_id, ws_connection_id):
            await broadcast_presence_update(manager, session_id)
