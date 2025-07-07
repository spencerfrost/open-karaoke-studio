"""
Cover Art Utilities for Metadata Update Script

This module handles all cover art related operations including:
- Detecting low-resolution cover art
- Downloading high-resolution cover art
- Validating cover art files
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

from app.db.models import DbSong
from app.services.file_management import get_cover_art_path
from app.services.itunes_service import get_itunes_cover_art
from app.config import get_config

logger = logging.getLogger(__name__)

# Constants
LOW_RES_THRESHOLD = 20000  # 20KB - files smaller than this are considered low-res
HIGH_RES_MIN_SIZE = 50000  # 50KB - minimum size for a good high-res image


def is_low_resolution_cover_art(cover_art_path: Path) -> bool:
    """
    Check if a cover art file is low resolution based on file size.

    Args:
        cover_art_path: Path to the cover art file

    Returns:
        True if the file is low resolution or doesn't exist
    """
    if not cover_art_path.exists():
        return True

    file_size = cover_art_path.stat().st_size
    return file_size < LOW_RES_THRESHOLD


def should_download_cover_art(
    song: DbSong, force_download: bool = False
) -> tuple[bool, str]:
    """
    Determine if cover art should be downloaded for a song.

    Args:
        song: The song database object
        force_download: Whether to force re-download even if cover art exists

    Returns:
        Tuple of (should_download, reason)
    """
    config = get_config()
    song_dir = config.LIBRARY_DIR / song.id

    if not song_dir.exists():
        return False, f"Song directory does not exist: {song_dir}"

    if not song.cover_art_path:
        return True, "No cover art at all"

    if force_download:
        return True, "Force re-download requested"

    # Check if existing cover art is low-resolution
    cover_art_path = get_cover_art_path(song_dir)
    if is_low_resolution_cover_art(cover_art_path):
        if cover_art_path.exists():
            file_size = cover_art_path.stat().st_size
            return (
                True,
                f"Low-res cover art ({file_size} bytes), will upgrade to high-res",
            )
        else:
            return True, "Cover art file missing, will re-download"

    file_size = cover_art_path.stat().st_size
    return False, f"Already has high-res cover art ({file_size} bytes)"


def download_high_res_cover_art(
    song: DbSong, itunes_data: Dict[str, Any], dry_run: bool = False
) -> Optional[str]:
    """
    Download high-resolution cover art for a song.

    Args:
        song: The song database object
        itunes_data: iTunes metadata containing artwork URL
        dry_run: If True, only simulate the download

    Returns:
        Relative path to the downloaded cover art, or None if failed
    """
    config = get_config()
    song_dir = config.LIBRARY_DIR / song.id

    if dry_run:
        logger.info(f"[DRY RUN] Would download high-res cover art for song {song.id}")
        cover_art_path = get_cover_art_path(song_dir)
        return str(cover_art_path.relative_to(config.LIBRARY_DIR))

    # Use the FIXED get_itunes_cover_art function (has 600x600 logic)
    logger.info(f"Downloading high-res cover art for song {song.id}")
    relative_path = get_itunes_cover_art(itunes_data, song_dir)

    if relative_path:
        # Verify the download worked and file size is reasonable
        cover_art_path = get_cover_art_path(song_dir)
        if cover_art_path.exists():
            file_size = cover_art_path.stat().st_size
            if file_size > LOW_RES_THRESHOLD:
                logger.info(
                    f"Successfully downloaded high-res cover art for song {song.id} ({file_size} bytes)"
                )
                return relative_path
            else:
                logger.warning(
                    f"Downloaded cover art for song {song.id} seems small ({file_size} bytes)"
                )
                return relative_path
        else:
            logger.error(f"Cover art file not found after download for song {song.id}")
            return None
    else:
        logger.warning(f"Failed to download cover art for song {song.id}")
        return None


def validate_cover_art_quality(cover_art_path: Path) -> tuple[bool, str]:
    """
    Validate the quality of a cover art file.

    Args:
        cover_art_path: Path to the cover art file

    Returns:
        Tuple of (is_high_quality, description)
    """
    if not cover_art_path.exists():
        return False, "File does not exist"

    file_size = cover_art_path.stat().st_size

    if file_size < LOW_RES_THRESHOLD:
        return False, f"Low resolution ({file_size} bytes)"
    elif file_size >= HIGH_RES_MIN_SIZE:
        return True, f"High resolution ({file_size} bytes)"
    else:
        return True, f"Medium resolution ({file_size} bytes)"


def get_cover_art_stats() -> Dict[str, int]:
    """
    Get statistics about cover art across all songs in the database.

    Returns:
        Dictionary with cover art statistics
    """
    from app.repositories.song_repository import SongRepository
from app.db.database import get_db_session

    config = get_config()
    with get_db_session() as session:
        repo = SongRepository(session)
        songs = repo.fetch_all()

    stats = {
        "total_songs": len(songs),
        "with_cover_art": 0,
        "without_cover_art": 0,
        "low_res_cover_art": 0,
        "high_res_cover_art": 0,
        "missing_files": 0,
    }

    for song in songs:
        if song.cover_art_path:
            stats["with_cover_art"] += 1
            song_dir = config.LIBRARY_DIR / song.id
            cover_art_path = get_cover_art_path(song_dir)

            if cover_art_path.exists():
                if is_low_resolution_cover_art(cover_art_path):
                    stats["low_res_cover_art"] += 1
                else:
                    stats["high_res_cover_art"] += 1
            else:
                stats["missing_files"] += 1
        else:
            stats["without_cover_art"] += 1

    return stats
