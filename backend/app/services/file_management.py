# backend/app/services/file_management.py
#
# ===== CLEANED UP VERSION =====
# Legacy file operations have been moved to FileService.
# This file now contains only business logic functions that go beyond simple file operations.
# ==============================

import logging
import shutil
from pathlib import Path
from typing import Optional

import requests

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
    except OSError as e:
        print(f"Error copying original file: {e}")
        return None


def get_processed_songs(library_path: Optional[Path] = None) -> list[str]:
    """Scans the library and returns a list of potential song IDs (directories).

    NOTE: This function remains for compatibility with custom library paths.
    For default library, prefer FileService.get_processed_song_ids()
    """
    if library_path:
        # If custom library path provided, use direct implementation
        if not library_path.is_dir():
            return []
        return [d.name for d in library_path.iterdir() if d.is_dir()]
    
    # Use FileService for default library
    file_service = FileService()
    return file_service.get_processed_song_ids()


# =============================================================================
# METADATA FUNCTIONS - Database and business logic
# =============================================================================


def read_song_metadata(song_id: str, library_path: Optional[Path] = None) -> Optional[SongMetadata]:
    """
    Reads song metadata from the database.
    Falls back to legacy metadata.json if database entry not found.
    """
    try:
        from ..db.song_operations import get_song

        db_song = get_song(song_id)

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
                releaseTitle=db_song.album,
                releaseId=db_song.release_id,
                releaseDate=db_song.release_date,
                genre=db_song.genre,
                language=db_song.language,
                lyrics=db_song.lyrics,
                syncedLyrics=db_song.synced_lyrics,
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
        from ..db.song_operations import create_or_update_song

        create_or_update_song(song_id, metadata)
        logging.info("Updated database record for song: %s", song_id)
    except ImportError:
        # Database module not available, log error
        logging.error("Cannot save metadata: Database module not available")
        raise Exception("Database module not available, cannot save metadata")
    except Exception as e:
        logging.error("Error updating database for %s: %s", song_id, e)
        raise Exception(f"Could not write metadata for {song_id}: {e}") from e


def download_image(url: str, save_path: Path) -> bool:
    """Downloads an image from a URL and saves it to the specified path."""
    try:
        # Create a session to handle redirects properly
        session = requests.Session()

        # Configure session with user agent to avoid being blocked
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
        }

        # First make a HEAD request to check content type and handle redirects
        head_response = session.head(url, headers=headers, timeout=10, allow_redirects=True)

        # If HEAD request fails, try a GET request anyway as some servers don't support HEAD
        if head_response.status_code != 200:
            logging.warning(
                "HEAD request failed with status %s, trying GET instead", head_response.status_code
            )

        # Make the actual GET request to download the image
        response = session.get(url, headers=headers, stream=True, timeout=10, allow_redirects=True)
        response.raise_for_status()  # Raise exception for HTTP errors

        # Check if response contains image data
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            logging.warning("Downloaded content is not an image: %s", content_type)
            # Some YouTube thumbnails might not correctly report content-type
            # Check if it at least looks like an image based on first few bytes
            first_bytes = next(response.iter_content(128), b"")
            # Check for common image file signatures (JPEG, PNG, WebP)
            if not (
                first_bytes.startswith(b"\xff\xd8\xff")  # JPEG
                or first_bytes.startswith(b"\x89PNG\r\n\x1a\n")  # PNG
                or (first_bytes.startswith(b"RIFF") and b"WEBP" in first_bytes[:12])
            ):  # WebP
                logging.warning("Content doesn't appear to be an image based on file signature")
                return False

        # Ensure the directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # Save the image
        with open(save_path, "wb", encoding="utf-8") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Verify the file was saved and has content
        if save_path.exists() and save_path.stat().st_size > 0:
            logging.info("Successfully downloaded and saved image to %s", save_path)
            return True
        else:
            logging.warning("Image file was saved but appears to be empty: %s", save_path)
            return False

    except requests.exceptions.RequestException as e:
        logging.error("Network error downloading image from %s: %s", url, e)
        return False
    except Exception as e:
        logging.error("Error downloading image from %s: %s", url, e)
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
