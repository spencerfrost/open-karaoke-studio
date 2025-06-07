# backend/app/services/metadata_service.py
"""
Service layer for music metadata operations.
This provides a clean abstraction for metadata search and formatting,
currently using iTunes as the backend but designed to be extensible.
"""

from typing import Dict, Any, List, Optional
from flask import current_app
from .itunes_service import search_itunes, enhance_metadata_with_itunes, get_itunes_cover_art
from .interfaces.metadata_service import MetadataServiceInterface
from pathlib import Path


class MetadataService(MetadataServiceInterface):
    """Service for music metadata operations using iTunes as the backend."""
    
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
        try:
            current_app.logger.info(f"MetadataService: Searching for artist='{artist}', title='{title}', album='{album}', limit={limit}")
            
            # Use iTunes service as the backend
            results = search_itunes(artist, title, album, limit)
            
            current_app.logger.info(f"MetadataService: Found {len(results)} results")
            return results
            
        except Exception as e:
            current_app.logger.error(f"MetadataService search error: {e}")
            raise
    
    def format_metadata_response(self, results: List[Dict[str, Any]], search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format metadata search results into a consistent API response.
        
        Args:
            results: List of metadata results
            search_params: Original search parameters
            
        Returns:
            Dict[str, Any]: Formatted response data
        """
        # Map iTunes results to a consistent metadata format
        metadata_results = []
        
        for result in results:
            metadata_result = {
                "metadataId": str(result.get("id", "")),
                "title": result.get("title", ""),
                "artist": result.get("artist", ""),
                "album": result.get("album", ""),
                "releaseDate": result.get("releaseDateFormatted", ""),
                "releaseYear": result.get("releaseYear"),
                "genre": result.get("genre", ""),
                "duration": result.get("durationSeconds"),
                "trackNumber": result.get("trackNumber"),
                "previewUrl": result.get("previewUrl", ""),
                "artworkUrl": result.get("artworkUrl100", ""),
                "isStreamable": result.get("isStreamable", False),
                
                # Additional iTunes-specific fields that might be useful
                "artistId": result.get("artistId"),
                "albumId": result.get("albumId"),
                "discNumber": result.get("discNumber"),
                "explicit": result.get("trackExplicitness") != "notExplicit",
                "country": result.get("country", ""),
                "price": result.get("price"),
            }
            
            metadata_results.append(metadata_result)
        
        return {
            "results": metadata_results,
            "search": search_params,
            "count": len(metadata_results),
            "success": True
        }
    
    def enhance_song_metadata(self, metadata: Dict[str, Any], song_dir: Path) -> Dict[str, Any]:
        """
        Enhance existing song metadata with additional information.
        
        Args:
            metadata: Existing song metadata
            song_dir: Song directory for cover art download
            
        Returns:
            Dict[str, Any]: Enhanced metadata
        """
        try:
            current_app.logger.info(f"MetadataService: Enhancing metadata for '{metadata.get('title', 'Unknown')}' by '{metadata.get('artist', 'Unknown')}'")
            
            # Use iTunes service to enhance metadata
            enhanced = enhance_metadata_with_itunes(metadata, song_dir)
            
            current_app.logger.info("MetadataService: Metadata enhancement completed")
            return enhanced
            
        except Exception as e:
            current_app.logger.error(f"MetadataService enhancement error: {e}")
            return metadata
    
    def download_cover_art(self, track_data: Dict[str, Any], song_dir: Path) -> Optional[str]:
        """
        Download cover art for a track.
        
        Args:
            track_data: Track metadata containing artwork URLs
            song_dir: Directory to save cover art
            
        Returns:
            str: Relative path to downloaded cover art or None
        """
        try:
            current_app.logger.info(f"MetadataService: Downloading cover art for track ID {track_data.get('id', 'Unknown')}")
            
            # Use iTunes service to download cover art
            cover_path = get_itunes_cover_art(track_data, song_dir)
            
            if cover_path:
                current_app.logger.info(f"MetadataService: Cover art downloaded to {cover_path}")
            else:
                current_app.logger.warning("MetadataService: No cover art available or download failed")
                
            return cover_path
            
        except Exception as e:
            current_app.logger.error(f"MetadataService cover art download error: {e}")
            return None


# Convenience function for backwards compatibility and direct usage
def search_metadata(artist: str, title: str, album: str = '', limit: int = 5) -> List[Dict[str, Any]]:
    """
    Convenience function for metadata search.
    
    Args:
        artist (str): Artist name
        title (str): Song title  
        album (str): Album name (optional)
        limit (int): Maximum number of results to return
        
    Returns:
        List[Dict[str, Any]]: List of song metadata
    """
    service = MetadataService()
    return service.search_metadata(artist, title, album, limit)
