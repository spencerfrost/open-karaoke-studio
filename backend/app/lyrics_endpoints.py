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
