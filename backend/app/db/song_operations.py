# backend/app/db/song_operations.py
"""
Song business logic and operations for Open Karaoke Studio.

This module contains all song-related CRUD operations, search functionality,
file system synchronization, and other song-specific business logic.
"""

import logging
import traceback
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import asc, desc, func

from ..config import get_config
from ..services import file_management
from .database import get_db_session
from .models import DbSong, SongMetadata


def get_all_songs() -> list[DbSong]:
    """Get all songs from the database, sorted by date_added in descending order (newest first)"""
    try:
        with get_db_session() as session:
            songs = session.query(DbSong).order_by(DbSong.date_added.desc()).all()
            return songs
    except Exception as e:
        logging.error("Error getting songs from database: %s", e)
        return []


def get_song(song_id: str) -> Optional[DbSong]:
    """Get a song by ID from the database"""
    try:
        with get_db_session() as session:
            song = session.query(DbSong).filter(DbSong.id == song_id).first()
            return song
    except Exception as e:
        logging.error("Error getting song %s from database: %s", song_id, e)
        return None


def create_or_update_song(song_id: str, metadata: SongMetadata) -> Optional[DbSong]:
    """Create or update a song in the database from metadata

    Returns:
        The refreshed DbSong model with all data loaded
    """

    try:
        with get_db_session() as session:
            db_song = session.query(DbSong).filter(DbSong.id == song_id).first()

            if not db_song:
                # Create new song
                db_song = DbSong(id=song_id)
                session.add(db_song)

            # Update all fields from metadata (using safe attribute access)
            db_song.title = metadata.title
            db_song.artist = metadata.artist
            db_song.album = getattr(metadata, "album", None)
            db_song.genre = metadata.genre
            db_song.year = getattr(metadata, "year", None)
            db_song.track_number = getattr(metadata, "track_number", None)
            db_song.disc_number = getattr(metadata, "disc_number", None)
            db_song.duration = metadata.duration
            db_song.file_path = getattr(metadata, "file_path", None)
            db_song.file_size = getattr(metadata, "file_size", None)
            db_song.original_filename = metadata.original_filename

            # Update audio paths if provided
            if metadata.vocals_path:
                db_song.vocals_path = metadata.vocals_path
            if metadata.instrumental_path:
                db_song.instrumental_path = metadata.instrumental_path

            session.commit()

            # Refresh to get all updated data including auto-generated fields
            session.refresh(db_song)

            return db_song

    except Exception as e:
        logging.error("Error creating/updating song %s: %s", song_id, e)
        logging.error(traceback.format_exc())
        return None


def sync_songs_with_filesystem() -> int:
    """Synchronize database with filesystem by adding new songs and removing deleted ones.

    Returns:
        Number of songs added to the database
    """
    config = get_config()
    karaoke_library_path = Path(config.KARAOKE_LIBRARY_PATH)

    if not karaoke_library_path.exists():
        logging.warning("Karaoke library path does not exist: %s", karaoke_library_path)
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
                # Use file_management service to get metadata
                metadata = file_management.read_song_metadata(song_id)
                if metadata:
                    if create_or_update_song(song_id, metadata):
                        new_songs_count += 1
                        logging.info("Added new song: %s", song_id)

            # Remove songs that no longer exist in filesystem
            deleted_song_ids = db_song_ids - filesystem_song_ids
            for song_id in deleted_song_ids:
                if delete_song(song_id):
                    logging.info("Removed deleted song: %s", song_id)

            return new_songs_count

    except Exception as e:
        logging.error("Error syncing songs with filesystem: %s", e)
        logging.error(traceback.format_exc())
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
                logging.info("Deleted song: %s", song_id)
                return True
            else:
                logging.warning("Song not found for deletion: %s", song_id)
                return False

    except Exception as e:
        logging.error("Error deleting song %s: %s", song_id, e)
        logging.error(traceback.format_exc())
        return False


def update_song_audio_paths(song_id: str, vocals_path: str, instrumental_path: str) -> bool:
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
                logging.error("Song not found: %s", song_id)
                return False

            # Update the audio paths
            song.vocals_path = vocals_path
            song.instrumental_path = instrumental_path

            # Set processing status to completed if both paths are provided
            if vocals_path and instrumental_path:
                song.processing_status = "completed"
                song.has_audio_files = True

            session.commit()
            logging.info("Updated audio paths for song %s", song_id)
            return True

    except Exception as e:
        logging.error("Error updating audio paths for song %s: %s", song_id, e)
        logging.error(traceback.format_exc())
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
                logging.error("Song not found: %s", song_id)
                return False

            # Update all editable metadata fields
            song.title = updated_song.title or song.title
            song.artist = updated_song.artist or song.artist
            song.album = updated_song.album or song.album
            song.genre = updated_song.genre or song.genre
            song.year = updated_song.year or song.year
            song.track_number = updated_song.track_number or song.track_number
            song.disc_number = updated_song.disc_number or song.disc_number
            song.duration = updated_song.duration or song.duration
            song.lyrics = updated_song.lyrics or song.lyrics
            song.itunes_artwork_url = updated_song.itunes_artwork_url or song.itunes_artwork_url
            song.itunes_track_id = updated_song.itunes_track_id or song.itunes_track_id
            song.youtube_url = updated_song.youtube_url or song.youtube_url
            song.preview_url = updated_song.preview_url or song.preview_url
            song.release_date = updated_song.release_date or song.release_date
            song.apple_music_id = updated_song.apple_music_id or song.apple_music_id
            song.spotify_id = updated_song.spotify_id or song.spotify_id
            song.isrc = updated_song.isrc or song.isrc
            song.explicit = (
                updated_song.explicit if updated_song.explicit is not None else song.explicit
            )
            song.popularity = updated_song.popularity or song.popularity
            song.energy = updated_song.energy or song.energy
            song.danceability = updated_song.danceability or song.danceability
            song.valence = updated_song.valence or song.valence
            song.acousticness = updated_song.acousticness or song.acousticness
            song.instrumentalness = updated_song.instrumentalness or song.instrumentalness
            song.speechiness = updated_song.speechiness or song.speechiness
            song.liveness = updated_song.liveness or song.liveness
            song.loudness = updated_song.loudness or song.loudness
            song.tempo = updated_song.tempo or song.tempo
            song.time_signature = updated_song.time_signature or song.time_signature
            song.key_signature = updated_song.key_signature or song.key_signature
            song.mode = updated_song.mode or song.mode

            # Update file paths if provided
            if updated_song.file_path:
                song.file_path = updated_song.file_path
            if updated_song.vocals_path:
                song.vocals_path = updated_song.vocals_path
            if updated_song.instrumental_path:
                song.instrumental_path = updated_song.instrumental_path
            if updated_song.thumbnail_path:
                song.thumbnail_path = updated_song.thumbnail_path

            # Update status fields if provided
            if updated_song.processing_status:
                song.processing_status = updated_song.processing_status
            if updated_song.has_audio_files is not None:
                song.has_audio_files = updated_song.has_audio_files

            session.commit()
            logging.info("Updated song metadata for %s", song_id)
            return True

    except Exception as e:
        logging.error("Error updating song metadata for %s: %s", song_id, e)
        logging.error(traceback.format_exc())
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
                logging.error("Song not found: %s", song_id)
                return False

            # Update the thumbnail path
            song.thumbnail_path = thumbnail_path

            session.commit()
            logging.info("Updated thumbnail path for song %s", song_id)
            return True

    except Exception as e:
        logging.error("Error updating thumbnail for song %s: %s", song_id, e)
        logging.error(traceback.format_exc())
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
        logging.error("Error getting artists with counts: %s", e)
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
        logging.error("Error getting total artist count: %s", e)
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
        logging.error("Error getting songs for artist '%s': %s", artist_name, e)
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
                    session.query(DbSong.artist, func.count(DbSong.id).label("song_count"))
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
        logging.error("Error searching songs: %s", e)
        return {
            "songs": [],
            "pagination": {"total": 0, "limit": limit, "offset": offset, "hasMore": False},
        }
