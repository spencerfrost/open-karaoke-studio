# backend/app/db/song_operations.py
"""
Song business logic and operations for Open Karaoke Studio.

This module contains all song-related CRUD operations, search functionality,
file system synchronization, and other song-specific business logic.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import asc, desc, func

from ..config import get_config
from .database import get_db_session
from .models import DbSong

logger = logging.getLogger(__name__)


def get_songs() -> list[DbSong]:
    """Get all songs from the database, sorted by date_added in descending order (newest first)"""
    try:
        with get_db_session() as session:
            songs = session.query(DbSong).order_by(DbSong.date_added.desc()).all()
            return songs
    except Exception as e:
        logger.error("Error getting songs from database: %s", e, exc_info=True)
        return []


def get_song(song_id: str) -> Optional[DbSong]:
    """Get a song by ID from the database"""
    try:
        with get_db_session() as session:
            song = session.query(DbSong).filter(DbSong.id == song_id).first()
            return song
    except Exception as e:
        logger.error(
            "Error getting song %s from database: %s", song_id, e, exc_info=True
        )
        return None


def create_or_update_song(
    song_id: str,
    title: str,
    artist: str,
    duration_ms: Optional[int] = None,
    video_id: Optional[str] = None,
    source: Optional[str] = None,
    source_url: Optional[str] = None,
    thumbnail_path: Optional[str] = None,
    cover_art_path: Optional[str] = None,
    uploader: Optional[str] = None,
    uploader_id: Optional[str] = None,
    channel: Optional[str] = None,
    channel_id: Optional[str] = None,
    description: Optional[str] = None,
    upload_date: Optional[str] = None,
    album: Optional[str] = None,
    genre: Optional[str] = None,
    language: Optional[str] = None,
    lyrics: Optional[str] = None,
    synced_lyrics: Optional[str] = None,
    favorite: bool = False,
) -> Optional[DbSong]:
    """Create or update a song in the database with direct parameters

    Args:
        song_id: Unique identifier for the song
        title: Song title
        artist: Artist name
        duration_ms: Song duration_ms in milliseconds
        video_id: YouTube video ID
        source: Source platform (e.g., 'youtube')
        source_url: Original source URL
        thumbnail_path: Path to thumbnail image
        cover_art_path: Path to cover art image
        uploader: Channel/uploader name
        uploader_id: Channel/uploader ID
        channel: Channel name
        channel_id: Channel ID
        description: Song/video description
        upload_date: Upload date string
        album: Album name
        genre: Music genre
        language: Language code
        lyrics: Song lyrics
        synced_lyrics: Time-synced lyrics
        favorite: Whether song is marked as favorite

    Returns:
        The refreshed DbSong model with all data loaded, or None if failed
    """
    try:
        with get_db_session() as session:
            db_song = session.query(DbSong).filter(DbSong.id == song_id).first()

            if not db_song:
                # Create new song with direct parameter assignment
                db_song = DbSong(
                    id=song_id,
                    title=title,
                    artist=artist,
                    duration_ms=duration_ms,
                    video_id=video_id,
                    source=source,
                    source_url=source_url,
                    thumbnail_path=thumbnail_path,
                    cover_art_path=cover_art_path,
                    uploader=uploader,
                    uploader_id=uploader_id,
                    channel=channel,
                    channel_id=channel_id,
                    description=description,
                    upload_date=upload_date,
                    album=album,
                    genre=genre,
                    language=language,
                    lyrics=lyrics,
                    synced_lyrics=synced_lyrics,
                    favorite=favorite,
                )
                session.add(db_song)
            else:
                # Update existing song with direct assignment (only non-None values)
                if title:
                    db_song.title = title
                if artist:
                    db_song.artist = artist
                if duration_ms is not None:
                    db_song.duration_ms = duration_ms
                if video_id:
                    db_song.video_id = video_id
                if source:
                    db_song.source = source
                if source_url:
                    db_song.source_url = source_url
                if thumbnail_path:
                    db_song.thumbnail_path = thumbnail_path
                if cover_art_path:
                    db_song.cover_art_path = cover_art_path
                if uploader:
                    db_song.uploader = uploader
                if uploader_id:
                    db_song.uploader_id = uploader_id
                if channel:
                    db_song.channel = channel
                if channel_id:
                    db_song.channel_id = channel_id
                if description:
                    db_song.description = description
                if upload_date:
                    db_song.upload_date = upload_date
                if album:
                    db_song.album = album
                if genre:
                    db_song.genre = genre
                if language:
                    db_song.language = language
                if lyrics:
                    db_song.lyrics = lyrics
                if synced_lyrics:
                    db_song.synced_lyrics = synced_lyrics
                # Update favorite regardless (boolean field)
                db_song.favorite = favorite

            session.commit()
            session.refresh(db_song)
            return db_song

    except Exception as e:
        logger.error("Error creating/updating song %s: %s", song_id, e, exc_info=True)
        return None


def sync_songs_with_filesystem() -> int:
    """Synchronize database with filesystem by adding new songs and removing deleted ones.

    Returns:
        Number of songs added to the database
    """
    config = get_config()
    karaoke_library_path = Path(config.KARAOKE_LIBRARY_PATH)

    if not karaoke_library_path.exists():
        logger.warning("Karaoke library path does not exist: %s", karaoke_library_path)
        return 0

    # Get song folders from filesystem
    song_folders = [d for d in karaoke_library_path.iterdir() if d.is_dir()]
    filesystem_song_ids = {folder.name for folder in song_folders}

    # Get song IDs from database
    try:
        with get_db_session() as session:
            db_song_ids = {song.id for song in session.query(DbSong.id).all()}

            # Add new songs
            new_songs_count = 0
            for song_id in filesystem_song_ids - db_song_ids:
                # Create minimal song entry for discovered folders
                # Metadata will be populated by other services (YouTube, etc.)
                if create_or_update_song(
                    song_id=song_id,
                    title="Unknown Title",  # Will be updated when metadata is available
                    artist="Unknown Artist",  # Will be updated when metadata is available
                ):
                    new_songs_count += 1
                    logger.info("Added new song folder: %s", song_id)

            # Remove songs that no longer exist in filesystem
            deleted_song_ids = db_song_ids - filesystem_song_ids
            for song_id in deleted_song_ids:
                if delete_song(song_id):
                    logger.info("Removed deleted song: %s", song_id)

            return new_songs_count

    except Exception as e:
        logger.error("Error syncing songs with filesystem: %s", e, exc_info=True)
        return 0


def delete_song(song_id: str) -> bool:
    """Delete a song from the database

    Args:
        song_id: The ID of the song to delete

    Returns:
        True if the song was successfully deleted, False otherwise
    """
    try:
        with get_db_session() as session:
            song = session.query(DbSong).filter(DbSong.id == song_id).first()

            if song:
                session.delete(song)
                session.commit()
                logger.info("Deleted song: %s", song_id)
                return True
            else:
                logger.warning("Song not found for deletion: %s", song_id)
                return False

    except Exception as e:
        logger.error("Error deleting song %s: %s", song_id, e, exc_info=True)
        return False


def update_song_audio_paths(
    song_id: str, vocals_path: str, instrumental_path: str
) -> bool:
    """Update the audio paths for a song (after audio separation is complete)

    Args:
        song_id: The ID of the song to update
        vocals_path: Path to the vocals file
        instrumental_path: Path to the instrumental file

    Returns:
        True if update was successful, False otherwise
    """
    try:
        with get_db_session() as session:
            song = session.query(DbSong).filter(DbSong.id == song_id).first()

            if not song:
                logger.error("Song not found: %s", song_id)
                return False

            # Update the audio paths
            song.vocals_path = vocals_path
            song.instrumental_path = instrumental_path

            # Set processing status to completed if both paths are provided
            if vocals_path and instrumental_path:
                song.processing_status = "completed"
                song.has_audio_files = True

            session.commit()
            logger.info("Updated audio paths for song %s", song_id)
            return True

    except Exception as e:
        logger.error(
            "Error updating audio paths for song %s: %s", song_id, e, exc_info=True
        )
        return False


def update_song_with_metadata(song_id: str, updated_song: DbSong) -> bool:
    """Update a song with new metadata from a DbSong model

    Args:
        song_id: The ID of the song to update
        updated_song: DbSong model with updated metadata

    Returns:
        True if update was successful, False otherwise
    """
    try:
        with get_db_session() as session:
            song = session.query(DbSong).filter(DbSong.id == song_id).first()

            if not song:
                logger.error("Song not found: %s", song_id)
                return False

            # Update all editable metadata fields
            song.title = updated_song.title or song.title
            song.artist = updated_song.artist or song.artist
            song.album = updated_song.album or song.album
            song.genre = updated_song.genre or song.genre
            song.year = updated_song.year or song.year
            song.duration_ms = updated_song.duration_ms or song.duration_ms
            song.lyrics = updated_song.lyrics or song.lyrics

            # Update file paths if provided - only for fields that exist
            if hasattr(updated_song, "vocals_path") and updated_song.vocals_path:
                song.vocals_path = updated_song.vocals_path
            if (
                hasattr(updated_song, "instrumental_path")
                and updated_song.instrumental_path
            ):
                song.instrumental_path = updated_song.instrumental_path
            if hasattr(updated_song, "thumbnail_path") and updated_song.thumbnail_path:
                song.thumbnail_path = updated_song.thumbnail_path

            session.commit()
            logger.info("Updated song metadata for %s", song_id)
            return True

    except Exception as e:
        logger.error(
            "Error updating song metadata for %s: %s", song_id, e, exc_info=True
        )
        return False


def update_song_thumbnail(song_id: str, thumbnail_path: str) -> bool:
    """Update the thumbnail path for a song

    Args:
        song_id: The ID of the song to update
        thumbnail_path: Path to the thumbnail file

    Returns:
        True if update was successful, False otherwise
    """
    try:
        with get_db_session() as session:
            song = session.query(DbSong).filter(DbSong.id == song_id).first()

            if not song:
                logger.error("Song not found: %s", song_id)
                return False

            # Update the thumbnail path
            song.thumbnail_path = thumbnail_path

            session.commit()
            logger.info("Updated thumbnail path for song %s", song_id)
            return True

    except Exception as e:
        logger.error(
            "Error updating thumbnail for song %s: %s", song_id, e, exc_info=True
        )
        return False


def get_artists_with_counts(
    search_term: str = "", limit: int = 100, offset: int = 0
) -> list[dict[str, Any]]:
    """Get a list of unique artists with their song counts, optionally filtered by search term.

    Args:
        search_term: Optional search term to filter artists
        limit: Maximum number of artists to return
        offset: Number of artists to skip for pagination

    Returns:
        List of dictionaries containing artist info and song counts
    """
    try:
        with get_db_session() as session:
            # Build the query
            query = session.query(
                DbSong.artist, func.count(DbSong.id).label("song_count")
            ).group_by(DbSong.artist)

            # Apply search filter if provided
            if search_term:
                query = query.filter(DbSong.artist.ilike(f"%{search_term}%"))

            # Order alphabetically by artist name for proper grouping
            query = query.order_by(DbSong.artist)

            # Apply pagination
            artists = query.offset(offset).limit(limit).all()

            # Convert to list of dictionaries with proper frontend format
            return [
                {
                    "name": artist,
                    "songCount": song_count,
                    "firstLetter": artist[0].upper() if artist else "?",
                }
                for artist, song_count in artists
            ]

    except Exception as e:
        logger.error("Error getting artists with counts: %s", e, exc_info=True)
        return []


def get_artists_total_count(search_term: str = "") -> int:
    """Get the total count of unique artists, optionally filtered by search term.

    Args:
        search_term: Optional search term to filter artists

    Returns:
        Total number of unique artists
    """
    try:
        with get_db_session() as session:
            query = session.query(DbSong.artist).distinct()

            if search_term:
                query = query.filter(DbSong.artist.ilike(f"%{search_term}%"))

            return query.count()

    except Exception as e:
        logger.error("Error getting total artist count: %s", e, exc_info=True)
        return 0


def get_songs_by_artist(
    artist_name: str,
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "title",
    direction: str = "asc",
) -> dict[str, Any]:
    """Get songs by a specific artist with pagination and sorting.

    Args:
        artist_name: The artist name to filter by
        limit: Maximum number of songs to return
        offset: Number of songs to skip for pagination
        sort_by: Field to sort by ('title', 'album', 'year', 'dateAdded')
        direction: Sort direction ('asc' or 'desc')

    Returns:
        Dictionary containing songs and pagination info
    """
    try:
        with get_db_session() as session:
            # Build base query
            base_query = session.query(DbSong).filter(DbSong.artist == artist_name)

            # Apply sorting
            sort_field = getattr(DbSong, sort_by, DbSong.title)
            if direction.lower() == "desc":
                base_query = base_query.order_by(desc(sort_field))
            else:
                base_query = base_query.order_by(asc(sort_field))

            # Get total count
            total_count = base_query.count()

            # Apply pagination
            songs = base_query.offset(offset).limit(limit).all()

            return {"songs": songs, "total": total_count}

    except Exception as e:
        logger.error(
            "Error getting songs for artist '%s': %s", artist_name, e, exc_info=True
        )
        return {"songs": [], "total": 0}


def search_songs_paginated(
    query: str,
    limit: int = 20,
    offset: int = 0,
    group_by_artist: bool = False,
    sort_by: str = "relevance",
    direction: str = "desc",
) -> dict[str, Any]:
    """Search songs with pagination and optional artist grouping.

    Args:
        query: Search query string
        limit: Maximum number of results to return
        offset: Number of results to skip
        group_by_artist: Whether to group results by artist
        sort_by: Field to sort by ('relevance', 'title', 'artist', 'dateAdded')
        direction: Sort direction ('asc' or 'desc')

    Returns:
        Dict with search results and pagination info
    """
    try:
        with get_db_session() as session:
            # Build base search query
            search_filter = (
                DbSong.title.ilike(f"%{query}%")
                | DbSong.artist.ilike(f"%{query}%")
                | DbSong.album.ilike(f"%{query}%")
            )

            if group_by_artist:
                # Group results by artist
                artist_query = (
                    session.query(
                        DbSong.artist, func.count(DbSong.id).label("song_count")
                    )
                    .filter(search_filter)
                    .group_by(DbSong.artist)
                )

                total_artists = artist_query.count()

                # Get artists with pagination
                artist_results = artist_query.offset(offset).limit(limit).all()

                artists_data = []
                total_songs = 0

                for artist, count in artist_results:
                    # Get a sample of songs for this artist
                    songs_query = (
                        session.query(DbSong)
                        .filter(search_filter, DbSong.artist == artist)
                        .limit(5)
                    )  # Show max 5 songs per artist in grouped view

                    songs = songs_query.all()
                    total_songs += count

                    artists_data.append(
                        {
                            "artist": artist,
                            "songCount": count,
                            "songs": songs,  # These will be converted to pydantic in the API
                        }
                    )

                return {
                    "artists": artists_data,
                    "total_songs": total_songs,
                    "total_artists": total_artists,
                    "pagination": {
                        "total": total_artists,
                        "limit": limit,
                        "offset": offset,
                        "hasMore": offset + limit < total_artists,
                    },
                }

            else:
                # Flat search results
                base_query = session.query(DbSong).filter(search_filter)

                # Apply sorting
                if sort_by == "relevance":
                    # Simple relevance: title matches first, then artist matches
                    base_query = base_query.order_by(
                        DbSong.title.ilike(f"%{query}%").desc(),
                        DbSong.artist.ilike(f"%{query}%").desc(),
                        DbSong.date_added.desc(),
                    )
                else:
                    sort_field = getattr(DbSong, sort_by, DbSong.title)
                    if direction.lower() == "desc":
                        base_query = base_query.order_by(desc(sort_field))
                    else:
                        base_query = base_query.order_by(asc(sort_field))

                # Get total count
                total_count = base_query.count()

                # Apply pagination
                songs = base_query.offset(offset).limit(limit).all()

                return {
                    "songs": songs,
                    "pagination": {
                        "total": total_count,
                        "limit": limit,
                        "offset": offset,
                        "hasMore": offset + limit < total_count,
                    },
                }

    except Exception as e:
        logger.error("Error searching songs: %s", e, exc_info=True)
        return {
            "songs": [],
            "pagination": {
                "total": 0,
                "limit": limit,
                "offset": offset,
                "hasMore": False,
            },
        }
