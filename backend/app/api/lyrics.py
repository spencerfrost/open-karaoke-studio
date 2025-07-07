import logging

from flask import Blueprint, current_app, jsonify, request

from ..exceptions import FileSystemError, NetworkError, ServiceError, ValidationError
from ..schemas.requests import SaveLyricsRequest
from ..services.lyrics_service import LyricsService
from ..utils.error_handlers import handle_api_error
from ..utils.validation import validate_json_request

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
        )
    except TimeoutError as e:
        raise NetworkError(
            "Lyrics service request timed out",
            "LYRICS_TIMEOUT_ERROR",
            {"query": query, "error": str(e)},
        )
    except Exception as e:
        raise ServiceError(
            "Unexpected error during lyrics search",
            "LYRICS_SEARCH_ERROR",
            {"query": query, "error": str(e)},
        )


@lyrics_bp.route("/<string:song_id>", methods=["POST"])
@handle_api_error
@validate_json_request(SaveLyricsRequest)
def save_song_lyrics(song_id: str, validated_data: SaveLyricsRequest = None):
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
        lyrics_service = LyricsService()

        # Validate and save lyrics
        success = lyrics_service.save_lyrics(song_id, validated_data.lyrics)

        if success:
            logger.info("Successfully saved lyrics for song %s", song_id)
            return jsonify({"message": "Lyrics saved successfully"}), 200
        else:
            raise ServiceError(
                "Failed to save lyrics", "LYRICS_SAVE_ERROR", {"song_id": song_id}
            )

    except ValidationError:
        raise  # Let error handlers deal with it
    except ServiceError:
        raise  # Let error handlers deal with it
    except OSError as e:
        # File system errors (disk full, permission denied, etc.)
        raise FileSystemError(
            "Failed to save lyrics to file system",
            "LYRICS_FILE_ERROR",
            {"song_id": song_id, "error": str(e)},
        )
    except Exception as e:
        raise ServiceError(
            "Unexpected error saving lyrics",
            "LYRICS_SAVE_ERROR",
            {"song_id": song_id, "error": str(e)},
        )


@lyrics_bp.route("/<string:song_id>", methods=["GET"])
@handle_api_error
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
            from ..exceptions import ResourceNotFoundError

            raise ResourceNotFoundError("Song lyrics", song_id)

    except ServiceError:
        raise  # Let error handlers deal with it
    except OSError as e:
        # File system errors (can't read lyrics file)
        raise FileSystemError(
            "Failed to read lyrics from file system",
            "LYRICS_FILE_READ_ERROR",
            {"song_id": song_id, "error": str(e)},
        )
    except Exception as e:
        raise ServiceError(
            "Unexpected error retrieving lyrics",
            "LYRICS_GET_ERROR",
            {"song_id": song_id, "error": str(e)},
        )
