from flask import Blueprint, request, jsonify, current_app

# Import the service functions
from ..services.lyrics_service import make_request, fetch_lyrics, update_song_with_lyrics

# Blueprint for LRCLIB-proxy endpoints
lyrics_bp = Blueprint('lyrics', __name__, url_prefix='/api/lyrics')


@lyrics_bp.route('/search', methods=['GET'])
def search_lyrics():
    # Proxy GET /api/search
    q = request.args.get('q')
    track = request.args.get('track_name')
    if not (q or track):
        return jsonify({'error': "Missing 'q' or 'track_name' parameter"}), 400
    params = {}
    if q:
        params['q'] = q
    if track:
        params['track_name'] = track
    for opt in ('artist_name', 'album_name'):
        val = request.args.get(opt)
        if val:
            params[opt] = val
    status, data = make_request('/api/search', params)
    return jsonify(data), status


@lyrics_bp.route('/get', methods=['GET'])
def get_lyrics():
    # Proxy GET /api/get
    required = ('track_name', 'artist_name', 'album_name', 'duration')
    missing = [p for p in required if not request.args.get(p)]
    if missing:
        return jsonify({'error': f"Missing parameters: {', '.join(missing)}"}), 400
    params = {p: request.args.get(p) for p in required}
    status, data = make_request('/api/get', params)
    return jsonify(data), status


@lyrics_bp.route('/get-cached', methods=['GET'])
def get_cached_lyrics():
    # Proxy GET /api/get-cached
    required = ('track_name', 'artist_name', 'album_name', 'duration')
    missing = [p for p in required if not request.args.get(p)]
    if missing:
        return jsonify({'error': f"Missing parameters: {', '.join(missing)}"}), 400
    params = {p: request.args.get(p) for p in required}
    status, data = make_request('/api/get-cached', params)
    return jsonify(data), status


@lyrics_bp.route('/search', methods=['POST'])
def search_lyrics_json():
    """
    Search for lyrics via POST with JSON body containing artist and title.
    This endpoint is more directly aligned with our frontend metadata dialog flow.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    title = data.get('title', '')
    artist = data.get('artist', '')
    album = data.get('album', '') # Optional album name for more precise matching
    duration = data.get('duration')  # Optional duration for more precise matching
    song_id = data.get('song_id')  # Optional song_id for direct metadata update
    
    if not title or not artist:
        return jsonify({'error': 'Both title and artist are required'}), 400
    
    # Prepare parameters for LRCLIB API
    params = {
        'track_name': title,
        'artist_name': artist
    }
    
    # Add duration if available
    if duration:
        params['duration'] = duration
    
    try:
        # Make the API call to LRCLIB
        status, data = make_request('/api/get', params)
        
        # If song_id is provided, save the lyrics to the song's metadata and database
        if song_id and status == 200 and data and not data.get('error'):
            success = update_song_with_lyrics(song_id, data)
            if success:
                data['metadataUpdated'] = True
        
        return jsonify(data), status
    except Exception as e:
        current_app.logger.error(f"Error fetching lyrics: {str(e)}")
        return jsonify({'error': f'Failed to fetch lyrics: {str(e)}'}), 500
