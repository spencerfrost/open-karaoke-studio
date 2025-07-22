import logging

from app.exceptions import NetworkError, ServiceError, ValidationError
from app.services.lyrics_service import LyricsService
from app.utils.error_handlers import handle_api_error
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)
lyrics_bp = Blueprint("lyrics", __name__, url_prefix="/api/lyrics")


@lyrics_bp.route("/search", methods=["GET"])
@handle_api_error
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
        raise ValidationError(
            "Missing track_name/artist_name information", "MISSING_PARAMETERS"
        )

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

    except ServiceError:
        raise  # Let error handlers deal with it
    except ConnectionError as e:
        raise NetworkError(
            "Failed to connect to lyrics service",
            "LYRICS_CONNECTION_ERROR",
            {"query": query, "error": str(e)},
        ) from e
    except TimeoutError as e:
        raise NetworkError(
            "Lyrics service request timed out",
            "LYRICS_TIMEOUT_ERROR",
            {"query": query, "error": str(e)},
        ) from e
    except Exception as e:
        raise ServiceError(
            "Unexpected error during lyrics search",
            "LYRICS_SEARCH_ERROR",
            {"query": query, "error": str(e)},
        ) from e
