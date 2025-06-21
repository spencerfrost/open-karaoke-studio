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
        logger.debug(
            f"Searching iTunes for: '{title}' by '{artist}' (album: '{album}') - specific search"
        )
        results = search_itunes(artist, title, album, limit=1)

        if results:
            best_match = results[0]
            logger.debug(
                f"Found specific iTunes match for song {song.id}: {best_match.get('trackName')} by {best_match.get('artistName')}"
            )
            return best_match

    # Strategy 2: Search with just artist + title (broader search)
    logger.debug(f"Searching iTunes for: '{title}' by '{artist}' - broad search")
    results = search_itunes(artist, title, limit=5)

    if results:
        # For broader search, take the first result but log it
        best_match = results[0]
        logger.debug(
            f"Found broad iTunes match for song {song.id}: {best_match.get('trackName')} by {best_match.get('artistName')}"
        )
        return best_match

    # Strategy 3: Search with just title if artist search fails
    if artist:
        logger.debug(f"Searching iTunes for: '{title}' - title-only search")
        results = search_itunes("", title, limit=3)

        if results:
            best_match = results[0]
            logger.debug(
                f"Found title-only iTunes match for song {song.id}: {best_match.get('trackName')} by {best_match.get('artistName')}"
            )
            return best_match

    logger.info(f"No iTunes match found for song {song.id}: '{title}' by '{artist}'")
    return None


def enhance_song_metadata(
    song: DbSong, itunes_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    DEPRECATED: This function is misleading and redundant.

    What it ACTUALLY does:
    1. Converts DbSong to dict
    2. Calls enhance_metadata_with_itunes() which IGNORES the passed itunes_data
       and searches iTunes API again (wasteful!)
    3. Returns enhanced metadata dict

    Args:
        song: The song database object
        itunes_data: iTunes metadata dictionary (IGNORED by this function!)

    Returns:
        Enhanced metadata dictionary or None if failed

    TODO: Replace usage with direct call to enhance_metadata_with_itunes()
    """
    try:
        logger.warning(
            f"enhance_song_metadata() for song {song.id} is deprecated - makes redundant iTunes API call"
        )

        # Convert DbSong to metadata dictionary using to_dict() method
        metadata_dict = song.to_dict()

        # Convert camelCase back to snake_case for legacy iTunes function compatibility
        legacy_metadata_dict = {
            "title": metadata_dict["title"],
            "artist": metadata_dict["artist"],
            "album": metadata_dict["album"],
            "duration": metadata_dict["duration"],
            "genre": metadata_dict["genre"],
            "releaseDate": metadata_dict["releaseDate"],
            "year": metadata_dict["year"],
            "itunes_track_id": song.itunes_track_id,  # Direct access for fields not in to_dict()
            "cover_art_path": song.cover_art_path,
            "date_added": song.date_added,
            "source": metadata_dict["source"],
            "source_url": metadata_dict["sourceUrl"],
            "video_id": metadata_dict["videoId"],
            "favorite": metadata_dict["favorite"],
        }

        # We need the song directory path for cover art processing
        from pathlib import Path

        song_dir = Path(f"/home/spencer/code/open-karaoke-studio/karaoke_library/{song.id}")

        # NOTE: This ignores the passed itunes_data and searches iTunes again!
        enhanced_metadata = enhance_metadata_with_itunes(legacy_metadata_dict, song_dir)

        if enhanced_metadata:
            logger.debug(f"Enhanced metadata created for song {song.id}")
            return enhanced_metadata
        else:
            logger.warning(f"Failed to create enhanced metadata for song {song.id}")
            return None

    except Exception as e:
        logger.error(f"Error creating enhanced metadata for song {song.id}: {e}")
        return None


def enhance_song_with_itunes_data(
    song: DbSong, itunes_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Efficiently enhance song metadata using already-fetched iTunes data.

    This function ACTUALLY uses the iTunes data you pass in, unlike enhance_song_metadata()
    which ignores it and makes redundant API calls.

    Args:
        song: The song database object
        itunes_data: Already-fetched iTunes metadata dictionary

    Returns:
        Enhanced metadata dictionary ready for database update
    """
    try:
        # Start with current song data
        enhanced = {
            "title": song.title or itunes_data.get("trackName"),
            "artist": song.artist or itunes_data.get("artistName"),
            "album": song.album or itunes_data.get("collectionName"),
            "genre": song.genre or itunes_data.get("primaryGenreName"),
            "duration": song.duration
            or itunes_data.get("trackTimeMillis", 0) // 1000,  # Convert ms to seconds
        }

        # Add iTunes-specific fields
        enhanced.update(
            {
                "itunes_track_id": itunes_data.get("trackId"),
                "itunes_artist_id": itunes_data.get("artistId"),
                "itunes_collection_id": itunes_data.get("collectionId"),
                "track_time_millis": itunes_data.get("trackTimeMillis"),
                "itunes_explicit": itunes_data.get("trackExplicitness") == "explicit",
                "itunes_preview_url": itunes_data.get("previewUrl"),
            }
        )

        # Add release information
        if "releaseDate" in itunes_data:
            enhanced["release_date"] = itunes_data["releaseDate"]
            # Extract year from release date
            try:
                release_year = int(itunes_data["releaseDate"][:4])
                enhanced["year"] = release_year
            except (ValueError, TypeError):
                pass

        # Add artwork URLs as JSON
        artwork_urls = []
        for size in [30, 60, 100, 600]:  # Include 600x600 for high-res
            url_key = f"artworkUrl{size}"
            if url_key in itunes_data:
                artwork_urls.append(itunes_data[url_key])

        if artwork_urls:
            import json

            enhanced["itunes_artwork_urls"] = json.dumps(artwork_urls)

        # Store raw iTunes metadata as JSON
        import json

        enhanced["itunes_raw_metadata"] = json.dumps(itunes_data)

        logger.debug(f"Efficiently enhanced song {song.id} metadata using iTunes data")
        return enhanced

    except Exception as e:
        logger.error(f"Error enhancing song {song.id} with iTunes data: {e}")
        return {}


def validate_itunes_match(
    song: DbSong, itunes_data: Dict[str, Any]
) -> "tuple[bool, str]":
    """
    Validate if an iTunes search result is a good match for the song.

    Args:
        song: The song database object
        itunes_data: iTunes metadata dictionary

    Returns:
        Tuple of (is_good_match, reason)
    """
    itunes_title = itunes_data.get("trackName", "").lower()
    itunes_artist = itunes_data.get("artistName", "").lower()

    song_title = song.title.lower() if song.title else ""
    song_artist = (
        song.artist.lower() if song.artist and song.artist != "Unknown Artist" else ""
    )

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
            if any(
                word in itunes_artist for word in song_artist.split() if len(word) > 2
            ):
                artist_match = True

    # Determine match quality
    if title_match and artist_match:
        return True, "Good match (title and artist)"
    elif title_match and not song_artist:
        return True, "Good match (title, no original artist to compare)"
    elif title_match:
        return (
            True,
            f"Partial match (title matches, artist differs: '{song_artist}' vs '{itunes_artist}')",
        )
    elif artist_match:
        return (
            False,
            f"Weak match (artist matches but title differs: '{song_title}' vs '{itunes_title}')",
        )
    else:
        return (
            False,
            f"Poor match (title: '{song_title}' vs '{itunes_title}', artist: '{song_artist}' vs '{itunes_artist}')",
        )


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
