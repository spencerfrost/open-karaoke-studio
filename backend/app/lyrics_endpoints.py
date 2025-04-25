# New file: lyrics_endpoints.py in backend/app
from flask import Blueprint, request, jsonify, current_app
import requests

# Blueprint for LRCLIB-proxy endpoints
lyrics_bp = Blueprint('lyrics', __name__, url_prefix='/api/lyrics')

# Recommended User-Agent header
USER_AGENT = "OpenKaraokeStudio/0.1 (https://github.com/spencerfrost/open-karaoke)"


def _make_request(path: str, params: dict) -> tuple[int, dict]:
    """
    Internal helper to call LRCLIB and return status code + JSON.
    """
    url = f"https://lrclib.net{path}"
    headers = {'User-Agent': USER_AGENT}
    current_app.logger.info(f"LRCLIB request: {url} params={params}")
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    status = resp.status_code
    try:
        data = resp.json()
    except ValueError:
        text = resp.text.strip()
        if status >= 400:
            # Pass through HTML or error text in JSON
            data = {'error': text}
        else:
            data = {'error': 'Invalid JSON from LRCLIB'}
    return status, data


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
    status, data = _make_request('/api/search', params)
    return jsonify(data), status


@lyrics_bp.route('/get', methods=['GET'])
def get_lyrics():
    # Proxy GET /api/get
    required = ('track_name', 'artist_name', 'album_name', 'duration')
    missing = [p for p in required if not request.args.get(p)]
    if missing:
        return jsonify({'error': f"Missing parameters: {', '.join(missing)}"}), 400
    params = {p: request.args.get(p) for p in required}
    status, data = _make_request('/api/get', params)
    return jsonify(data), status


@lyrics_bp.route('/get-cached', methods=['GET'])
def get_cached_lyrics():
    # Proxy GET /api/get-cached
    required = ('track_name', 'artist_name', 'album_name', 'duration')
    missing = [p for p in required if not request.args.get(p)]
    if missing:
        return jsonify({'error': f"Missing parameters: {', '.join(missing)}"}), 400
    params = {p: request.args.get(p) for p in required}
    status, data = _make_request('/api/get-cached', params)
    return jsonify(data), status


@lyrics_bp.route('/get/<int:lyrics_id>', methods=['GET'])
def get_lyrics_by_id(lyrics_id: int):
    # Proxy GET /api/get/{id}
    status, data = _make_request(f'/api/get/{lyrics_id}', {})
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
    song_id = data.get('song_id')  # Optional song_id for direct metadata update
    duration = data.get('duration')  # Optional duration for more precise matching
    
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
        status, data = _make_request('/api/get', params)
        
        # If song_id is provided, we could save the lyrics directly to the song's metadata
        # This would require accessing the file_management module and updating metadata
        if song_id and status == 200 and data and not data.get('error'):
            try:
                from .file_management import read_song_metadata, write_song_metadata
                from .models import SongMetadata
                
                # Read current metadata
                metadata = read_song_metadata(song_id)
                if metadata:
                    # Convert to dict for updating
                    metadata_dict = metadata.dict() if hasattr(metadata, 'dict') else metadata.model_dump()
                    
                    # Update with lyrics data
                    if 'syncedLyrics' in data:
                        metadata_dict['syncedLyrics'] = data['syncedLyrics']
                    if 'plainLyrics' in data:
                        metadata_dict['lyrics'] = data['plainLyrics']
                    
                    # Write updated metadata
                    write_song_metadata(song_id, SongMetadata(**metadata_dict))
                    
                    # Add flag indicating metadata was updated
                    data['metadataUpdated'] = True
            except Exception as e:
                current_app.logger.error(f"Error updating lyrics in metadata: {str(e)}")
                # Still return lyrics even if metadata update failed
                data['metadataUpdateError'] = str(e)
        
        return jsonify(data), status
    except Exception as e:
        current_app.logger.error(f"Error fetching lyrics: {str(e)}")
        return jsonify({'error': f'Failed to fetch lyrics: {str(e)}'}), 500


# Function to be called directly from other modules
def fetch_lyrics(title: str, artist: str, duration: float = None):
    """
    Fetch lyrics for a song that can be called from other modules.
    Returns lyrics data or None if not found.
    """
    params = {
        'track_name': title,
        'artist_name': artist
    }
    
    if duration:
        params['duration'] = str(duration)
    
    try:
        status, data = _make_request('/api/get', params)
        if status == 200 and not data.get('error'):
            return data
        return None
    except Exception as e:
        current_app.logger.error(f"Error fetching lyrics: {str(e)}")
        return None
