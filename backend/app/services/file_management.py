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

from ..db.models import DbSong
from .file_service import FileService

logger = logging.getLogger(__name__)

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
        logger.error("Error copying original file: %s", e, exc_info=True)
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
        head_response = session.head(
            url, headers=headers, timeout=10, allow_redirects=True
        )

        # If HEAD request fails, try a GET request anyway as some servers don't support HEAD
        if head_response.status_code != 200:
            logger.warning(
                "HEAD request failed with status %s, trying GET instead",
                head_response.status_code,
            )

        # Make the actual GET request to download the image
        response = session.get(
            url, headers=headers, stream=True, timeout=10, allow_redirects=True
        )
        response.raise_for_status()  # Raise exception for HTTP errors

        # Check if response contains image data
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            logger.warning("Downloaded content is not an image: %s", content_type)
            # Some YouTube thumbnails might not correctly report content-type
            # Check if it at least looks like an image based on first few bytes
            first_bytes = next(response.iter_content(128), b"")
            # Check for common image file signatures (JPEG, PNG, WebP)
            if not (
                first_bytes.startswith(b"\xff\xd8\xff")  # JPEG
                or first_bytes.startswith(b"\x89PNG\r\n\x1a\n")  # PNG
                or (first_bytes.startswith(b"RIFF") and b"WEBP" in first_bytes[:12])
            ):  # WebP
                logger.warning(
                    "Content doesn't appear to be an image based on file signature"
                )
                return False

        # Ensure the directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # Save the image
        with open(save_path, "wb") as f:  # Binary mode doesn't take encoding
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Verify the file was saved and has content
        if save_path.exists() and save_path.stat().st_size > 0:
            return True
        else:
            logger.warning(
                "Image file was saved but appears to be empty: %s", save_path
            )
            return False

    except requests.exceptions.RequestException as e:
        logger.error("Network error downloading image from %s: %s", url, e)
        return False
    except Exception as e:
        logger.error("Error downloading image from %s: %s", url, e)
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
