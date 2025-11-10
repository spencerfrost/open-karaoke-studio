import logging

from app.db.database import get_db_session
from app.db.models.song import DbSong
from app.services.youtube_music_service import YoutubeMusicService
from flask import Blueprint, jsonify, request

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
        service = YoutubeMusicService()
        results = service.search_songs(query, limit=limit)
        
        # Check which songs already exist in library
        # Use both video_id (exact) and artist+title (fuzzy) matching
        video_ids = [r["videoId"] for r in results if "videoId" in r]
        existing_video_ids = set()
        existing_songs_by_artist_title = set()
        
        if video_ids or results:
            with get_db_session() as session:
                # Check by video_id for exact YouTube matches
                if video_ids:
                    existing_songs = session.query(DbSong.video_id).filter(
                        DbSong.video_id.in_(video_ids)
                    ).all()
                    existing_video_ids = {song.video_id for song in existing_songs}
                
                # Check by artist + title for fuzzy matches (case-insensitive)
                for result in results:
                    artist = result.get("artist", "").strip()
                    title = result.get("title", "").strip()
                    if artist and title:
                        existing = session.query(DbSong.id).filter(
                            DbSong.artist.ilike(artist),
                            DbSong.title.ilike(title)
                        ).first()
                        if existing:
                            existing_songs_by_artist_title.add((artist.lower(), title.lower()))
        
        # Add existsInLibrary flag to each result
        for result in results:
            video_id = result.get("videoId")
            artist = result.get("artist", "").strip().lower()
            title = result.get("title", "").strip().lower()
            
            result["existsInLibrary"] = (
                video_id in existing_video_ids or 
                (artist, title) in existing_songs_by_artist_title
            )
        
        return jsonify({"results": results, "error": None}), 200
    except Exception as e:
        logger.error("YouTube Music search failed: %s", e, exc_info=True)
        return jsonify({"results": [], "error": str(e)}), 500
