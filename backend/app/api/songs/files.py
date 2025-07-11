"""Song API Files Module"""

import os
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from app.config import get_config
from app.db.database import get_db_session
from app.exceptions import (
    FileOperationError,
    InvalidTrackTypeError,
    ResourceNotFoundError,
    ValidationError,
)
from app.repositories.song_repository import SongRepository
from app.services import FileService
from app.utils.error_handlers import handle_api_error
from app.utils.validation import validate_path_params
from flask import send_file, send_from_directory

from . import logger, song_bp


import logging

print("songs/files.py loaded")

def get_thumbnail(song_id: str, extension: str):
    """Serve the thumbnail image for a song."""
    logger = logging.getLogger(__name__)
    # Decode the song ID to handle URL-encoded characters
    song_id = unquote(song_id)

    # Validate extension
    allowed_extensions = {"jpg", "jpeg", "png", "webp"}
    if extension.lower() not in allowed_extensions:
        logger.warning(f"Invalid image format requested: {extension}")
        raise ValidationError(
            f"Invalid image format: {extension}. Allowed: {', '.join(allowed_extensions)}",
            "INVALID_IMAGE_FORMAT",
        )

    # Get song from database to find thumbnail path
    with get_db_session() as session:
        repo = SongRepository(session)
        db_song = repo.fetch(song_id)
    if not db_song:
        logger.warning(f"Song not found in DB: {song_id}")
        raise ResourceNotFoundError("Song", song_id)

    # Construct the path to the thumbnail
    file_service = FileService()
    song_dir = file_service.get_song_directory(song_id)
    thumbnail_path = song_dir / f"thumbnail.{extension}"
    logger.info(f"LIBRARY_DIR: {file_service.base_library_dir}")
    logger.info(f"Looking for thumbnail at: {thumbnail_path}")

    if not thumbnail_path.exists():
        logger.warning(f"Thumbnail not found: {thumbnail_path}")
        raise ResourceNotFoundError(
            "Thumbnail image", f"{song_id}/thumbnail.{extension}"
        )

    if not os.access(thumbnail_path, os.R_OK):
        logger.warning(f"Thumbnail not readable: {thumbnail_path}")
        raise FileOperationError("read", str(thumbnail_path), "File is not readable")

    # Determine correct mimetype based on extension
    mimetype_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }
    mimetype = mimetype_map.get(extension.lower(), "image/jpeg")

    try:
        return send_file(thumbnail_path, mimetype=mimetype)
    except FileNotFoundError as e:
        logger.error(f"FileNotFoundError serving thumbnail: {e}")
        raise ResourceNotFoundError(
            "Thumbnail image", f"{song_id}/thumbnail.{extension}"
        )
    except PermissionError as e:
        logger.error(f"PermissionError serving thumbnail: {e}")
        raise FileOperationError(
            "serve",
            str(thumbnail_path),
            f"Permission denied accessing thumbnail: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error serving thumbnail: {e}")
        raise FileOperationError(
            "serve",
            str(thumbnail_path),
            f"Unexpected error serving thumbnail: {str(e)}",
        )


@song_bp.route("/<string:song_id>/thumbnail", methods=["GET"])
@handle_api_error
def get_thumbnail_auto(song_id: str):
    """Serve the thumbnail image for a song, auto-detecting format."""
    import os

    from flask import send_file

    # Decode the song ID to handle URL-encoded characters
    song_id = unquote(song_id)

    # Get song from database to find thumbnail path
    with get_db_session() as session:
        repo = SongRepository(session)
        db_song = repo.fetch(song_id)
    if not db_song:
        raise ResourceNotFoundError("Song", song_id)

    # Construct the path to the thumbnail
    file_service = FileService()
    song_dir = file_service.get_song_directory(song_id)

    # Try different formats in order of preference
    formats_to_try = [
        ("webp", "image/webp"),  # Best quality/compression
        ("jpg", "image/jpeg"),  # Most common
        ("jpeg", "image/jpeg"),  # Alternative JPEG extension
        ("png", "image/png"),  # Lossless fallback
    ]

    for extension, mimetype in formats_to_try:
        thumbnail_path = song_dir / f"thumbnail.{extension}"
        if thumbnail_path.exists() and os.access(thumbnail_path, os.R_OK):
            try:
                return send_file(thumbnail_path, mimetype=mimetype)
            except Exception as e:
                logger.warning("Failed to serve thumbnail %s: %s", thumbnail_path, e)
                continue  # Try next format

    raise ResourceNotFoundError("Thumbnail image", f"{song_id}/thumbnail.*")


@song_bp.route("/<string:song_id>/download/<string:track_type>", methods=["GET"])
@handle_api_error
@validate_path_params(song_id=str, track_type=str)
def download_song_track(song_id: str, track_type: str):
    print("download_song_track called", song_id, track_type)
    logger = logging.getLogger(__name__)
    logger.info(f"Download request for song '{song_id}', track type '{track_type}'")
    track_type = track_type.lower()
    valid_track_types = ["vocals", "instrumental", "original"]
    if track_type not in valid_track_types:
        logger.warning(f"Invalid track type requested: {track_type}")
        raise InvalidTrackTypeError(track_type, valid_track_types)
    try:
        file_service = FileService()
        song_dir = file_service.get_song_directory(song_id)
        logger.info(f"LIBRARY_DIR: {file_service.base_library_dir}")
        logger.info(f"Looking for track at: {song_dir / f'{track_type}.mp3'}")
        if not song_dir.is_dir():
            logger.warning(f"Song directory not found: {song_dir}")
            raise ResourceNotFoundError("Song", song_id)
        track_file: Optional[Path] = song_dir / f"{track_type}.mp3"
        if not (track_file and track_file.is_file()):
            logger.warning(f"Track file not found: {track_file}")
            raise FileOperationError(
                "locate",
                str(track_file),
                f"{track_type.capitalize()} track not found for this song",
            )

        config = get_config()
        library_base_path = config.LIBRARY_DIR.resolve()
        file_path_resolved = track_file.resolve()
        logger.info(f"Resolved track file path: {file_path_resolved}")
        logger.info(f"Library base path: {library_base_path}")
        if library_base_path not in file_path_resolved.parents:
            logger.error(f"Attempted download outside library bounds: {track_file}")
            raise ValidationError(
                "Access denied - file outside library bounds", "SECURITY_VIOLATION"
            )
        logger.info(f"Sending {track_type}.mp3 from directory '{song_dir}'")
        return send_from_directory(
            song_dir,
            track_file.name,
            as_attachment=True,
        )
    except (
        ResourceNotFoundError,
        InvalidTrackTypeError,
        FileOperationError,
        ValidationError,
    ):
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during download for song '{song_id}', track '{track_type}': {e}",
            exc_info=True,
        )
        raise FileOperationError(
            "download",
            f"{song_id}/{track_type}.mp3",
            f"Internal error during file operation: {str(e)}",
        )
