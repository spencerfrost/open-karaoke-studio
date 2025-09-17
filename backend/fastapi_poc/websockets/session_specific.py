"""
Session-specific WebSocket endpoints for Open Karaoke Studio

Handles WebSocket connections that are scoped to specific karaoke sessions.
Includes unified session endpoints and legacy session-specific performance/queue endpoints.
"""

import json
import secrets
import sys
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect

# Add the parent directory to the Python path to import from app
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.db.database import SessionLocal
from app.db.models.queue import KaraokeQueueItem
from app.db.models.song import DbSong

from .connection_manager import SessionConnectionManager
from .performance import global_performance_state


async def websocket_unified_session_endpoint(
    websocket: WebSocket, session_id: str, manager: SessionConnectionManager
):
    """
    Unified session WebSocket endpoint.
    Handles all session-related communication: performance controls, player state, and queue management.
    Only devices in the specified session can access this endpoint.
    """
    device_id = f"device_{secrets.token_urlsafe(8)}"
    await manager.connect(websocket, device_id)

    # Verify session exists in database
    db = SessionLocal()
    try:
        from app.db.models import KaraokeSession

        session = (
            db.query(KaraokeSession)
            .filter(
                KaraokeSession.session_id == session_id,
                KaraokeSession.is_active == True,
            )
            .first()
        )

        if not session:
            await websocket.send_text(
                json.dumps({"type": "session_error", "error": "Session not found"})
            )
            await websocket.close()
            return
    finally:
        db.close()

    # Add device to session (in-memory for WebSocket management)
    manager.join_session(session_id, device_id, "unified")

    # Join unified session room (covers both performance and queue)
    session_room = manager.get_session_room_name(session_id)
    await manager.join_room(websocket, session_room)

    print(f"Session {session_id} unified client connected: {device_id}")

    try:
        # Send current state to new connection
        await websocket.send_text(
            json.dumps(
                {
                    "type": "session_connected",
                    "session_id": session_id,
                    "device_id": device_id,
                    "performance_state": global_performance_state,
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
                        {"type": "performance_state", "state": global_performance_state}
                    )
                )

            elif message_type == "update_performance_control":
                control_name = message.get("control")
                value = message.get("value")

                if control_name and control_name in global_performance_state:
                    global_performance_state[control_name] = value

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
                is_playing = message.get("isPlaying")
                current_time = message.get("currentTime")
                duration = message.get("duration")

                if is_playing is not None:
                    global_performance_state["is_playing"] = is_playing
                if current_time is not None:
                    global_performance_state["current_time"] = current_time
                if duration is not None:
                    global_performance_state["duration"] = duration

                # Broadcast player state to all devices in session
                await manager.broadcast_to_room(
                    session_room,
                    {"type": "performance_state", "state": global_performance_state},
                    exclude=websocket,
                )

            elif message_type in [
                "playback_play",
                "playback_pause",
                "reset_player_state",
                "song_loaded",
                "song_ready",
            ]:
                if message_type == "playback_play":
                    global_performance_state["is_playing"] = True
                elif message_type == "playback_pause":
                    global_performance_state["is_playing"] = False
                elif message_type == "reset_player_state":
                    global_performance_state["current_time"] = 0
                    global_performance_state["is_playing"] = False
                elif message_type in ["song_loaded", "song_ready"]:
                    # Update song info from message
                    song_id = message.get("songId")
                    duration = message.get("duration", 0)
                    if song_id:
                        global_performance_state["current_song_id"] = song_id
                    if duration > 0:
                        global_performance_state["duration"] = duration
                    global_performance_state["current_time"] = message.get(
                        "currentTime", 0
                    )
                    global_performance_state["is_playing"] = message.get(
                        "isPlaying", False
                    )
                    global_performance_state["is_ready"] = message.get(
                        "isReady", message_type == "song_ready"
                    )

                # Broadcast to all devices in this session
                await manager.broadcast_to_room(
                    session_room,
                    {"type": message_type, "state": global_performance_state},
                    exclude=websocket,
                )

            # === QUEUE MANAGEMENT MESSAGES ===
            elif message_type == "join_queue_room":
                await websocket.send_text(
                    json.dumps({"type": "queue_joined", "room": session_room})
                )

            elif message_type == "request_queue_update":
                # Get current queue from database
                db = SessionLocal()
                try:
                    queue_items = (
                        db.query(KaraokeQueueItem)
                        .order_by(KaraokeQueueItem.position)
                        .all()
                    )
                    queue_data = []
                    for item in queue_items:
                        song = (
                            db.query(DbSong).filter(DbSong.id == item.song_id).first()
                        )
                        if song:
                            queue_data.append(
                                {
                                    "id": item.id,
                                    "songId": item.song_id,
                                    "singer": item.singer_name,
                                    "position": item.position,
                                    "addedAt": (
                                        item.created_at.isoformat()
                                        if hasattr(item, "created_at")
                                        else None
                                    ),
                                    "song": {
                                        "id": song.id,
                                        "title": song.title,
                                        "artist": song.artist,
                                        "album": song.album,
                                        "duration": song.duration,
                                        "coverArt": getattr(
                                            song, "cover_art_url", None
                                        ),
                                        "syncedLyrics": song.synced_lyrics,
                                        "plainLyrics": song.plain_lyrics,
                                    },
                                }
                            )

                    await websocket.send_text(
                        json.dumps({"type": "queue_updated", "items": queue_data})
                    )
                finally:
                    db.close()

            elif message_type == "queue_changed":
                # Broadcast queue changes to all devices in session
                await manager.broadcast_to_room(
                    session_room,
                    {"type": "queue_updated", "trigger": "external_change"},
                    exclude=websocket,
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        manager.leave_session(device_id, session_id)
        print(f"Session {session_id} unified client disconnected: {device_id}")


async def websocket_session_performance_endpoint(
    websocket: WebSocket, session_id: str, manager: SessionConnectionManager
):
    """
    Session-specific performance controls WebSocket endpoint.
    Only devices in the specified session can access this endpoint.
    """
    device_id = f"device_{secrets.token_urlsafe(8)}"
    await manager.connect(websocket, device_id)

    # Verify session exists in database
    db = SessionLocal()
    try:
        from app.db.models import KaraokeSession

        session = (
            db.query(KaraokeSession)
            .filter(
                KaraokeSession.session_id == session_id,
                KaraokeSession.is_active == True,
            )
            .first()
        )

        if not session:
            await websocket.send_text(
                json.dumps({"type": "session_error", "error": "Session not found"})
            )
            await websocket.close()
            return
    finally:
        db.close()

    # Add device to session (in-memory for WebSocket management)
    manager.join_session(session_id, device_id, "performer")

    # Join session-specific performance room
    performance_room = manager.get_session_room_name(session_id, "controls")
    await manager.join_room(websocket, performance_room)

    print(f"Session {session_id} performance client connected: {device_id}")

    try:
        # Send current performance state to new connection
        await websocket.send_text(
            json.dumps({"type": "performance_state", "state": global_performance_state})
        )

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")

            if message_type == "join_performance":
                await websocket.send_text(
                    json.dumps(
                        {"type": "performance_state", "state": global_performance_state}
                    )
                )

            elif message_type == "update_performance_control":
                control_name = message.get("control")
                value = message.get("value")

                if control_name and control_name in global_performance_state:
                    global_performance_state[control_name] = value

                    # Broadcast to all devices in this session only
                    await manager.broadcast_to_room(
                        performance_room,
                        {
                            "type": "control_updated",
                            "control": control_name,
                            "value": value,
                        },
                    )

            elif message_type == "update_player_state":
                is_playing = message.get("isPlaying")
                current_time = message.get("currentTime")
                duration = message.get("duration")

                if is_playing is not None:
                    global_performance_state["is_playing"] = is_playing
                if current_time is not None:
                    global_performance_state["current_time"] = current_time
                if duration is not None:
                    global_performance_state["duration"] = duration

                await websocket.send_text(
                    json.dumps(
                        {"type": "performance_state", "state": global_performance_state}
                    )
                )

            elif message_type in [
                "playback_play",
                "playback_pause",
                "reset_player_state",
            ]:
                if message_type == "playback_play":
                    global_performance_state["is_playing"] = True
                elif message_type == "playback_pause":
                    global_performance_state["is_playing"] = False
                elif message_type == "reset_player_state":
                    global_performance_state["current_time"] = 0
                    global_performance_state["is_playing"] = False

                # Broadcast to all devices in this session
                await manager.broadcast_to_room(
                    performance_room,
                    {"type": message_type, "state": global_performance_state},
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        manager.leave_session(device_id, session_id)
        print(f"Session {session_id} performance client disconnected: {device_id}")


async def websocket_session_queue_endpoint(
    websocket: WebSocket, session_id: str, manager: SessionConnectionManager
):
    """
    Session-specific queue WebSocket endpoint.
    Only devices in the specified session can access this endpoint.
    """
    device_id = f"device_{secrets.token_urlsafe(8)}"
    await manager.connect(websocket, device_id)

    # Verify session exists in database
    db = SessionLocal()
    try:
        from app.db.models import KaraokeSession

        session = (
            db.query(KaraokeSession)
            .filter(
                KaraokeSession.session_id == session_id,
                KaraokeSession.is_active == True,
            )
            .first()
        )

        if not session:
            await websocket.send_text(
                json.dumps({"type": "session_error", "error": "Session not found"})
            )
            await websocket.close()
            return
    finally:
        db.close()

    # Add device to session (in-memory for WebSocket management)
    manager.join_session(session_id, device_id, "controller")

    # Join session-specific queue room
    queue_room = manager.get_session_room_name(session_id, "queue")
    await manager.join_room(websocket, queue_room)

    print(f"Session {session_id} queue client connected: {device_id}")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")

            if message_type == "join_queue_room":
                await websocket.send_text(
                    json.dumps({"type": "queue_joined", "room": queue_room})
                )

            elif message_type == "request_queue_update":
                # Get current queue from database
                db = SessionLocal()
                try:
                    queue_items = (
                        db.query(KaraokeQueueItem)
                        .order_by(KaraokeQueueItem.position)
                        .all()
                    )
                    queue_data = []
                    for item in queue_items:
                        song = (
                            db.query(DbSong).filter(DbSong.id == item.song_id).first()
                        )
                        if song:
                            queue_data.append(
                                {
                                    "id": item.id,
                                    "songId": item.song_id,
                                    "singer": item.singer_name,
                                    "position": item.position,
                                    "addedAt": (
                                        item.created_at.isoformat()
                                        if hasattr(item, "created_at")
                                        else None
                                    ),
                                    "song": {
                                        "id": song.id,
                                        "title": song.title,
                                        "artist": song.artist,
                                        "album": song.album,
                                        "duration": song.duration,
                                        "coverArt": getattr(
                                            song, "cover_art_url", None
                                        ),
                                        "syncedLyrics": song.synced_lyrics,
                                        "plainLyrics": song.plain_lyrics,
                                    },
                                }
                            )

                    await websocket.send_text(
                        json.dumps({"type": "queue_updated", "items": queue_data})
                    )
                finally:
                    db.close()

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        manager.leave_session(device_id, session_id)
        print(f"Session {session_id} queue client disconnected: {device_id}")
