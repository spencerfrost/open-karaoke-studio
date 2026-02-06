"""
Queue broadcasting utilities for Open Karaoke Studio

Provides helper functions for broadcasting queue updates to WebSocket clients.
Queue management is handled through the unified session WebSocket endpoint.
"""

import logging

from sqlalchemy.orm import joinedload, subqueryload

from app.db.database import get_db_session
from app.db.models.queue import KaraokeQueueItem
from app.db.models.song import DbSong

from .connection_manager import SessionConnectionManager

logger = logging.getLogger(__name__)


async def get_current_queue_state(session_id: str):
    """
    Get current karaoke queue state for a specific session using real database queries.
    Updated for PostgreSQL compatibility.
    """
    try:
        with get_db_session() as session:
            # Get queue items with song data for the specific session
            queue_items = (
                session.query(KaraokeQueueItem)
                .filter(KaraokeQueueItem.session_id == session_id)
                .options(
                    joinedload(KaraokeQueueItem.song).subqueryload(DbSong.lyrics)
                )
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
                                "syncedLyrics": item.song._get_active_lyrics_content("synced"),
                                "plainLyrics": item.song._get_active_lyrics_content("plain"),
                            },
                        }
                    )
            return queue_data
    except Exception as e:
        logger.error(f"Error getting queue state from PostgreSQL: {e}")
        return []


# Queue broadcasting functions
async def broadcast_queue_update(manager: SessionConnectionManager, session_id: str):
    """Broadcast queue update to a specific session room."""
    queue_data = await get_current_queue_state(session_id)
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
