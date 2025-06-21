import logging
from flask import Blueprint, current_app, jsonify, request

from ..exceptions import ServiceError, ValidationError
from ..services.lyrics_service import LyricsService

logger = logging.getLogger(__name__)
lyrics_bp = Blueprint("lyrics", __name__, url_prefix="/api/lyrics")


@lyrics_bp.route("/search", methods=["GET"])
def search_lyrics():
    """
    Search for lyrics via GET (with query parameters).

    Parameters:
    - track_name: Song title (required)
    - artist_name: Artist name (required)
    - album_name: Album name (optional) - can improve search results

    Returns:
    - A JSON array with lyrics results from LRCLIB
    """
    track_name = request.args.get("track_name")
    artist_name = request.args.get("artist_name")
    album_name = request.args.get("album_name")

    if not track_name or not artist_name:
        return jsonify({"error": "Missing track_name/artist_name information"}), 400

    try:
        lyrics_service = LyricsService()

        # Build query string from parameters
        query_parts = [artist_name, track_name]
        if album_name:
            query_parts.append(album_name)

        query = " ".join(query_parts)
        results = lyrics_service.search_lyrics(query)

        logger.info("Found %s lyrics results for query: %s", len(results), query)
        return jsonify(results), 200

    except ServiceError as e:
        logger.error("Service error searching lyrics: %s", e)
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error("Error searching lyrics: %s", str(e))
        return jsonify({"error": f"Failed to search lyrics: {str(e)}"}), 500


@lyrics_bp.route("/<string:song_id>", methods=["POST"])
def save_song_lyrics(song_id: str):
    """
    Save lyrics for a specific song.

    Parameters:
    - song_id: The ID of the song to save lyrics for

    Request body:
    - lyrics: The lyrics text to save

    Returns:
    - Success/error message
    """
    try:
        data = request.get_json()
        if not data or "lyrics" not in data:
            return jsonify({"error": "Missing lyrics in request body"}), 400

        lyrics_text = data["lyrics"]
        if not isinstance(lyrics_text, str):
            return jsonify({"error": "Lyrics must be a string"}), 400

        lyrics_service = LyricsService()

        # Validate and save lyrics
        success = lyrics_service.save_lyrics(song_id, lyrics_text)

        if success:
            logger.info("Successfully saved lyrics for song %s", song_id)
            return jsonify({"message": "Lyrics saved successfully"}), 200
        else:
            return jsonify({"error": "Failed to save lyrics"}), 500

    except ValidationError as e:
        logger.warning("Validation error saving lyrics for %s: %s", song_id, e)
        return jsonify({"error": f"Invalid lyrics: {str(e)}"}), 400
    except ServiceError as e:
        logger.error("Service error saving lyrics for %s: %s", song_id, e)
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error("Unexpected error saving lyrics for %s: %s", song_id, e)
        return jsonify({"error": "Failed to save lyrics"}), 500


@lyrics_bp.route("/<string:song_id>", methods=["GET"])
def get_song_lyrics_local(song_id: str):
    """
    Get locally stored lyrics for a specific song.

    Parameters:
    - song_id: The ID of the song to get lyrics for

    Returns:
    - Lyrics text if found, error message otherwise
    """
    try:
        lyrics_service = LyricsService()
        lyrics_text = lyrics_service.get_lyrics(song_id)

        if lyrics_text:
            logger.info("Retrieved local lyrics for song %s", song_id)
            return jsonify({"lyrics": lyrics_text}), 200
        else:
            logger.info("No local lyrics found for song %s", song_id)
            return jsonify({"error": "No lyrics found"}), 404

    except ServiceError as e:
        logger.error("Service error getting lyrics for %s: %s", song_id, e)
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error("Unexpected error getting lyrics for %s: %s", song_id, e)
        return jsonify({"error": "Failed to get lyrics"}), 500
