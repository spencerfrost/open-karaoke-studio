# backend/app/api/metadata.py

from flask import Blueprint, jsonify, request, current_app
from ..services.metadata_service import MetadataService
from ..exceptions import ServiceError, ValidationError

# Create a metadata blueprint with the new, clean URL structure
metadata_bp = Blueprint('metadata', __name__, url_prefix='/api/metadata')

@metadata_bp.route('/search', methods=['GET'])
def search_metadata_endpoint():
    """Endpoint to search for song metadata using iTunes Search API."""
    current_app.logger.info("Received metadata search request")
    
    try:
        # Get search terms from query parameters
        title = request.args.get('title', '').strip()
        artist = request.args.get('artist', '').strip()
        album = request.args.get('album', '').strip()
        limit = int(request.args.get('limit', 5))
        sort_by = request.args.get('sort_by', 'relevance')  # For backwards compatibility
        
        # Validate that at least title or artist is provided
        if not title and not artist:
            return jsonify({"error": "At least one of 'title' or 'artist' parameters is required"}), 400
        
        current_app.logger.info(f"Metadata search - Artist: '{artist}', Title: '{title}', Album: '{album}', Limit: {limit}")
        
        # Initialize service
        metadata_service = MetadataService()
        
        # Search using the service layer
        results = metadata_service.search_metadata(artist, title, album, limit)
        
        # Format response using service
        search_params = {
            "artist": artist,
            "title": title,
            "album": album,
            "limit": limit,
            "sort_by": sort_by
        }
        response_data = metadata_service.format_metadata_response(results, search_params)
        
        current_app.logger.info(f"Metadata search returned {len(results)} results")
        return jsonify(response_data), 200
            
    except ValueError as e:
        current_app.logger.error(f"ValueError in metadata search: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error during metadata search: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred during metadata search"}), 500
