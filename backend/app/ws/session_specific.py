"""
Session-specific WebSocket endpoints for Open Karaoke Studio

Handles WebSocket connections that are scoped to specific karaoke sessions.
Includes unified session endpoints and legacy session-specific performance/queue endpoints.
"""

import json
import secrets

from fastapi import WebSocket, WebSocketDisconnect


from app.db.database import SessionLocal
from app.db.models.queue import KaraokeQueueItem
from app.db.models.song import DbSong

from .connection_manager import SessionConnectionManager

# Session-based performance state - separate state for each session
session_performance_states = {}

def get_session_performance_state(session_id: str):
    """Get or create performance state for a specific session."""
    if session_id not in session_performance_states:
        session_performance_states[session_id] = {
            "vocal_volume": 1.0,
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


def cleanup_session_performance_state(session_id: str):
    """Clean up performance state for a specific session when it ends."""
    if session_id in session_performance_states:
        del session_performance_states[session_id]
        print(f"🧹 Cleaned up performance state for session {session_id}")


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

    # Verify session exists in database and check if this is the host
    db = SessionLocal()
    is_host = False
    host_device_id = None
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
        
        host_device_id = session.host_device_id
    finally:
        db.close()

    # Add device to session (in-memory for WebSocket management)
    manager.join_session(session_id, device_id, "unified")

    # Join unified session room (covers both performance and queue)
    session_room = manager.get_session_room_name(session_id)
    await manager.join_room(websocket, session_room)
    
    # Track if this WebSocket connection is the host
    # The host is identified by being the first "stage" type device to connect
    # or by sending a register_as_host message
    is_host = False

    print(f"Session {session_id} unified client connected: {device_id}")

    try:
        # Send current state to new connection
        session_state = get_session_performance_state(session_id)
        await websocket.send_text(
            json.dumps(
                {
                    "type": "session_connected",
                    "session_id": session_id,
                    "device_id": device_id,
                    "performance_state": session_state,
                }
            )
        )

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")

            # === PERFORMANCE & PLAYER STATE MESSAGES ===
            if message_type == "register_as_host":
                # Host device registers itself with its REST API device_id
                rest_device_id = message.get("device_id")
                if rest_device_id and rest_device_id == host_device_id:
                    is_host = True
                    print(f"🏠 Host registered for session {session_id}: {device_id} (REST ID: {rest_device_id})")
                    await websocket.send_text(
                        json.dumps({"type": "host_registered", "success": True})
                    )
                else:
                    await websocket.send_text(
                        json.dumps({"type": "host_registered", "success": False, "error": "Invalid host device ID"})
                    )
            
            elif message_type == "join_performance":
                await websocket.send_text(
                    json.dumps(
                        {"type": "performance_state", "state": get_session_performance_state(session_id)}
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
                session_state = get_session_performance_state(session_id)
                if message_type == "playback_play":
                    session_state["is_playing"] = True
                elif message_type == "playback_pause":
                    session_state["is_playing"] = False
                elif message_type == "reset_player_state":
                    session_state["current_time"] = 0
                    session_state["is_playing"] = False
                elif message_type in ["song_loaded", "song_ready"]:
                    # Update song info from message
                    song_id = message.get("songId")
                    duration = message.get("duration", 0)
                    if song_id:
                        session_state["current_song_id"] = song_id
                    if duration > 0:
                        session_state["duration"] = duration
                    session_state["current_time"] = message.get(
                        "currentTime", 0
                    )
                    session_state["is_playing"] = message.get(
                        "isPlaying", False
                    )
                    session_state["is_ready"] = message.get(
                        "isReady", message_type == "song_ready"
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
        print(f"Session {session_id} unified client disconnected: {device_id} (is_host: {is_host})")
        
        # If host disconnected, terminate the session for all connected devices
        if is_host:
            print(f"🛑 Host disconnected from session {session_id} - terminating session")
            
            # Broadcast session_ended to all connected devices
            await manager.broadcast_to_room(
                session_room,
                {"type": "session_ended", "reason": "Host disconnected"},
                exclude=websocket,
            )
            
            # Mark the session as inactive in the database
            db = SessionLocal()
            try:
                from app.db.models import KaraokeSession
                
                session = (
                    db.query(KaraokeSession)
                    .filter(KaraokeSession.session_id == session_id)
                    .first()
                )
                if session:
                    session.is_active = False
                    db.commit()
                    print(f"📝 Session {session_id} marked as inactive in database")
            except Exception as e:
                print(f"❌ Failed to update session status in database: {e}")
            finally:
                db.close()
            
            # Clean up performance state for this session
            cleanup_session_performance_state(session_id)
            
            # Force close all other connections in this session
            if session_room in manager.rooms:
                connections_to_close = [conn for conn in manager.rooms[session_room] if conn != websocket]
                for conn in connections_to_close:
                    try:
                        await conn.close(code=1000, reason="Session ended by host")
                        print(f"🔌 Force closed connection {id(conn)} for session {session_id}")
                    except Exception as e:
                        print(f"❌ Failed to close connection {id(conn)}: {e}")
                
                # Clear the room
                manager.rooms[session_room] = []
        
        manager.disconnect(websocket)
        manager.leave_session(device_id, session_id)


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
        session_state = get_session_performance_state(session_id)
        await websocket.send_text(
            json.dumps({"type": "performance_state", "state": session_state})
        )

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")

            if message_type == "join_performance":
                await websocket.send_text(
                    json.dumps(
                        {"type": "performance_state", "state": get_session_performance_state(session_id)}
                    )
                )

            elif message_type == "update_performance_control":
                control_name = message.get("control")
                value = message.get("value")
                session_state = get_session_performance_state(session_id)

                if control_name and control_name in session_state:
                    session_state[control_name] = value

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
                session_state = get_session_performance_state(session_id)

                if is_playing is not None:
                    session_state["is_playing"] = is_playing
                if current_time is not None:
                    session_state["current_time"] = current_time
                if duration is not None:
                    session_state["duration"] = duration

                await websocket.send_text(
                    json.dumps(
                        {"type": "performance_state", "state": session_state}
                    )
                )

            elif message_type in [
                "playback_play",
                "playback_pause",
                "reset_player_state",
            ]:
                session_state = get_session_performance_state(session_id)
                if message_type == "playback_play":
                    session_state["is_playing"] = True
                elif message_type == "playback_pause":
                    session_state["is_playing"] = False
                elif message_type == "reset_player_state":
                    session_state["current_time"] = 0
                    session_state["is_playing"] = False

                # Broadcast to all devices in this session
                await manager.broadcast_to_room(
                    performance_room,
                    {"type": message_type, "state": session_state},
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
