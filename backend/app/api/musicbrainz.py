# backend/app/musicbrainz_endpoints.py

from flask import Blueprint, jsonify, request, current_app
from ..services.metadata_service import metadata_service

# Create a blueprint
mb_bp = Blueprint('musicbrainz', __name__, url_prefix='/api/musicbrainz')

@mb_bp.route('/search', methods=['GET'])
def search_musicbrainz_endpoint():
    """Endpoint to search MusicBrainz for song metadata."""
    current_app.logger.info("Received MusicBrainz search request")
    
    try:
        # Get search terms from query parameters
        title = request.args.get('title', '')
        artist = request.args.get('artist', '')
        album = request.args.get('album', '')
        
        # Delegate to metadata service
        results = metadata_service.search_metadata(
            artist=artist,
            title=title, 
            album=album
        )
        
        return jsonify(results), 200
            
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error during MusicBrainz search: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred during MusicBrainz search"}), 500
