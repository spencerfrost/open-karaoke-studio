from flask import Blueprint, request, jsonify, current_app

from ..services.lyrics_service import make_request
from ..db.database import create_or_update_song

lyrics_bp = Blueprint("lyrics", __name__, url_prefix="/api/lyrics")


@lyrics_bp.route("/search", methods=["GET", "POST"])
def search_lyrics():
    """
    Search for lyrics via POST (with JSON body) or GET (with query parameters).

    Parameters:
    - track_name: Song title (required)
    - artist_name: Artist name (required)
    - album_name: Album name (optional) - can improve search results
    - song_id: Optional song ID to update database metadata if lyrics are found
    """
    # Extract parameters based on request method
    song_id, track_name, artist_name, album_name = _extract_lyrics_search_params()
    if not track_name or not artist_name:
        return jsonify({"error": "Missing track_name/artist_name information"}), 400

    search_params = {"track_name": track_name, "artist_name": artist_name}

    # Add album to search params if provided
    if album_name:
        search_params["album_name"] = album_name

    try:
        # Call the lyrics service
        status, data = make_request("/api/search", search_params)

        if data:
            if "plainLyrics" in data and isinstance(data["plainLyrics"], str):
                current_app.logger.info(f"plainLyrics found")
            if "syncedLyrics" in data and isinstance(data["syncedLyrics"], str):
                current_app.logger.info(f"syncedLyrics found")

        # Update database if needed
        if song_id and status == 200 and data:
            _update_song_metadata(song_id, data)

        return jsonify(data), status
    except Exception as e:
        current_app.logger.error(f"Error fetching lyrics: {str(e)}")
        return jsonify({"error": f"Failed to fetch lyrics: {str(e)}"}), 500


def _extract_lyrics_search_params():
    """Helper function to extract parameters from either POST or GET requests."""
    if request.method == "POST":
        params = request.get_json()
        if not params:
            return None, None, None, None

        song_id = params.get("song_id")
        track_name = params.get("track_name")
        artist_name = params.get("artist_name")
        album_name = params.get("album_name")
    else:  # GET
        song_id = request.args.get("song_id")
        track_name = request.args.get("track_name")
        artist_name = request.args.get("artist_name")
        album_name = request.args.get("album_name")

    return song_id, track_name, artist_name, album_name


def _update_song_metadata(song_id, data):
    """Helper function to update song metadata in the database."""
    current_app.logger.debug(f"Updating metadata for song {song_id}")
    try:
        from ..db.models import SongMetadata

        metadata = SongMetadata(
            lyrics=data.get("plainLyrics"), syncedLyrics=data.get("syncedLyrics")
        )
        create_or_update_song(song_id, metadata)
    except Exception as e:
        current_app.logger.error(f"Error updating song metadata: {str(e)}")


@lyrics_bp.route("/get", methods=["GET"])
def get_lyrics():
    required = ("track_name", "artist_name", "album_name", "duration")
    missing = [p for p in required if not request.args.get(p)]
    if missing:
        return jsonify({"error": f"Missing parameters: {', '.join(missing)}"}), 400
    params = {p: request.args.get(p) for p in required}
    status, data = make_request("/api/get", params)
    return jsonify(data), status


@lyrics_bp.route("/get-cached", methods=["GET"])
def get_cached_lyrics():
    required = ("track_name", "artist_name", "album_name", "duration")
    missing = [p for p in required if not request.args.get(p)]
    if missing:
        return jsonify({"error": f"Missing parameters: {', '.join(missing)}"}), 400
    params = {p: request.args.get(p) for p in required}
    status, data = make_request("/api/get-cached", params)
    return jsonify(data), status
