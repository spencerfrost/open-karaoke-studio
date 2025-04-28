from flask import Blueprint, request, jsonify, current_app

from ..services.lyrics_service import make_request
from ..db.database import create_or_update_song

lyrics_bp = Blueprint('lyrics', __name__, url_prefix='/api/lyrics')

@lyrics_bp.route('/search', methods=['POST'])
def search_lyrics():
    """ Search for lyrics via POST with body containing artist and title. """
    params = request.get_json()
    song_id = params.get('song_id')
    if not params:
        return jsonify({'error': 'No params provided'}), 400
    if 'title' not in params or 'artist' not in params:
        return jsonify({'error': 'Missing title or artist'}), 400
    
    try:
        status, data = make_request('/api/search', params)
        if song_id and status == 200 and data:
            # log the data for debugging json indentation
            current_app.logger.debug(f"Data: {data}")
            
            try:
                from ..db.models import SongMetadata
                metadata = SongMetadata(
                    lyrics=data.get('plainLyrics'),
                    syncedLyrics=data.get('syncedLyrics')
                )
                create_or_update_song(song_id, metadata)
            except Exception as e:
                current_app.logger.error(f"Error updating song metadata: {str(e)}")
        
        return jsonify(data), status
    except Exception as e:
        current_app.logger.error(f"Error fetching lyrics: {str(e)}")
        return jsonify({'error': f'Failed to fetch lyrics: {str(e)}'}), 500
    

@lyrics_bp.route('/get', methods=['GET'])
def get_lyrics():
    required = ('track_name', 'artist_name', 'album_name', 'duration')
    missing = [p for p in required if not request.args.get(p)]
    if missing:
        return jsonify({'error': f"Missing parameters: {', '.join(missing)}"}), 400
    params = {p: request.args.get(p) for p in required}
    status, data = make_request('/api/get', params)
    return jsonify(data), status


@lyrics_bp.route('/get-cached', methods=['GET'])
def get_cached_lyrics():
    required = ('track_name', 'artist_name', 'album_name', 'duration')
    missing = [p for p in required if not request.args.get(p)]
    if missing:
        return jsonify({'error': f"Missing parameters: {', '.join(missing)}"}), 400
    params = {p: request.args.get(p) for p in required}
    status, data = make_request('/api/get-cached', params)
    return jsonify(data), status
