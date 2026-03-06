"""
Queue broadcasting utilities for Open Karaoke Studio

Provides helper functions for broadcasting queue updates to WebSocket clients.
Queue management is handled through the unified session WebSocket endpoint.
"""

import logging

from app.db.database import get_db_session
from app.db.models.queue import KaraokeQueueItem
from app.db.models.session import SessionPlaybackState
from app.db.models.song import DbSong
from sqlalchemy.orm import joinedload, subqueryload

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
                .options(joinedload(KaraokeQueueItem.song).subqueryload(DbSong.lyrics))
                .order_by(KaraokeQueueItem.position, KaraokeQueueItem.id)
                .all()
            )

            playback_state = (
                session.query(SessionPlaybackState)
                .filter(SessionPlaybackState.session_id == session_id)
                .first()
            )

            current_item_id = (
                playback_state.current_queue_item_id if playback_state else None
            )
            queue_items_by_id = {item.id: item for item in queue_items}

            current_item = None
            if current_item_id is not None:
                candidate = queue_items_by_id.get(current_item_id)
                if candidate and candidate.song:
                    current_item = candidate

            if current_item is None:
                current_item = next(
                    (item for item in queue_items if item.position == 0 and item.song),
                    None,
                )

            # Format data for frontend
            upcoming_data = []
            for idx, item in enumerate(
                [
                    item
                    for item in queue_items
                    if item.song
                    and (current_item is None or item.id != current_item.id)
                ],
                start=1,
            ):
                if item.song:  # Ensure song exists
                    # Handle potential null timestamps gracefully
                    added_at = None
                    if hasattr(item, "created_at") and item.created_at:
                        added_at = item.created_at.isoformat()

                    upcoming_data.append(
                        {
                            "id": item.id,
                            "songId": item.song_id,
                            "singer": item.singer_name,
                            "position": idx,
                            "addedAt": added_at,
                            "song": {
                                "id": item.song.id,
                                "title": item.song.title,
                                "artist": item.song.artist,
                                "album": item.song.album,
                                "duration": item.song.duration,
                                "coverArt": getattr(item.song, "cover_art_url", None),
                                "syncedLyrics": item.song._get_active_lyrics_content(
                                    "synced"
                                ),
                                "plainLyrics": item.song._get_active_lyrics_content(
                                    "plain"
                                ),
                            },
                        }
                    )

            current_data = None
            if current_item and current_item.song:
                added_at = None
                if hasattr(current_item, "created_at") and current_item.created_at:
                    added_at = current_item.created_at.isoformat()

                current_data = {
                    "id": current_item.id,
                    "songId": current_item.song_id,
                    "singer": current_item.singer_name,
                    "position": 0,
                    "addedAt": added_at,
                    "song": {
                        "id": current_item.song.id,
                        "title": current_item.song.title,
                        "artist": current_item.song.artist,
                        "album": current_item.song.album,
                        "duration": current_item.song.duration,
                        "coverArt": getattr(current_item.song, "cover_art_url", None),
                        "syncedLyrics": current_item.song._get_active_lyrics_content(
                            "synced"
                        ),
                        "plainLyrics": current_item.song._get_active_lyrics_content(
                            "plain"
                        ),
                    },
                }

            items = [current_data] if current_data else []
            items.extend(upcoming_data)

            return {
                "current": current_data,
                "upcoming": upcoming_data,
                "items": items,
            }
    except Exception as e:
        logger.error(f"Error getting queue state from PostgreSQL: {e}")
        return {"current": None, "upcoming": [], "items": []}


# Queue broadcasting functions
async def broadcast_queue_update(manager: SessionConnectionManager, session_id: str):
    """Broadcast queue update to a specific session room."""
    queue_data = await get_current_queue_state(session_id)
    session_room = manager.get_session_room_name(session_id)
    await manager.broadcast_to_room(
        session_room,
        {
            "type": "queue_updated",
            "current": queue_data.get("current"),
            "upcoming": queue_data.get("upcoming", []),
            "items": queue_data.get("items", []),
        },
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
