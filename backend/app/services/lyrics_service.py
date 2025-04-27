# backend/app/services/lyrics_service.py
import requests
from typing import Tuple, Dict, Optional, Any
from flask import current_app

# Recommended User-Agent header
USER_AGENT = "OpenKaraokeStudio/0.1 (https://github.com/spencerfrost/open-karaoke)"


def make_request(path: str, params: dict) -> Tuple[int, Dict[str, Any]]:
    """
    Helper function to call LRCLIB API and return status code + JSON.
    
    Args:
        path (str): API endpoint path
        params (dict): Query parameters to include in the request
        
    Returns:
        Tuple[int, Dict[str, Any]]: (HTTP status code, JSON response data)
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


def fetch_lyrics(title: str, artist: str, duration: float = None) -> Optional[Dict[str, Any]]:
    """
    Fetch lyrics for a song that can be called from other modules.
    
    Args:
        title (str): Song title
        artist (str): Artist name
        duration (float, optional): Song duration in seconds
        
    Returns:
        Optional[Dict[str, Any]]: Lyrics data or None if not found
    """
    params = {
        'track_name': title,
        'artist_name': artist
    }
    
    if duration is not None:
        params['duration'] = str(duration)
    
    try:
        status, data = make_request('/api/get', params)
        if status == 200 and not data.get('error'):
            return data
        return None
    except Exception as e:
        current_app.logger.error(f"Error fetching lyrics: {str(e)}")
        return None


def update_song_with_lyrics(song_id: str, lyrics_data: Dict[str, Any]) -> bool:
    """
    Update a song's metadata and database records with lyrics data.
    
    Args:
        song_id (str): The UUID of the song
        lyrics_data (Dict[str, Any]): The lyrics data from LRCLIB
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    if not lyrics_data:
        return False
        
    try:
        # Import here to avoid circular imports
        from ..services.file_management import read_song_metadata, write_song_metadata
        
        # Read current metadata
        metadata = read_song_metadata(song_id)
        if not metadata:
            current_app.logger.error(f"Could not read metadata for song {song_id}")
            return False
            
        # Extract lyrics data
        plain_lyrics = lyrics_data.get('plainLyrics')
        synced_lyrics = lyrics_data.get('syncedLyrics')
        
        # Update metadata with lyrics
        metadata.lyrics = plain_lyrics
        metadata.syncedLyrics = synced_lyrics
        
        # Write updated metadata (this should also update the database via file_management.py)
        write_song_metadata(song_id, metadata)
        
        # Try to update database directly for redundancy - use proper imports
        try:
            from ..db.models import DbSong
            from ..db.database import get_db_session
            
            # Query the song in the database
            with get_db_session() as db:
                db_song = db.query(DbSong).filter(DbSong.id == song_id).first()
                if db_song:
                    db_song.lyrics = plain_lyrics
                    db_song.synced_lyrics = synced_lyrics
                    db.commit()
                    current_app.logger.info(f"Successfully updated lyrics in database for song {song_id}")
                else:
                    current_app.logger.warning(f"Song {song_id} not found in database for lyrics update")
                    
        except ImportError as ie:
            current_app.logger.info(f"Database module not available for direct lyrics update: {str(ie)}")
        except Exception as e:
            current_app.logger.error(f"Error updating lyrics in database: {str(e)}")
            # Continue anyway since the metadata file was updated
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Error updating song with lyrics: {str(e)}")
        return False
