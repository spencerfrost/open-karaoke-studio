# backend/app/services/interfaces/metadata_service.py
"""
Metadata Service Interface for dependency injection and testing
"""

from typing import Protocol, List, Dict, Optional, Any
from pathlib import Path


class MetadataServiceInterface(Protocol):
    """Interface for Metadata Service to enable dependency injection and testing"""
    
    def search_metadata(
        self, 
        artist: str = '', 
        title: str = '', 
        album: str = '', 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for song metadata by artist and/or title.
        
        Args:
            artist (str): Artist name
            title (str): Song title  
            album (str): Album name (optional)
            limit (int): Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of formatted metadata results
        """
        ...
    
    def enhance_metadata(
        self, 
        metadata: Dict[str, Any], 
        song_dir: Path
    ) -> Dict[str, Any]:
        """
        Enhance existing song metadata with additional information.
        
        Args:
            metadata (Dict[str, Any]): Existing metadata
            song_dir (Path): Directory path for the song
            
        Returns:
            Dict[str, Any]: Enhanced metadata
        """
        ...
    
    def get_cover_art(
        self, 
        release_id: str, 
        song_dir: Path
    ) -> Optional[str]:
        """
        Download and store cover art for a release.
        
        Args:
            release_id (str): Release ID from metadata provider
            song_dir (Path): Directory to store cover art
            
        Returns:
            Optional[str]: Path to downloaded cover art or None
        """
        ...
