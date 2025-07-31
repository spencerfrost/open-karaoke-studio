from app.db import SessionLocal
from app.db.models import DbSong, KaraokeQueueItem
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.orm import joinedload

karaoke_queue_bp = Blueprint("karaoke_queue", __name__, url_prefix="/api/karaoke-queue")


@karaoke_queue_bp.route("", methods=["GET"])
def get_queue():
    """Retrieve the current karaoke queue with song details."""
    session = SessionLocal()
    try:
        queue = (
            session.query(KaraokeQueueItem)
            .options(joinedload(KaraokeQueueItem.song))
            .order_by(KaraokeQueueItem.position)
            .all()
        )
        result = []
        for item in queue:
            if item.song:  # Ensure song exists
                result.append(
                    {
                        "id": item.id,
                        "songId": item.song_id,
                        "singer": item.singer_name,
                        "position": item.position,
                        "addedAt": (
                            item.created_at.isoformat()
                            if hasattr(item, "created_at") and item.created_at
                            else None
                        ),
                        "song": {
                            "id": item.song.id,
                            "title": item.song.title,
                            "artist": item.song.artist,
                            "album": item.song.album,
                            "durationMs": item.song.duration_ms,
                            "coverArt": getattr(item.song, "cover_art_url", None),
                            "syncedLyrics": item.song.synced_lyrics,
                            "plainLyrics": item.song.plain_lyrics,
                        },
                    }
                )
        return jsonify(result)
    finally:
        session.close()


@karaoke_queue_bp.route("", methods=["POST"])
def add_to_queue():
    """Add a new item to the karaoke queue."""
    data = request.json
    if not data or "singer" not in data or "songId" not in data:
        return (
            jsonify(
                {
                    "error": "Missing required fields",
                    "code": "MISSING_PARAMETERS",
                    "details": {"required": ["singer", "songId"]},
                }
            ),
            400,
        )
    session = SessionLocal()
    try:
        # Check if song exists
        song = session.query(DbSong).filter(DbSong.id == data["songId"]).first()
        if not song:
            return jsonify({"error": "Song not found"}), 404

        max_position = (
            session.query(KaraokeQueueItem.position)
            .order_by(KaraokeQueueItem.position.desc())
            .first()
        )
        new_position = (max_position[0] + 1) if max_position else 1
        new_item = KaraokeQueueItem(
            singer_name=data["singer"],
            song_id=data["songId"],
            position=new_position,
        )
        session.add(new_item)
        session.commit()

        # Broadcast update via WebSocket if available
        try:
            socketio = current_app.extensions.get("socketio")
            if socketio and hasattr(socketio, "broadcast_queue_update"):
                socketio.broadcast_queue_update()
        except Exception as e:
            print(f"WebSocket broadcast error: {e}")

        # Return the created item with song data
        session.refresh(new_item)
        result = {
            "id": new_item.id,
            "songId": new_item.song_id,
            "singer": new_item.singer_name,
            "position": new_item.position,
            "addedAt": (
                new_item.created_at.isoformat()
                if hasattr(new_item, "created_at") and new_item.created_at
                else None
            ),
            "song": {
                "id": song.id,
                "title": song.title,
                "artist": song.artist,
                "album": song.album,
                "durationMs": song.duration_ms,
                "coverArt": getattr(song, "cover_art_url", None),
                "syncedLyrics": song.synced_lyrics,
                "plainLyrics": song.plain_lyrics,
            },
        }
        return jsonify(result), 201
    finally:
        session.close()


@karaoke_queue_bp.route("/<int:item_id>", methods=["DELETE"])
def remove_from_queue(item_id):
    """Remove an item from the karaoke queue."""
    session = SessionLocal()
    try:
        item = (
            session.query(KaraokeQueueItem)
            .filter(KaraokeQueueItem.id == item_id)
            .first()
        )
        if not item:
            return jsonify({"error": "Item not found"}), 404
        session.delete(item)
        session.commit()

        # Reindex positions to be contiguous
        remaining_items = (
            session.query(KaraokeQueueItem)
            .order_by(KaraokeQueueItem.position)
            .all()
        )
        for idx, queue_item in enumerate(remaining_items):
            queue_item.position = idx  # type: ignore
        session.commit()

        # Broadcast update via WebSocket if available
        try:
            socketio = current_app.extensions.get("socketio")
            if socketio and hasattr(socketio, "broadcast_queue_update"):
                socketio.broadcast_queue_update()
        except Exception as e:
            print(f"WebSocket broadcast error: {e}")

        return jsonify({"success": True})
    finally:
        session.close()


@karaoke_queue_bp.route("/reorder", methods=["PUT"])
def reorder_queue():
    """Reorder the karaoke queue."""
    data = request.json
    if not data or "queue" not in data or not isinstance(data["queue"], list):
        return (
            jsonify(
                {
                    "error": "Missing or invalid queue data",
                    "code": "MISSING_PARAMETERS",
                    "details": {"required": ["queue"]},
                }
            ),
            400,
        )
    session = SessionLocal()
    try:
        for item in data["queue"]:
            queue_item = (
                session.query(KaraokeQueueItem)
                .filter(KaraokeQueueItem.id == item["id"])
                .first()
            )
            if queue_item:
                queue_item.position = item["position"]
        session.commit()

        # Broadcast update via WebSocket if available
        try:
            socketio = current_app.extensions.get("socketio")
            if socketio and hasattr(socketio, "broadcast_queue_update"):
                socketio.broadcast_queue_update()
        except Exception as e:
            print(f"WebSocket broadcast error: {e}")

        return jsonify({"success": True})
    finally:
        session.close()


@karaoke_queue_bp.route("/<int:item_id>/play", methods=["POST"])
def play_queue_item(item_id):
    """Play a specific item from the queue (moves it to the player)."""
    session = SessionLocal()
    try:
        item = (
            session.query(KaraokeQueueItem)
            .options(joinedload(KaraokeQueueItem.song))
            .filter(KaraokeQueueItem.id == item_id)
            .first()
        )
        if not item:
            return jsonify({"error": "Item not found"}), 404

        if not item.song:
            return jsonify({"error": "Song not found"}), 404

        # Remove current song (position 0) if it exists
        current_song = (
            session.query(KaraokeQueueItem)
            .filter(KaraokeQueueItem.position == 0)
            .first()
        )
        if current_song:
            session.delete(current_song)
        
        # Move the played item to position 0 (current song)
        item.position = 0  # type: ignore
        session.commit()

        # Reindex remaining positions to be contiguous (1, 2, 3, ...)
        remaining_items = (
            session.query(KaraokeQueueItem)
            .filter(KaraokeQueueItem.position > 0)
            .order_by(KaraokeQueueItem.position)
            .all()
        )
        for idx, queue_item in enumerate(remaining_items, start=1):
            queue_item.position = idx  # type: ignore
        session.commit()

        # Broadcast queue update via WebSocket if available
        try:
            socketio = current_app.extensions.get("socketio")
            if socketio and hasattr(socketio, "broadcast_queue_update"):
                socketio.broadcast_queue_update()

            # Also broadcast the song that should be played
            if socketio:
                song_data = {
                    "id": item.song.id,
                    "title": item.song.title,
                    "artist": item.song.artist,
                    "album": item.song.album,
                    "durationMs": item.song.duration_ms,
                    "coverArt": getattr(item.song, "cover_art_url", None),
                    "syncedLyrics": item.song.synced_lyrics,
                    "plainLyrics": item.song.plain_lyrics,
                }
                socketio.emit(
                    "play_song",
                    {"song": song_data, "singer": item.singer_name},
                    room="karaoke_queue",
                )

        except Exception as e:
            print(f"WebSocket broadcast error: {e}")

        # Return the song data for the player
        result = {
            "id": item.song.id,
            "title": item.song.title,
            "artist": item.song.artist,
            "album": item.song.album,
            "durationMs": item.song.duration_ms,
            "coverArt": getattr(item.song, "cover_art_url", None),
            "syncedLyrics": item.song.synced_lyrics,
            "plainLyrics": item.song.plain_lyrics,
            "singer": item.singer_name,
        }
        return jsonify(result)
    finally:
        session.close()
