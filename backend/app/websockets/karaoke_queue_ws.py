"""
WebSocket event handlers for the karaoke queue.

This module handles real-time updates for the karaoke queue, such as
queue updates and notifications to connected clients.
"""

from flask_socketio import emit, join_room, leave_room
from app.db import SessionLocal
from app.db.models import KaraokeQueueItem, DbSong
from sqlalchemy.orm import joinedload


def register_handlers(socketio):
    """Register WebSocket event handlers for the karaoke queue."""

    @socketio.on("join_queue_room")
    def on_join_queue(data):
        """Client joins the karaoke queue room for real-time updates."""
        room = "karaoke_queue"
        join_room(room)
        emit("queue_joined", {"room": room})

    @socketio.on("leave_queue_room")
    def on_leave_queue(data):
        """Client leaves the karaoke queue room."""
        room = "karaoke_queue"
        leave_room(room)
        emit("queue_left", {"room": room})

    def broadcast_queue_update():
        """Broadcast queue update to all clients in the queue room."""
        session = SessionLocal()
        try:
            # Get queue items with song data
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
                    queue_data.append({
                        "id": item.id,
                        "songId": item.song_id,
                        "singer": item.singer_name,
                        "position": item.position,
                        "addedAt": item.created_at.isoformat() if hasattr(item, 'created_at') and item.created_at else None,
                        "song": {
                            "id": item.song.id,
                            "title": item.song.title,
                            "artist": item.song.artist,
                            "album": item.song.album,
                            "durationMs": item.song.duration_ms,
                            "coverArt": getattr(item.song, 'cover_art_url', None),
                            "status": item.song.status,
                            "syncedLyrics": item.song.synced_lyrics,
                            "plainLyrics": item.song.plain_lyrics
                        }
                    })
            
            socketio.emit("queue_updated", {"items": queue_data}, room="karaoke_queue")
        except Exception as e:
            print(f"Error broadcasting queue update: {e}")
        finally:
            session.close()
    
    # Make the broadcast function available to other modules
    socketio.broadcast_queue_update = broadcast_queue_update
    
    return socketio
