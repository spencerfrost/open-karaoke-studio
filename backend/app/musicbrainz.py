# backend/app/musicbrainz.py
import musicbrainzngs
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from .file_management import download_image, get_cover_art_path

# Configure MusicBrainz API client
musicbrainzngs.set_useragent(
    "OpenKaraokeStudio", 
    "1.0", 
    "s.s.frost@gmail.com"  # Replace with actual contact
)

def search_musicbrainz(artist: str, title: str) -> Optional[Dict[str, Any]]:
    """
    Search MusicBrainz for recording metadata.
    
    Args:
        artist (str): Artist name
        title (str): Song title
        
    Returns:
        Optional[Dict[str, Any]]: Recording metadata or None if not found
    """
    try:
        logging.info(f"Searching MusicBrainz for: {artist} - {title}")
        
        # Search for recordings matching artist and title
        result = musicbrainzngs.search_recordings(
            artist=artist,
            recording=title,
            limit=5
        )
        
        if result and 'recording-list' in result and result['recording-list']:
            # Return the top match
            return {
                "mbid": result['recording-list'][0].get('id'),
                "title": result['recording-list'][0].get('title'),
                "length": result['recording-list'][0].get('length'),
                "artist": result['recording-list'][0].get('artist-credit', [{}])[0].get('artist', {}).get('name'),
                "artist_id": result['recording-list'][0].get('artist-credit', [{}])[0].get('artist', {}).get('id'),
                "release": _extract_release_info(result['recording-list'][0])
            }
            
    except Exception as e:
        logging.error(f"MusicBrainz search error: {e}")
    
    return None

def _extract_release_info(recording: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract release information from a recording."""
    if 'release-list' not in recording or not recording['release-list']:
        return None
    
    # Get the first release (typically the most relevant)
    release = recording['release-list'][0]
    
    return {
        "id": release.get('id'),
        "title": release.get('title'),
        "date": release.get('date')
    }

def get_cover_art(release_id: str, song_dir: Path) -> Optional[str]:
    """
    Download cover art for a release from MusicBrainz Cover Art Archive.
    
    Args:
        release_id (str): MusicBrainz release ID
        song_dir (Path): Directory to save the cover art
        
    Returns:
        Optional[str]: Relative path to the cover art or None if not available
    """
    if not release_id:
        return None
    
    try:
        # Get cover art from Cover Art Archive
        cover_art_list = musicbrainzngs.get_image_list(release_id)
        
        if cover_art_list and 'images' in cover_art_list and cover_art_list['images']:
            # Try to get front image first
            front_images = [img for img in cover_art_list['images'] if img.get('front', False)]
            
            if front_images:
                image_url = front_images[0]['image']
            else:
                # Fall back to first image
                image_url = cover_art_list['images'][0]['image']
            
            # Download the cover art
            cover_path = get_cover_art_path(song_dir)
            if download_image(image_url, cover_path):
                # Return the relative path from the library root
                from . import config
                return str(cover_path.relative_to(config.BASE_LIBRARY_DIR))
                
    except Exception as e:
        logging.error(f"Cover art lookup error: {e}")
    
    return None

def enhance_metadata_with_musicbrainz(metadata: Dict[str, Any], song_dir: Path) -> Dict[str, Any]:
    """
    Enhance song metadata with MusicBrainz data.
    
    Args:
        metadata (Dict[str, Any]): Existing metadata
        song_dir (Path): Song directory for storing cover art
        
    Returns:
        Dict[str, Any]: Enhanced metadata
    """
    try:
        # Search MusicBrainz with the existing artist and title
        artist = metadata.get('artist', '')
        title = metadata.get('title', '')
        
        if not artist or artist == "Unknown Artist" or not title:
            return metadata  # Not enough information to search
            
        mb_data = search_musicbrainz(artist, title)
        
        if not mb_data:
            return metadata  # No results found
            
        # Try to get cover art
        cover_art_path = None
        if mb_data.get('release', {}) and mb_data['release'].get('id'):
            cover_art_path = get_cover_art(mb_data['release']['id'], song_dir)
            
        # Update metadata with MusicBrainz data
        enhanced = metadata.copy()
        enhanced.update({
            "mbid": mb_data.get("mbid"),
            # Only update title/artist if MusicBrainz has better data
            "title": mb_data.get("title") if mb_data.get("title") else metadata.get("title"),
            "artist": mb_data.get("artist") if mb_data.get("artist") else metadata.get("artist"),
            "artistId": mb_data.get("artist_id"),
            "releaseTitle": mb_data.get("release", {}).get("title"),
            "releaseId": mb_data.get("release", {}).get("id"),
            "releaseDate": mb_data.get("release", {}).get("date"),
        })
        
        # Add cover art if found
        if cover_art_path:
            enhanced["coverArt"] = cover_art_path
            
        return enhanced
        
    except Exception as e:
        logging.error(f"Error enhancing metadata with MusicBrainz: {e}")
        return metadata  # Return original metadata on error
