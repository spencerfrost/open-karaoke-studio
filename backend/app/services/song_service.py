# backend/app/services/song_service.py
"""
Song Service Layer - handles all song-related business logic
"""

import logging
from typing import Optional

from ..db import song_operations
from ..db.models import Song, SongMetadata
from ..exceptions import DatabaseError, ServiceError
from .interfaces.song_service import SongServiceInterface

logger = logging.getLogger(__name__)


class SongService(SongServiceInterface):
    """
    Song Service implementation handling all song-related business logic.
    Removes fat controller patterns by centralizing song operations.
    """

    def __init__(self):
        """Initialize the song service"""

    def get_all_songs(self) -> list[Song]:
        """
        Get all songs with automatic filesystem sync if needed.

        Returns:
            List of Song objects

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            from ..db.song_operations import get_all_songs

            db_songs = get_all_songs()

            # If no songs found, attempt sync with filesystem
            if not db_songs:
                logger.info("No songs in database, attempting filesystem sync")
                sync_count = self.sync_with_filesystem()
                logger.info("Synced %s songs from filesystem", sync_count)
                db_songs = get_all_songs()

            # Convert to Pydantic models for API response
            songs = [song.to_pydantic() for song in db_songs]
            return songs

        except Exception as e:
            logger.error(f"Error retrieving songs: {e}", exc_info=True)
            raise ServiceError("Failed to retrieve songs")

    def get_song_by_id(self, song_id: str) -> Optional[Song]:
        """
        Get single song by ID.

        Args:
            song_id: Song identifier

        Returns:
            Song object if found, None otherwise

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            from ..db.song_operations import get_song

            db_song = get_song(song_id)
            return db_song.to_pydantic() if db_song else None

        except Exception as e:
            logger.error(f"Error retrieving song {song_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to retrieve song {song_id}")

    def search_songs(self, query: str) -> list[Song]:
        """
        Search songs by title or artist.

        Args:
            query: Search query string

        Returns:
            List of matching Song objects

        Raises:
            ServiceError: If search fails
        """
        try:
            # For now, get all songs and filter in memory
            # This can be optimized with database-level search later
            all_songs = song_operations.get_all_songs()

            if not query.strip():
                return [song.to_pydantic() for song in all_songs]

            query_lower = query.lower()
            matching_songs = []

            for db_song in all_songs:
                # Search in title and artist
                if query_lower in db_song.title.lower() or query_lower in db_song.artist.lower():
                    matching_songs.append(db_song.to_pydantic())

            return matching_songs

        except Exception as e:
            logger.error(f"Error searching songs with query '{query}': {e}", exc_info=True)
            raise ServiceError("Failed to search songs")

    def create_song_from_metadata(self, song_id: str, metadata: SongMetadata) -> Song:
        """
        Create song from metadata.

        Args:
            song_id: Song identifier
            metadata: Song metadata

        Returns:
            Created Song object

        Raises:
            ServiceError: If creation fails
        """
        try:
            from ..db.song_operations import create_or_update_song

            db_song = create_or_update_song(song_id, metadata)
            if not db_song:
                raise DatabaseError(f"Failed to create song {song_id}")

            return db_song.to_pydantic()

        except Exception as e:
            logger.error(f"Error creating song {song_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to create song {song_id}")

    def update_song_metadata(self, song_id: str, metadata: SongMetadata) -> Optional[Song]:
        """
        Update song metadata.

        Args:
            song_id: Song identifier
            metadata: Updated metadata

        Returns:
            Updated Song object if successful, None if song not found

        Raises:
            ServiceError: If update fails
        """
        try:
            from ..db.song_operations import create_or_update_song, get_song

            # Check if song exists
            existing_song = get_song(song_id)
            if not existing_song:
                return None

            # Update the song
            db_song = create_or_update_song(song_id, metadata)
            return db_song.to_pydantic() if db_song else None

        except Exception as e:
            logger.error(f"Error updating song {song_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to update song {song_id}")

    def delete_song(self, song_id: str) -> bool:
        """
        Delete song and associated files.

        Args:
            song_id: Song identifier

        Returns:
            True if deleted successfully, False if not found

        Raises:
            ServiceError: If deletion fails
        """
        try:
            from ..db.song_operations import delete_song, get_song

            # Check if song exists
            existing_song = get_song(song_id)
            if not existing_song:
                return False

            # Delete from database
            success = delete_song(song_id)
            return success

        except Exception as e:
            logger.error(f"Error deleting song {song_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to delete song {song_id}")

    def sync_with_filesystem(self) -> int:
        """
        Sync database with filesystem.

        Returns:
            Number of songs synced

        Raises:
            ServiceError: If sync fails
        """
        try:
            from ..db.song_operations import sync_songs_with_filesystem

            # For now, delegate to existing database function
            # This will be refactored in future sync service issue
            return sync_songs_with_filesystem()

        except Exception as e:
            logger.error(f"Error syncing with filesystem: {e}", exc_info=True)
            raise ServiceError("Failed to sync with filesystem")
