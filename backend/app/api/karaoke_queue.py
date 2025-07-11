from app.db import SessionLocal
from app.db.models import KaraokeQueueItem
from flask import Blueprint, jsonify, request

karaoke_queue_bp = Blueprint("karaoke_queue", __name__, url_prefix="/karaoke-queue")


@karaoke_queue_bp.route("/", methods=["GET"])
def get_queue():
    """Retrieve the current karaoke queue."""
    session = SessionLocal()
    try:
        queue = (
            session.query(KaraokeQueueItem).order_by(KaraokeQueueItem.position).all()
        )
        return jsonify(
            [
                {
                    "id": item.id,
                    "singer_name": item.singer_name,
                    "song_id": item.song_id,
                    "position": item.position,
                }
                for item in queue
            ]
        )
    finally:
        session.close()


@karaoke_queue_bp.route("/", methods=["POST"])
def add_to_queue():
    """Add a new item to the karaoke queue."""
    data = request.json
    if not data or "singer_name" not in data or "song_id" not in data:
        return (
            jsonify(
                {
                    "error": "Missing required fields",
                    "code": "MISSING_PARAMETERS",
                    "details": {"required": ["singer_name", "song_id"]},
                }
            ),
            400,
        )
    session = SessionLocal()
    try:
        max_position = (
            session.query(KaraokeQueueItem.position)
            .order_by(KaraokeQueueItem.position.desc())
            .first()
        )
        new_position = (max_position[0] + 1) if max_position else 1
        new_item = KaraokeQueueItem(
            singer_name=data["singer_name"],
            song_id=data["song_id"],
            position=new_position,
        )
        session.add(new_item)
        session.commit()
        return jsonify({"success": True, "id": new_item.id}), 201
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
        return jsonify({"success": True})
    finally:
        session.close()
