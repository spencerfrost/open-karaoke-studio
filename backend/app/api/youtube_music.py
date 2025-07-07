import logging

from flask import Blueprint, jsonify, request

from app.services.youtube_music_service import YouTubeMusicService

logger = logging.getLogger(__name__)

youtube_music_bp = Blueprint("youtube_music", __name__, url_prefix="/api/youtube-music")


@youtube_music_bp.route("/search", methods=["GET"])
def search_youtube_music():
    query = request.args.get("q", "")
    limit = request.args.get("limit", 10, type=int)
    if not query:
        logger.warning("Missing query parameter for YouTube Music search.")
        return jsonify({"error": "Missing query parameter 'q'"}), 400
    try:
        service = YouTubeMusicService()
        results = service.search_songs(query, limit=limit)
        return jsonify({"results": results, "error": None}), 200
    except Exception as e:
        logger.error("YouTube Music search failed: %s", e, exc_info=True)
        return jsonify({"results": [], "error": str(e)}), 500
