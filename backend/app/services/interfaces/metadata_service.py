# backend/app/services/interfaces/metadata_service.py
"""
Metadata Service Interface for dependency injection and testing
"""

from typing import Protocol, List, Dict, Any, Optional, runtime_checkable
from pathlib import Path


@runtime_checkable
class MetadataServiceInterface(Protocol):
    """Interface for Metadata Service to enable dependency injection and testing"""
    
    def search_metadata(self, artist: str, title: str, album: str = '', limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for song metadata.
        
        Args:
            artist (str): Artist name
            title (str): Song title
            album (str): Album name (optional)
            limit (int): Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of song metadata
        """
        ...
    
    def format_metadata_response(self, results: List[Dict[str, Any]], search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format metadata search results into a consistent API response.
        
        Args:
            results: List of metadata results
            search_params: Original search parameters
            
        Returns:
            Dict[str, Any]: Formatted response data
        """
        ...
    
    def enhance_song_metadata(self, metadata: Dict[str, Any], song_dir: Path) -> Dict[str, Any]:
        """
        Enhance existing song metadata with additional information.
        
        Args:
            metadata: Existing song metadata
            song_dir: Song directory for cover art download
            
        Returns:
            Dict[str, Any]: Enhanced metadata
        """
        ...
    
    def download_cover_art(self, track_data: Dict[str, Any], song_dir: Path) -> Optional[str]:
        """
        Download cover art for a track.
        
        Args:
            track_data: Track metadata containing artwork URLs
            song_dir: Directory to save cover art
            
        Returns:
            str: Relative path to downloaded cover art or None
        """
        ...
