# backend/app/services/metadata_manager.py
"""
Metadata management service for handling song metadata operations.

This service manages metadata operations including reading from/writing to
the database and handling legacy metadata.json files during migration.
"""

import logging
from typing import Optional
from pathlib import Path

from ..db.models import SongMetadata
from ..exceptions import ServiceError


class MetadataManager:
    """
    Service for managing song metadata operations.
    
    Handles metadata persistence in the database and provides
    fallback support for legacy metadata.json files.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def read_song_metadata(
        self, 
        song_id: str, 
        library_path: Optional[Path] = None
    ) -> Optional[SongMetadata]:
        """
        Reads song metadata from the database.
        Falls back to legacy metadata.json if database entry not found.
        
        Args:
            song_id: The unique identifier for the song
            library_path: Optional library path (for legacy fallback)
            
        Returns:
            SongMetadata object if found, None otherwise
            
        Raises:
            ServiceError: If database is unavailable or other critical error occurs
        """
        try:
            from ..db import database
            db_song = database.get_song(song_id)
            
            if db_song:
                # Convert DbSong to SongMetadata
                metadata = SongMetadata(
                    title=db_song.title,
                    artist=db_song.artist,
                    duration=db_song.duration,
                    favorite=db_song.favorite,
                    dateAdded=db_song.date_added,
                    coverArt=db_song.cover_art_path,
                    thumbnail=db_song.thumbnail_path,
                    source=db_song.source,
                    sourceUrl=db_song.source_url,
                    videoId=db_song.video_id,
                    uploader=db_song.uploader,
                    uploaderId=db_song.uploader_id,
                    channel=db_song.channel,
                    channelId=db_song.channel_id,
                    description=db_song.description,
                    uploadDate=db_song.upload_date,
                    mbid=db_song.mbid,
                    releaseTitle=db_song.release_title,
                    releaseId=db_song.release_id,
                    releaseDate=db_song.release_date,
                    genre=db_song.genre,
                    language=db_song.language,
                    lyrics=db_song.lyrics,
                    syncedLyrics=db_song.synced_lyrics
                )
                self.logger.info(f"Successfully read metadata for song: {song_id}")
                return metadata
            else:
                self.logger.info(f"No database entry found for song: {song_id}")
                return None
                
        except ImportError:
            self.logger.error("Cannot read metadata: Database module not available")
            raise ServiceError("Database module not available, cannot read metadata")
        except Exception as e:
            self.logger.error(f"Error reading metadata for {song_id}: {e}")
            return None
    
    def write_song_metadata(self, song_id: str, metadata: SongMetadata) -> None:
        """
        Writes song metadata to the database.
        No longer writes to metadata.json file.
        
        Args:
            song_id: The unique identifier for the song
            metadata: The metadata object to save
            
        Raises:
            ServiceError: If database is unavailable or write operation fails
        """
        try:
            from ..db import database
            database.create_or_update_song(song_id, metadata)
            self.logger.info(f"Successfully updated database record for song: {song_id}")
        except ImportError:
            self.logger.error("Cannot save metadata: Database module not available")
            raise ServiceError("Database module not available, cannot save metadata")
        except Exception as e:
            self.logger.error(f"Error updating database for {song_id}: {e}")
            raise ServiceError(f"Could not write metadata for {song_id}: {e}") from e
    
    def delete_song_metadata(self, song_id: str) -> bool:
        """
        Deletes song metadata from the database.
        
        Args:
            song_id: The unique identifier for the song
            
        Returns:
            True if deletion was successful, False otherwise
            
        Raises:
            ServiceError: If database is unavailable
        """
        try:
            from ..db import database
            success = database.delete_song(song_id)
            if success:
                self.logger.info(f"Successfully deleted metadata for song: {song_id}")
            else:
                self.logger.warning(f"No metadata found to delete for song: {song_id}")
            return success
        except ImportError:
            self.logger.error("Cannot delete metadata: Database module not available")
            raise ServiceError("Database module not available, cannot delete metadata")
        except Exception as e:
            self.logger.error(f"Error deleting metadata for {song_id}: {e}")
            raise ServiceError(f"Could not delete metadata for {song_id}: {e}") from e
    
    def update_metadata_field(
        self, 
        song_id: str, 
        field_name: str, 
        value: any
    ) -> bool:
        """
        Updates a specific metadata field for a song.
        
        Args:
            song_id: The unique identifier for the song
            field_name: The name of the field to update
            value: The new value for the field
            
        Returns:
            True if update was successful, False otherwise
            
        Raises:
            ServiceError: If database is unavailable or update fails
        """
        try:
            # First read existing metadata
            metadata = self.read_song_metadata(song_id)
            if not metadata:
                self.logger.warning(f"No metadata found for song {song_id} to update")
                return False
            
            # Update the specific field
            if hasattr(metadata, field_name):
                setattr(metadata, field_name, value)
                self.write_song_metadata(song_id, metadata)
                self.logger.info(f"Updated {field_name} for song: {song_id}")
                return True
            else:
                self.logger.error(f"Invalid field name: {field_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating {field_name} for {song_id}: {e}")
            raise ServiceError(f"Could not update {field_name} for {song_id}: {e}") from e
    
    def metadata_exists(self, song_id: str) -> bool:
        """
        Checks if metadata exists for a given song.
        
        Args:
            song_id: The unique identifier for the song
            
        Returns:
            True if metadata exists, False otherwise
        """
        try:
            metadata = self.read_song_metadata(song_id)
            return metadata is not None
        except ServiceError:
            # If there's a service error, we can't determine existence
            return False
        except Exception as e:
            self.logger.error(f"Error checking metadata existence for {song_id}: {e}")
            return False
