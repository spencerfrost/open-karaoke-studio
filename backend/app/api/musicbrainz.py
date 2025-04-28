# backend/app/musicbrainz_endpoints.py

from flask import Blueprint, jsonify, request, current_app
from ..services.musicbrainz_service import search_musicbrainz

# Create a blueprint
mb_bp = Blueprint('musicbrainz', __name__, url_prefix='/api/musicbrainz')

@mb_bp.route('/search', methods=['POST'])
def search_musicbrainz_endpoint():
    """Endpoint to search MusicBrainz for song metadata."""
    current_app.logger.info("Received MusicBrainz search request")
    
    try:
        # Get search terms from request
        data = request.get_json()
        if not data:
            return jsonify({"error": "No search terms provided"}), 400
            
        title = data.get('title', '')
        artist = data.get('artist', '')
        
        if not title and not artist:
            return jsonify({"error": "At least one search term (title or artist) is required"}), 400
            
        # Perform MusicBrainz search
        results = search_musicbrainz(artist, title)
        
        if not results:
            return jsonify([]), 200  # Return empty array, not an error
            
        # Format results for frontend
        formatted_results = []
        for result in results:
            formatted_results.append({
                "musicbrainzId": result.get("mbid"),
                "title": result.get("title"),
                "artist": result.get("artist"),
                "album": result.get("release", {}).get("title"),
                "year": result.get("release", {}).get("date"),
                "genre": result.get("genre"),
                "language": result.get("language"),
                "coverArt": result.get("coverArtUrl")
            })
            
        return jsonify(formatted_results), 200
            
    except Exception as e:
        current_app.logger.error(f"Error during MusicBrainz search: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred during MusicBrainz search"}), 500
