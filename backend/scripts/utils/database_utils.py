"""
Database Utilities for Metadata Update Script

This module handles database operations including:
- Song retrieval and filtering
- Database updates
- Transaction management
"""

import logging
from typing import Any, Dict, List, Optional, Union

from app.db.database import get_db_session
from app.db.models import DbSong
from app.repositories.song_repository import SongRepository

logger = logging.getLogger(__name__)


def get_songs_to_process(
    limit: Optional[int] = None,
    resume_from: Optional[str] = None,
    skip_existing: bool = False,
) -> List[DbSong]:
    """
    Get list of songs to process from database with filtering options.

    Args:
        limit: Maximum number of songs to return
        resume_from: Song ID to resume processing from
        skip_existing: Skip songs that already have iTunes track IDs

    Returns:
        List of songs to process
    """
    logger.info("Fetching songs from database...")

    try:
        with get_db_session() as session:
            repo = SongRepository(session)
            all_songs = repo.fetch_all()
        logger.info(f"Found {len(all_songs)} total songs in database")

        # Filter based on resume_from if specified
        if resume_from:
            found_resume_point = False
            filtered_songs = []
            for song in all_songs:
                if song.id == resume_from:
                    found_resume_point = True
                if found_resume_point:
                    filtered_songs.append(song)

            if not found_resume_point:
                logger.warning(
                    f"Resume point '{resume_from}' not found, processing all songs"
                )
                filtered_songs = all_songs
            else:
                logger.info(
                    f"Resuming from song ID: {resume_from}, {len(filtered_songs)} songs to process"
                )

            all_songs = filtered_songs

        # Filter out songs that already have iTunes metadata if skip_existing is True
        if skip_existing:
            songs_to_process = [song for song in all_songs if not song.itunes_track_id]
            logger.info(
                f"Skipping {len(all_songs) - len(songs_to_process)} songs with existing iTunes metadata"
            )
        else:
            songs_to_process = all_songs

        # Apply limit if specified
        if limit:
            songs_to_process = songs_to_process[:limit]
            logger.info(f"Limited to first {limit} songs")

        logger.info(f"Will process {len(songs_to_process)} songs")
        return songs_to_process

    except Exception as e:
        logger.error(f"Error fetching songs from database: {e}")
        raise


def update_song_metadata(
    song: DbSong, metadata: Dict[str, Any], dry_run: bool = False
) -> bool:
    """
    Update song in database with enhanced metadata.

    Args:
        song: The song database object
        metadata: Enhanced metadata dictionary to update
        dry_run: If True, only simulate the update

    Returns:
        True if update was successful (or simulated)
    """
    try:
        if dry_run:
            logger.info(f"[DRY RUN] Would update song {song.id} with enhanced metadata")
            log_metadata_changes(song, metadata)
            return True
        else:
            logger.debug(f"Updating song {song.id} in database")
            from app.db.database import get_db_session
            from app.repositories.song_repository import SongRepository

            with get_db_session() as session:
                repo = SongRepository(session)
                updated_song = repo.update(song.id, **metadata)
                if updated_song:
                    log_metadata_changes(song, metadata)
                    return True
                else:
                    logger.error(f"Failed to update song {song.id} in database")
                    return False
    except Exception as e:
        logger.error(f"Error updating song {song.id} in database: {e}")
        return False


def log_metadata_changes(original_song: DbSong, new_metadata: Dict[str, Any]) -> None:
    """
    Log the changes that would be made to song metadata.

    Args:
        original_song: Original song data
        new_metadata: New metadata dictionary to apply
    """
    changes = []

    # Check for changes in key fields
    if "title" in new_metadata and original_song.title != new_metadata["title"]:
        changes.append(f"title: '{original_song.title}' -> '{new_metadata['title']}'")

    if "artist" in new_metadata and original_song.artist != new_metadata["artist"]:
        changes.append(
            f"artist: '{original_song.artist}' -> '{new_metadata['artist']}'"
        )

    if "album" in new_metadata and original_song.album != new_metadata["album"]:
        changes.append(f"album: '{original_song.album}' -> '{new_metadata['album']}'")

    if "genre" in new_metadata and original_song.genre != new_metadata["genre"]:
        changes.append(f"genre: '{original_song.genre}' -> '{new_metadata['genre']}'")

    if (
        "release_date" in new_metadata
        and original_song.release_date != new_metadata["release_date"]
    ):
        changes.append(
            f"release_date: '{original_song.release_date}' -> '{new_metadata['release_date']}'"
        )

    if (
        "cover_art_path" in new_metadata
        and original_song.cover_art_path != new_metadata["cover_art_path"]
    ):
        changes.append(
            f"cover_art_path: '{original_song.cover_art_path}' -> '{new_metadata['cover_art_path']}'"
        )

    if (
        "itunes_track_id" in new_metadata
        and original_song.itunes_track_id != new_metadata["itunes_track_id"]
    ):
        changes.append(
            f"itunes_track_id: '{original_song.itunes_track_id}' -> '{new_metadata['itunes_track_id']}'"
        )

    if changes:
        logger.info(f"Song {original_song.id} changes: {'; '.join(changes)}")
    else:
        logger.debug(f"Song {original_song.id}: no metadata changes detected")


def get_database_stats() -> Dict[str, Any]:
    """
    Get comprehensive statistics about the song database.

    Returns:
        Dictionary with database statistics
    """
    try:
        with get_db_session() as session:
            repo = SongRepository(session)
            songs = repo.fetch_all()

        stats = {
            "total_songs": len(songs),
            "with_itunes_id": 0,
            "with_cover_art": 0,
            "with_genre": 0,
            "with_release_date": 0,
            "with_album": 0,
            "unknown_artist": 0,
        }

        for song in songs:
            if song.itunes_track_id:
                stats["with_itunes_id"] += 1
            if song.cover_art_path:
                stats["with_cover_art"] += 1
            if song.genre and song.genre.strip():
                stats["with_genre"] += 1
            if song.release_date:
                stats["with_release_date"] += 1
            if song.album and song.album.strip():
                stats["with_album"] += 1
            if not song.artist or song.artist == "Unknown Artist":
                stats["unknown_artist"] += 1

        # Calculate percentages
        if stats["total_songs"] > 0:
            for key in [
                "with_itunes_id",
                "with_cover_art",
                "with_genre",
                "with_release_date",
                "with_album",
                "unknown_artist",
            ]:
                percentage = (stats[key] / stats["total_songs"]) * 100
                stats[f"{key}_percentage"] = float(round(percentage, 1))

        return stats

    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {"error": str(e)}
