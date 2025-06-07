# backend/app/services/lyrics_service.py
import logging
import requests
import os
from pathlib import Path
from typing import Tuple, Dict, Optional, Any, List
from flask import current_app
from .interfaces.lyrics_service import LyricsServiceInterface
from .file_service import FileService
from ..exceptions import ServiceError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)

USER_AGENT = "OpenKaraokeStudio/0.1 (https://github.com/spencerfrost/open-karaoke)"


class LyricsService(LyricsServiceInterface):
    """Handle lyrics operations for songs"""
    
    def __init__(self, file_service: Optional[FileService] = None):
        """Initialize the lyrics service
        
        Args:
            file_service: Optional FileService instance for file operations
        """
        self.file_service = file_service or FileService()
        self.base_url = "https://lrclib.net"
        self.headers = {"User-Agent": USER_AGENT}
        
    def _make_request(self, path: str, params: dict) -> Tuple[int, Any]:
        """
        Helper function to call LRCLIB API

        Args:
            path (str): API endpoint path
            params (dict): Query parameters to include in the request

        Returns:
            Tuple[int, Any]: HTTP status code and response data as returned from LRCLIB
        """
        url = f"{self.base_url}{path}"
        logger.info(f"LRCLIB request: {url} params={params}")
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            status = resp.status_code

            try:
                data = resp.json()
            except ValueError:
                text = resp.text.strip()
                if status >= 400:
                    data = {"error": text}
                else:
                    data = {"error": "Invalid JSON from LRCLIB"}

            return status, data
            
        except requests.RequestException as e:
            logger.error(f"Failed to make request to LRCLIB: {e}")
            raise ServiceError(f"Failed to connect to lyrics service: {e}")
    
    def search_lyrics(self, query: str) -> List[Dict[str, Any]]:
        """Search for lyrics using a general query string
        
        Args:
            query: Search query string
            
        Returns:
            List of lyrics records matching the query
        """
        try:
            search_params = {"q": query}
            status, results = self._make_request("/api/search", search_params)
            
            if status == 200 and isinstance(results, list):
                logger.info(f"Found {len(results)} lyrics results for query: {query}")
                return results
            
            logger.info(f"No lyrics found for query: {query}")
            return []
            
        except ServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error searching lyrics: {e}")
            raise ServiceError(f"Failed to search lyrics: {e}")
    
    def search_lyrics_structured(self, params: Dict[str, str]) -> List[Dict[str, Any]]:
        """Search for lyrics using structured parameters (track_name, artist_name, album_name)
        
        Args:
            params: Dictionary containing track_name, artist_name, and optionally album_name
            
        Returns:
            List of lyrics records matching the search parameters
        """
        try:
            # Use the LRCLIB search endpoint with structured parameters
            status, results = self._make_request("/api/search", params)
            
            if status == 200 and isinstance(results, list):
                logger.info(f"Found {len(results)} structured lyrics results for params: {params}")
                return results
            
            logger.info(f"No structured lyrics found for params: {params}")
            return []
            
        except ServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in structured lyrics search: {e}")
            raise ServiceError(f"Failed to search lyrics with structured params: {e}")
    
    def get_lyrics(self, song_id: str) -> Optional[str]:
        """Get lyrics for a song from storage
        
        Args:
            song_id: Unique identifier for the song
            
        Returns:
            Lyrics text if found, None otherwise
        """
        try:
            lyrics_path = Path(self.get_lyrics_file_path(song_id))
            
            if lyrics_path.exists():
                with open(lyrics_path, 'r', encoding='utf-8') as f:
                    lyrics = f.read().strip()
                    if lyrics:
                        logger.info(f"Retrieved lyrics from file for song {song_id}")
                        return lyrics
            
            logger.info(f"No lyrics file found for song {song_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to read lyrics for song {song_id}: {e}")
            raise ServiceError(f"Failed to read lyrics: {e}")
    
    def save_lyrics(self, song_id: str, lyrics: str) -> bool:
        """Save lyrics for a song to storage
        
        Args:
            song_id: Unique identifier for the song
            lyrics: Lyrics text to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.validate_lyrics(lyrics):
                raise ValidationError("Invalid lyrics format")
            
            lyrics_path = Path(self.get_lyrics_file_path(song_id))
            lyrics_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(lyrics_path, 'w', encoding='utf-8') as f:
                f.write(lyrics)
            
            logger.info(f"Saved lyrics to file for song {song_id}")
            return True
            
        except (ValidationError, ServiceError):
            raise
        except Exception as e:
            logger.error(f"Failed to save lyrics for song {song_id}: {e}")
            raise ServiceError(f"Failed to save lyrics: {e}")
    
    def validate_lyrics(self, lyrics: str) -> bool:
        """Validate lyrics format and completeness
        
        Args:
            lyrics: Lyrics text to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not lyrics or not isinstance(lyrics, str):
            return False
        
        # Basic validation rules
        lyrics = lyrics.strip()
        
        # Must have some content
        if len(lyrics) < 3:
            return False
        
        # Must not be just whitespace or newlines
        if not lyrics.replace('\n', '').replace(' ', ''):
            return False
        
        # Could add more validation rules here:
        # - Check for profanity
        # - Validate LRC format if it's synced lyrics
        # - Check minimum word count
        
        return True
    
    def lyrics_file_exists(self, song_id: str) -> bool:
        """Check if lyrics file exists for a song
        
        Args:
            song_id: Unique identifier for the song
            
        Returns:
            True if lyrics file exists, False otherwise
        """
        try:
            lyrics_path = Path(self.get_lyrics_file_path(song_id))
            return lyrics_path.exists() and lyrics_path.is_file()
        except Exception as e:
            logger.error(f"Error checking lyrics file for song {song_id}: {e}")
            return False
    
    def get_lyrics_file_path(self, song_id: str) -> str:
        """Get path to lyrics file for a song
        
        Args:
            song_id: Unique identifier for the song
            
        Returns:
            Path to the lyrics file
        """
        song_dir = self.file_service.get_song_directory(song_id)
        return str(song_dir / "lyrics.txt")
    
    def create_default_lyrics(self, song_id: str) -> str:
        """Create default lyrics for a song
        
        Args:
            song_id: Unique identifier for the song
            
        Returns:
            Default lyrics text
        """
        return "[Instrumental]"


# Legacy function for backward compatibility
def make_request(path: str, params: dict) -> Tuple[int, Any]:
    """
    Legacy helper function to call LRCLIB API for backward compatibility
    
    Args:
        path (str): API endpoint path
        params (dict): Query parameters to include in the request

    Returns:
        Tuple[int, Any]: HTTP status code and response data as returned from LRCLIB
    """
    service = LyricsService()
    return service._make_request(path, params)

