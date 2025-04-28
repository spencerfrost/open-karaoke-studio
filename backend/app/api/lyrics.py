import logging
from flask import Blueprint, request, jsonify, current_app

# Import the service functions
from ..services.lyrics_service import make_request
from ..db.database import create_or_update_song

lyrics_bp = Blueprint('lyrics', __name__, url_prefix='/api/lyrics')

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


@lyrics_bp.route('/search', methods=['POST'])
def search_lyrics():
    """ Search for lyrics via POST with body containing artist and title. """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    if 'title' not in data or 'artist' not in data:
        return jsonify({'error': 'Missing title or artist'}), 400
    title = data.get('title', '')
    artist = data.get('artist', '')
    album = data.get('album', '')
    song_id = data.get('song_id')
    
    if not title or not artist:
        return jsonify({'error': 'Both title and artist are required'}), 400
    
    params = {
        'track_name': title,
        'artist_name': artist
    }
    
    if album:
        params['album_name'] = album
    
    try:
        status, data = make_request('/api/search', params)
        
        if song_id and status == 200 and data:
            try:
                create_or_update_song(song_id, data)
                data['metadataUpdated'] = True
            except Exception as e:
                current_app.logger.error(f"Error updating song metadata: {str(e)}")
        
        return jsonify(data), status
    except Exception as e:
        current_app.logger.error(f"Error fetching lyrics: {str(e)}")
        return jsonify({'error': f'Failed to fetch lyrics: {str(e)}'}), 500
