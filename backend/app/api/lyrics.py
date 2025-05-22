from flask import Blueprint, request, jsonify, current_app

from ..services.lyrics_service import make_request
from ..db.database import create_or_update_song

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
    
    query_parts = [artist_name, track_name]
    if album_name:
        query_parts.append(album_name)
    
    combined_query = " ".join(query_parts)
    search_params = {"q": combined_query}

    try:
        status, data = make_request("/api/search", search_params)
        
        if isinstance(data, list):
            current_app.logger.info(f"Found {len(data)} lyrics results")
        
        # Return the raw response from LRCLIB
        return jsonify(data), status

    except Exception as e:
        current_app.logger.error(f"Error fetching lyrics: {str(e)}")
        return jsonify({"error": f"Failed to fetch lyrics: {str(e)}"}), 500
