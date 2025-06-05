# backend/app/services/file_management.py
#
# ===== CLEANED UP VERSION =====
# Legacy file operations have been moved to FileService.
# This file now contains only business logic functions that go beyond simple file operations.
# ==============================

import shutil
import json
import requests
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from ..config import get_config
from ..db.models import SongMetadata 
from .file_service import FileService

# =============================================================================
# PATH CONSTRUCTION HELPERS - These provide useful path construction logic
# =============================================================================

def get_vocals_path_stem(song_dir: Path) -> Path:
    """Returns the standard path stem (without extension) for the vocals file."""
    return song_dir / "vocals"


def get_instrumental_path_stem(song_dir: Path) -> Path:
    """Returns the standard path stem (without extension) for the instrumental file."""
    return song_dir / "instrumental"

# =============================================================================
# FILE OPERATIONS WITH BUSINESS LOGIC
# =============================================================================

def save_original_file(input_path: Path, song_dir: Path) -> Optional[Path]:
    """Copies the original input file to the song directory."""
    if not input_path.exists():
        return None

    # Use FileService to get the correct original file path
    song_id = song_dir.name
    original_suffix = input_path.suffix
    file_service = FileService()
    destination = file_service.get_original_path(song_id, original_suffix)
    
    try:
        shutil.copy2(input_path, destination)
        return destination
    except (IOError, OSError) as e:
        print(f"Error copying original file: {e}")
        return None


def get_processed_songs(library_path: Optional[Path] = None) -> List[str]:
    """Scans the library and returns a list of potential song IDs (directories).
    
    NOTE: This function remains for compatibility with custom library paths.
    For default library, prefer FileService.get_processed_song_ids()
    """
    if library_path:
        # If custom library path provided, use direct implementation
        if not library_path.is_dir():
            return []
        return [d.name for d in library_path.iterdir() if d.is_dir()]
    else:
        # Use FileService for default library
        file_service = FileService()
        return file_service.get_processed_song_ids()

# =============================================================================
# METADATA FUNCTIONS - Database and business logic
# =============================================================================

def read_song_metadata(
    song_id: str, library_path: Optional[Path] = None
) -> Optional[SongMetadata]:
    """
    Reads song metadata from the database.
    Falls back to legacy metadata.json if database entry not found.
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
            return metadata
            
    except ImportError:
        logging.error("Cannot read metadata: Database module not available")
        raise Exception("Database module not available, cannot read metadata")
    
    
    
    except Exception as e:
        print(f"Error accessing database: {e}")
        return None


def write_song_metadata(song_id: str, metadata: SongMetadata):
    """
    Writes song metadata to the database.
    No longer writes to metadata.json file.
    """
    try:
        from ..db import database
        database.create_or_update_song(song_id, metadata)
        logging.info(f"Updated database record for song: {song_id}")
    except ImportError:
        # Database module not available, log error
        logging.error("Cannot save metadata: Database module not available")
        raise Exception("Database module not available, cannot save metadata")
    except Exception as e:
        logging.error(f"Error updating database for {song_id}: {e}")
        raise Exception(f"Could not write metadata for {song_id}: {e}") from e


def download_image(url: str, save_path: Path) -> bool:
    """Downloads an image from a URL and saves it to the specified path."""
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()  # Raise exception for HTTP errors

        # Check if response contains image data
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            print(f"Downloaded content is not an image: {content_type}")
            return False

        # Save the image
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")
        return False

# =============================================================================
# PATH HELPERS - Simple utilities
# =============================================================================

def get_thumbnail_path(song_dir: Path) -> Path:
    """Returns the standard path for the YouTube thumbnail.
    
    NOTE: Consider using FileService.get_thumbnail_path() for consistency.
    """
    return song_dir / "thumbnail.jpg"


def get_cover_art_path(song_dir: Path) -> Path:
    """Returns the standard path for the album cover art.
    
    NOTE: Consider using FileService.get_cover_art_path() for consistency.
    """
    return song_dir / "cover.jpg"

# =============================================================================
# END OF FILE
# =============================================================================
