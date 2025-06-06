# backend/app/services/metadata_service.py
"""
Metadata Service implementation using MusicBrainz as the primary provider
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

from .interfaces.metadata_service import MetadataServiceInterface
from .musicbrainz_service import (
    search_musicbrainz, 
    enhance_metadata_with_musicbrainz,
    get_cover_art
)


class MusicBrainzMetadataService:
    """Metadata service implementation using MusicBrainz as the provider"""
    
    def search_metadata(
        self, 
        artist: str = '', 
        title: str = '', 
        album: str = '', 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for song metadata and format results for frontend consumption.
        
        Args:
            artist (str): Artist name
            title (str): Song title
            album (str): Album name (optional)
            limit (int): Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of formatted metadata results
        """
        try:
            # Validate input
            if not title and not artist:
                raise ValueError("At least one search term (title or artist) is required")
            
            # Perform MusicBrainz search
            raw_results = search_musicbrainz(artist, title, album, limit)
            
            if not raw_results:
                return []
            
            # Format results for frontend
            formatted_results = []
            for result in raw_results:
                formatted_result = self._format_search_result(result)
                formatted_results.append(formatted_result)
                
            return formatted_results
            
        except Exception as e:
            logging.error(f"Error during metadata search: {e}", exc_info=True)
            raise
    
    def enhance_metadata(
        self, 
        metadata: Dict[str, Any], 
        song_dir: Path
    ) -> Dict[str, Any]:
        """
        Enhance existing song metadata with MusicBrainz data.
        
        Args:
            metadata (Dict[str, Any]): Existing metadata
            song_dir (Path): Directory path for the song
            
        Returns:
            Dict[str, Any]: Enhanced metadata
        """
        try:
            return enhance_metadata_with_musicbrainz(metadata, song_dir)
        except Exception as e:
            logging.error(f"Error enhancing metadata: {e}", exc_info=True)
            return metadata
    
    def get_cover_art(
        self, 
        release_id: str, 
        song_dir: Path
    ) -> Optional[str]:
        """
        Download and store cover art for a release.
        
        Args:
            release_id (str): MusicBrainz release ID
            song_dir (Path): Directory to store cover art
            
        Returns:
            Optional[str]: Path to downloaded cover art or None
        """
        try:
            return get_cover_art(release_id, song_dir)
        except Exception as e:
            logging.error(f"Error getting cover art: {e}", exc_info=True)
            return None
    
    def _format_search_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a raw MusicBrainz search result for frontend consumption.
        
        Args:
            result (Dict[str, Any]): Raw result from MusicBrainz search
            
        Returns:
            Dict[str, Any]: Formatted result
        """
        return {
            "musicbrainzId": result.get("mbid"),
            "title": result.get("title"),
            "artist": result.get("artist"),
            "album": result.get("release", {}).get("title"),
            "year": result.get("release", {}).get("date"),
            "genre": result.get("genre"),
            "language": result.get("language"),
            "coverArt": result.get("coverArtUrl")
        }


# Service instance for dependency injection
metadata_service = MusicBrainzMetadataService()