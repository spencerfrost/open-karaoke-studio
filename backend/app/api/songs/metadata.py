"""Songs Metadata API Endpoints"""

from app.db.database import get_db_session
from app.repositories.song_repository import SongRepository
from app.services.metadata_service import MetadataService
from app.utils.error_handlers import handle_api_error
from flask import jsonify, request

from . import logger, song_bp


@song_bp.route("/metadata/auto", methods=["POST"])
@handle_api_error
def auto_save_itunes_metadata() -> tuple:
    """
    Accepts artist, title, album, and song_id.
    Fetches iTunes metadata and saves the first result to the song.
    Returns only success/failure JSON.
    """

    data = request.get_json()
    artist = data.get("artist")
    title = data.get("title")
    album = data.get("album")
    song_id = data.get("song_id")
    if not (artist and title and song_id):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Missing required fields: artist, title, song_id",
                }
            ),
            400,
        )
    try:
        metadata_service = MetadataService()
        results = metadata_service.search_metadata(
            artist=artist, title=title, album=album, limit=1
        )
        if not results:
            logger.warning(f"No iTunes metadata found for {artist} - {title} - {album}")
            return jsonify({"success": False, "error": "No iTunes metadata found"}), 404
        # Get the song from DB
        with get_db_session() as session:
            repo = SongRepository(session)
            song = repo.fetch(song_id)
        if not song:
            logger.error(f"Song not found: {song_id}")
            return jsonify({"success": False, "error": "Song not found"}), 404
        itunes_result = results[0].copy()
        if "id" in itunes_result:
            # Map iTunes 'id' to 'mbid' (or 'metadataId' if that's your model field)
            itunes_result["mbid"] = itunes_result["id"]
            del itunes_result["id"]

        # Now only update fields that exist on the model, and never the primary key 'id'
        update_fields = {k: v for k, v in itunes_result.items() if hasattr(song, k) and k != "id"}
        with get_db_session() as session:
            repo = SongRepository(session)
            updated_song = repo.update(song_id, **update_fields)
        if not updated_song:
            logger.error(f"Failed to update song metadata for {song_id}")
            return (
                jsonify({"success": False, "error": "Failed to update song metadata"}),
                500,
            )
        logger.info(f"Auto-saved iTunes metadata for song {song_id}")
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Failed to auto-save iTunes metadata: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
