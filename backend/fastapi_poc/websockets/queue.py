"""
WebSocket Queue endpoint for Open Karaoke Studio

Handles real-time karaoke queue updates and management.
Replaces Flask-SocketIO queue functionality with FastAPI WebSockets.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import joinedload

# Add the parent directory to the Python path to import from app
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.db.database import get_db_session
from app.db.models.queue import KaraokeQueueItem
from app.db.models.song import DbSong

from .connection_manager import SessionConnectionManager


async def get_current_queue_state():
    """
    Get current karaoke queue state using real database queries.
    Updated for PostgreSQL compatibility.
    """
    try:
        with get_db_session() as session:
            # Get queue items with song data - PostgreSQL handles this efficiently
            queue_items = (
                session.query(KaraokeQueueItem)
                .options(joinedload(KaraokeQueueItem.song))
                .order_by(KaraokeQueueItem.position)
                .all()
            )

            # Format data for frontend
            queue_data = []
            for item in queue_items:
                if item.song:  # Ensure song exists
                    # Handle potential null timestamps gracefully
                    added_at = None
                    if hasattr(item, "created_at") and item.created_at:
                        added_at = item.created_at.isoformat()

                    queue_data.append(
                        {
                            "id": item.id,
                            "songId": item.song_id,
                            "singer": item.singer_name,
                            "position": item.position,
                            "addedAt": added_at,
                            "song": {
                                "id": item.song.id,
                                "title": item.song.title,
                                "artist": item.song.artist,
                                "album": item.song.album,
                                "duration": item.song.duration,
                                "coverArt": getattr(item.song, "cover_art_url", None),
                                "syncedLyrics": item.song.synced_lyrics,
                                "plainLyrics": item.song.plain_lyrics,
                            },
                        }
                    )
            return queue_data
    except Exception as e:
        print(f"Error getting queue state from PostgreSQL: {e}")
        # Fallback to mock data if database fails
        return [
            {
                "id": "queue-item-1",
                "songId": "demo-song-1",
                "singer": "Demo Singer",
                "position": 1,
                "addedAt": datetime.now().isoformat(),
                "song": {
                    "id": "demo-song-1",
                    "title": "Demo Song",
                    "artist": "Demo Artist",
                    "album": "Demo Album",
                    "duration": 180,
                    "coverArt": None,
                    "syncedLyrics": None,
                    "plainLyrics": "Demo lyrics...",
                },
            }
        ]


async def websocket_queue_endpoint(
    websocket: WebSocket, manager: SessionConnectionManager
):
    """
    WebSocket endpoint for real-time karaoke queue updates.
    Replaces Flask-SocketIO queue functionality with FastAPI WebSockets.
    """
    await manager.connect(websocket)
    queue_room = "karaoke_queue"
    await manager.join_room(websocket, queue_room)

    print(f"Queue client connected: {id(websocket)}")

    try:
        # Send connection confirmation
        await websocket.send_text(
            json.dumps({"type": "queue_joined", "room": queue_room})
        )

        # Send current queue state
        queue_data = await get_current_queue_state()
        await websocket.send_text(
            json.dumps({"type": "queue_updated", "items": queue_data})
        )

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")

            if message_type == "join_queue_room":
                # Client explicitly joined queue room
                await websocket.send_text(
                    json.dumps({"type": "queue_joined", "room": queue_room})
                )

                # Send current queue
                queue_data = await get_current_queue_state()
                await websocket.send_text(
                    json.dumps({"type": "queue_updated", "items": queue_data})
                )

                print(f"Client {id(websocket)} joined queue room")

            elif message_type == "leave_queue_room":
                # Client left queue room
                await manager.leave_room(websocket, queue_room)
                await websocket.send_text(
                    json.dumps({"type": "queue_left", "room": queue_room})
                )

                print(f"Client {id(websocket)} left queue room")

            elif message_type == "request_queue_update":
                # Send current queue state on demand
                queue_data = await get_current_queue_state()
                await websocket.send_text(
                    json.dumps({"type": "queue_updated", "items": queue_data})
                )

            else:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                        }
                    )
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Queue client disconnected: {id(websocket)}")


# Queue broadcasting functions
async def broadcast_queue_update(manager: SessionConnectionManager):
    """Broadcast queue update to all active session rooms."""
    queue_data = await get_current_queue_state()

    # Broadcast to all active session rooms
    for session_id in manager.sessions.keys():
        session_room = manager.get_session_room_name(session_id)
        await manager.broadcast_to_room(
            session_room, {"type": "queue_updated", "items": queue_data}
        )


async def broadcast_queue_item_added(
    manager: SessionConnectionManager, item_data: dict
):
    """Broadcast new queue item addition to all clients."""
    await manager.broadcast_to_room(
        "karaoke_queue", {"type": "queue_item_added", "item": item_data}
    )


async def broadcast_queue_item_removed(manager: SessionConnectionManager, item_id: str):
    """Broadcast queue item removal to all clients."""
    await manager.broadcast_to_room(
        "karaoke_queue", {"type": "queue_item_removed", "itemId": item_id}
    )


async def broadcast_queue_reordered(manager: SessionConnectionManager, new_order: list):
    """Broadcast queue reorder to all clients."""
    await manager.broadcast_to_room(
        "karaoke_queue", {"type": "queue_reordered", "items": new_order}
    )
