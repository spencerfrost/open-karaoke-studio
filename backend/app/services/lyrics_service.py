# backend/app/services/lyrics_service.py
import requests
from typing import Tuple, Dict, Optional, Any
from flask import current_app

USER_AGENT = "OpenKaraokeStudio/0.1 (https://github.com/spencerfrost/open-karaoke)"

def make_request(path: str, params: dict) -> Tuple[int, Dict[str, Any]]:
    """
    Helper function to call LRCLIB API
    
    Args:
        path (str): API endpoint path
        params (dict): Query parameters to include in the request
        
    Returns:
        Tuple[int, Dict[str, Any]]: HTTP status code and response data
    
        
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
            data = {'error': text}
        else:
            data = {'error': 'Invalid JSON from LRCLIB'}
    current_app.logger.info(f"LRCLIB response: {resp.status_code} {resp.text[:250]}")
    return status, data


def fetch_lyrics(title: str, artist: str, album: str = None) -> Optional[Dict[str, Any]]:
    """ Fetch lyrics for a song that can be called from other modules.
    
    Args:
        title (str): Song title
        artist (str): Artist name
        album (str, optional): Album name
        
    Returns:
        Optional[Dict[str, Any]]: Lyrics data or None if not found
    """
    params = {
        'track_name': title,
        'artist_name': artist
    }
    
    if album is not None:
        params['album_name'] = str(album)
    
    try:
        status, data = make_request('/api/search', params)
        if status == 200:
            return data
        return None
    except Exception as e:
        current_app.logger.error(f"Error fetching lyrics: {str(e)}")
        return None
