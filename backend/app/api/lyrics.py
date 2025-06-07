from flask import Blueprint, request, jsonify, current_app

from ..services.lyrics_service import LyricsService
from ..db.database import create_or_update_song
from ..exceptions import ServiceError, ValidationError

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
        
        current_app.logger.info(f"Found {len(results)} lyrics results for query: {query}")
        return jsonify(results), 200

    except ServiceError as e:
        current_app.logger.error(f"Service error searching lyrics: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"Error searching lyrics: {str(e)}")
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
            current_app.logger.info(f"Successfully saved lyrics for song {song_id}")
            return jsonify({"message": "Lyrics saved successfully"}), 200
        else:
            return jsonify({"error": "Failed to save lyrics"}), 500
            
    except ValidationError as e:
        current_app.logger.warning(f"Validation error saving lyrics for {song_id}: {e}")
        return jsonify({"error": f"Invalid lyrics: {str(e)}"}), 400
    except ServiceError as e:
        current_app.logger.error(f"Service error saving lyrics for {song_id}: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error saving lyrics for {song_id}: {e}")
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
            current_app.logger.info(f"Retrieved local lyrics for song {song_id}")
            return jsonify({"lyrics": lyrics_text}), 200
        else:
            current_app.logger.info(f"No local lyrics found for song {song_id}")
            return jsonify({"error": "No lyrics found"}), 404
            
    except ServiceError as e:
        current_app.logger.error(f"Service error getting lyrics for {song_id}: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error getting lyrics for {song_id}: {e}")
        return jsonify({"error": "Failed to get lyrics"}), 500
