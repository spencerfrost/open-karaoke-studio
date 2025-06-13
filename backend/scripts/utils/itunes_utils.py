"""
iTunes Search Utilities for Metadata Update Script

This module handles iTunes Search API operations including:
- Searching for songs in iTunes
- Enhancing metadata with iTunes data
- Managing iTunes API rate limiting
"""

import logging
from typing import Optional, Dict, Any, List

from app.db.models import DbSong
from app.services.itunes_service import search_itunes, enhance_metadata_with_itunes

logger = logging.getLogger(__name__)


def search_itunes_for_song(song: DbSong) -> Optional[Dict[str, Any]]:
    """
    Search iTunes for metadata for a specific song using multiple strategies.
    
    Args:
        song: The song database object
        
    Returns:
        iTunes metadata dictionary or None if not found
    """
    # Use existing metadata for search
    artist = song.artist if song.artist != "Unknown Artist" else ""
    title = song.title
    album = song.album or ""

    if not artist and not title:
        logger.warning(f"Song {song.id} has no artist or title, skipping iTunes search")
        return None

    # Strategy 1: Search with artist + title + album (most specific)
    if album and album.strip():
        logger.debug(f"Searching iTunes for: '{title}' by '{artist}' (album: '{album}') - specific search")
        results = search_itunes(artist, title, album, limit=1)

        if results:
            best_match = results[0]
            logger.debug(f"Found specific iTunes match for song {song.id}: {best_match.get('trackName')} by {best_match.get('artistName')}")
            return best_match

    # Strategy 2: Search with just artist + title (broader search)
    logger.debug(f"Searching iTunes for: '{title}' by '{artist}' - broad search")
    results = search_itunes(artist, title, limit=5)

    if results:
        # For broader search, take the first result but log it
        best_match = results[0]
        logger.debug(f"Found broad iTunes match for song {song.id}: {best_match.get('trackName')} by {best_match.get('artistName')}")
        return best_match

    # Strategy 3: Search with just title if artist search fails
    if artist:
        logger.debug(f"Searching iTunes for: '{title}' - title-only search")
        results = search_itunes("", title, limit=3)

        if results:
            best_match = results[0]
            logger.debug(f"Found title-only iTunes match for song {song.id}: {best_match.get('trackName')} by {best_match.get('artistName')}")
            return best_match

    logger.info(f"No iTunes match found for song {song.id}: '{title}' by '{artist}'")
    return None


def enhance_song_metadata(song: DbSong, itunes_data: Dict[str, Any]) -> Optional[object]:
    """
    Create enhanced metadata from iTunes data.
    
    Args:
        song: The song database object
        itunes_data: iTunes metadata dictionary
        
    Returns:
        Enhanced SongMetadata object or None if failed
    """
    try:
        # Convert DbSong to metadata dictionary for enhance_metadata_with_itunes
        metadata_dict = {
            'title': song.title,
            'artist': song.artist,
            'album': song.album,
            'duration': song.duration,
            'genre': song.genre,
            'releaseDate': song.release_date,
            'year': song.year,
            'itunes_track_id': song.itunes_track_id,
            'cover_art_path': song.cover_art_path,
            'date_added': song.date_added,
            'source': song.source,
            'source_url': song.source_url,
            'video_id': song.video_id,
            'favorite': song.favorite,
        }
        
        # We need the song directory path for cover art processing
        from pathlib import Path
        song_dir = Path(f"/home/spencer/code/open-karaoke/karaoke_library/{song.id}")
        
        enhanced_metadata = enhance_metadata_with_itunes(metadata_dict, song_dir)
        
        if enhanced_metadata:
            logger.debug(f"Enhanced metadata created for song {song.id}")
            return enhanced_metadata
        else:
            logger.warning(f"Failed to create enhanced metadata for song {song.id}")
            return None
            
    except Exception as e:
        logger.error(f"Error creating enhanced metadata for song {song.id}: {e}")
        return None


def validate_itunes_match(song: DbSong, itunes_data: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate if an iTunes search result is a good match for the song.
    
    Args:
        song: The song database object
        itunes_data: iTunes metadata dictionary
        
    Returns:
        Tuple of (is_good_match, reason)
    """
    itunes_title = itunes_data.get('trackName', '').lower()
    itunes_artist = itunes_data.get('artistName', '').lower()
    
    song_title = song.title.lower() if song.title else ''
    song_artist = song.artist.lower() if song.artist and song.artist != "Unknown Artist" else ''
    
    # Check title similarity
    title_match = False
    if song_title and itunes_title:
        # Simple substring check - can be improved with fuzzy matching
        if song_title in itunes_title or itunes_title in song_title:
            title_match = True
        elif len(song_title) > 3 and len(itunes_title) > 3:
            # Check for partial match with longer titles
            words_song = set(song_title.split())
            words_itunes = set(itunes_title.split())
            common_words = words_song.intersection(words_itunes)
            if len(common_words) >= min(2, len(words_song) // 2):
                title_match = True
    
    # Check artist similarity
    artist_match = False
    if song_artist and itunes_artist:
        if song_artist in itunes_artist or itunes_artist in song_artist:
            artist_match = True
        elif len(song_artist) > 3 and len(itunes_artist) > 3:
            # Check for partial artist match
            if any(word in itunes_artist for word in song_artist.split() if len(word) > 2):
                artist_match = True
    
    # Determine match quality
    if title_match and artist_match:
        return True, "Good match (title and artist)"
    elif title_match and not song_artist:
        return True, "Good match (title, no original artist to compare)"
    elif title_match:
        return True, f"Partial match (title matches, artist differs: '{song_artist}' vs '{itunes_artist}')"
    elif artist_match:
        return False, f"Weak match (artist matches but title differs: '{song_title}' vs '{itunes_title}')"
    else:
        return False, f"Poor match (title: '{song_title}' vs '{itunes_title}', artist: '{song_artist}' vs '{itunes_artist}')"


def get_itunes_search_stats(songs: List[DbSong]) -> Dict[str, int]:
    """
    Get statistics about iTunes search coverage for a list of songs.
    
    Args:
        songs: List of song database objects
        
    Returns:
        Dictionary with search statistics
    """
    stats = {
        "total_songs": len(songs),
        "with_itunes_id": 0,
        "searchable": 0,  # Have artist and/or title for search
        "unsearchable": 0,  # Missing both artist and title
    }
    
    for song in songs:
        if song.itunes_track_id:
            stats["with_itunes_id"] += 1
        
        artist = song.artist if song.artist != "Unknown Artist" else ""
        title = song.title
        
        if artist or title:
            stats["searchable"] += 1
        else:
            stats["unsearchable"] += 1
    
    return stats
