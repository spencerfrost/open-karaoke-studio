# backend/app/api/songs.py

import logging
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from flask import Blueprint, jsonify, request, send_from_directory

from ..config import get_config

# Import database and models directly - no fake service layer
from ..db.song_operations import create_or_update_song
from ..db.song_operations import delete_song as db_delete_song
from ..db.song_operations import get_song
from ..exceptions import (
    DatabaseError,
    FileOperationError,
    InvalidTrackTypeError,
    NetworkError,
    ResourceNotFoundError,
    ServiceError,
    ValidationError,
)
from ..schemas.requests import CreateSongRequest
from ..services import FileService
from ..services.lyrics_service import LyricsService
from ..utils.error_handlers import handle_api_error
from ..utils.validation import validate_json_request, validate_path_params

logger = logging.getLogger(__name__)
song_bp = Blueprint("songs", __name__, url_prefix="/api/songs")


@song_bp.route("/metadata/auto", methods=["POST"])
@handle_api_error
def auto_save_itunes_metadata() -> tuple:
    """
    Accepts artist, title, album, and song_id. Fetches iTunes metadata and saves the first result to the song. Returns only success/failure JSON.
    """
    from ..db.song_operations import get_song, update_song_with_metadata
    from ..services.metadata_service import MetadataService

    data = request.get_json()
    artist = data.get("artist")
    title = data.get("title")
    album = data.get("album")
    song_id = data.get("song_id")
    if not (artist and title and song_id):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Missing required fields: artist, title, song_id",
                }
            ),
            400,
        )
    try:
        metadata_service = MetadataService()
        results = metadata_service.search_metadata(
            artist=artist, title=title, album=album, limit=1
        )
        if not results:
            logger.warning(f"No iTunes metadata found for {artist} - {title} - {album}")
            return jsonify({"success": False, "error": "No iTunes metadata found"}), 404
        # Get the song from DB
        song = get_song(song_id)
        if not song:
            logger.error(f"Song not found: {song_id}")
            return jsonify({"success": False, "error": "Song not found"}), 404
        # Update song with new metadata (using DB model)
        for k, v in results[0].items():
            if hasattr(song, k):
                setattr(song, k, v)
        success = update_song_with_metadata(song_id, song)
        if not success:
            logger.error(f"Failed to update song metadata for {song_id}")
            return (
                jsonify({"success": False, "error": "Failed to update song metadata"}),
                500,
            )
        logger.info(f"Auto-saved iTunes metadata for song {song_id}")
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Failed to auto-save iTunes metadata: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@song_bp.route("", methods=["GET"])
@handle_api_error
def get_songs():
    """
    Endpoint to get a list of processed songs with metadata.
    Supports query params: limit, offset, sort_by, direction.
    """
    logger.info("Received request for /api/songs")

    try:
        from flask import request

        from ..db.database import get_db_session
        from ..db.models import DbSong

        # Query params
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int, default=0)
        sort_by = request.args.get("sort_by", default="date_added")
        direction = request.args.get("direction", default="desc").lower()

        # Validate sort_by
        valid_sort_fields = {"date_added", "title", "artist", "album", "year"}
        if sort_by not in valid_sort_fields:
            sort_by = "date_added"

        # Build query
        with get_db_session() as session:
            base_query = session.query(DbSong)
            sort_column = getattr(DbSong, sort_by, DbSong.date_added)
            if direction == "asc":
                base_query = base_query.order_by(sort_column.asc())
            else:
                base_query = base_query.order_by(sort_column.desc())
            if offset:
                base_query = base_query.offset(offset)
            if limit:
                base_query = base_query.limit(limit)
            songs = base_query.all()
            response_data = [song.to_dict() for song in songs]

        logger.info("Returning %s songs.", len(response_data))
        return jsonify(response_data)

    except ConnectionError as e:
        # Database connection issues
        logger.error(
            "Database connection failed retrieving songs: %s", e, exc_info=True
        )
        raise DatabaseError(
            "Database connection failed while retrieving songs",
            "DATABASE_CONNECTION_ERROR",
            {"operation": "select_songs", "error": str(e)},
        )
    except Exception as e:
        # Unexpected database or serialization errors
        logger.error("Unexpected error retrieving songs: %s", e, exc_info=True)
        raise DatabaseError(
            "Unexpected error retrieving songs from database",
            "DATABASE_QUERY_ERROR",
            {"operation": "select_songs", "table": "songs", "error": str(e)},
        )


@song_bp.route("/<string:song_id>/download/<string:track_type>", methods=["GET"])
@handle_api_error
@validate_path_params(song_id=str, track_type=str)
def download_song_track(song_id: str, track_type: str):
    """Downloads a specific track type (vocals, instrumental, original) for a song."""
    logger.info("Download request for song '%s', track type '%s'", song_id, track_type)
    track_type = track_type.lower()  # Normalize track type

    # Validate track type first
    valid_track_types = ["vocals", "instrumental", "original"]
    if track_type not in valid_track_types:
        raise InvalidTrackTypeError(track_type, valid_track_types)

    try:
        file_service = FileService()
        song_dir = file_service.get_song_directory(song_id)

        if not song_dir.is_dir():
            raise ResourceNotFoundError("Song", song_id)

        track_file: Optional[Path] = song_dir / f"{track_type}.mp3"

        if not (track_file and track_file.is_file()):
            raise FileOperationError(
                "locate",
                str(track_file),
                f"{track_type.capitalize()} track not found for this song",
            )

        # Security Check: Ensure the file is within the base library directory
        config = get_config()
        library_base_path = config.LIBRARY_DIR.resolve()
        file_path_resolved = track_file.resolve()

        if library_base_path not in file_path_resolved.parents:
            logger.error("Attempted download outside library bounds: %s", track_file)
            raise ValidationError(
                "Access denied - file outside library bounds", "SECURITY_VIOLATION"
            )

        logger.info("Sending %s.mp3 from directory '%s'", track_type, song_dir)
        return send_from_directory(
            song_dir,  # Directory path object
            track_file.name,  # Just the filename string
            as_attachment=True,  # Trigger browser download prompt
        )

    except (
        ResourceNotFoundError,
        InvalidTrackTypeError,
        FileOperationError,
        ValidationError,
    ):
        # Re-raise our custom exceptions - they'll be handled by the error handlers
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


@song_bp.route("/<string:song_id>", methods=["GET"])
@handle_api_error
def get_song_details(song_id: str):
    """Endpoint to get details for a specific song - direct database access."""
    logger.info("Received request for song details: %s", song_id)

    try:
        # Get song directly from database
        db_song = get_song(song_id)

        if not db_song:
            raise ResourceNotFoundError("Song", song_id)

        # Convert to Pydantic response format using our new pattern
        from ..schemas.song import Song

        song = Song.model_validate(db_song.to_dict())
        response = song.model_dump(mode="json")

        logger.info("Returning details for song %s", song_id)
        return jsonify(response), 200

    except ServiceError:
        raise  # Let error handlers deal with it
    except ConnectionError as e:
        raise DatabaseError(
            "Database connection failed while fetching song details",
            "DATABASE_CONNECTION_ERROR",
            {"song_id": song_id, "error": str(e)},
        )
    except Exception as e:
        raise DatabaseError(
            "Unexpected error fetching song details",
            "SONG_DETAILS_ERROR",
            {"song_id": song_id, "error": str(e)},
        )


@song_bp.route("/<string:song_id>/thumbnail.<string:extension>", methods=["GET"])
@handle_api_error
def get_thumbnail(song_id: str, extension: str):
    """Serve the thumbnail image for a song."""
    import os

    from flask import send_file

    # Decode the song ID to handle URL-encoded characters
    song_id = unquote(song_id)

    # Validate extension
    allowed_extensions = {"jpg", "jpeg", "png", "webp"}
    if extension.lower() not in allowed_extensions:
        raise ValidationError(
            f"Invalid image format: {extension}. Allowed: {', '.join(allowed_extensions)}",
            "INVALID_IMAGE_FORMAT",
        )

    # Get song from database to find thumbnail path
    db_song = get_song(song_id)
    if not db_song:
        raise ResourceNotFoundError("Song", song_id)

    # Construct the path to the thumbnail
    file_service = FileService()
    song_dir = file_service.get_song_directory(song_id)
    thumbnail_path = song_dir / f"thumbnail.{extension}"

    if not thumbnail_path.exists():
        raise ResourceNotFoundError(
            "Thumbnail image", f"{song_id}/thumbnail.{extension}"
        )

    if not os.access(thumbnail_path, os.R_OK):
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
        raise ResourceNotFoundError(
            "Thumbnail image", f"{song_id}/thumbnail.{extension}"
        )
    except PermissionError as e:
        raise FileOperationError(
            "serve",
            str(thumbnail_path),
            f"Permission denied accessing thumbnail: {str(e)}",
        )
    except Exception as e:
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
    db_song = get_song(song_id)
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


# Backward compatibility route
@song_bp.route("/<string:song_id>/thumbnail.jpg", methods=["GET"])
def get_thumbnail_jpg_compat(song_id: str):
    """Legacy endpoint for thumbnail.jpg - redirects to auto-detection."""
    return get_thumbnail_auto(song_id)


@song_bp.route("/<string:song_id>/lyrics", methods=["GET"])
@handle_api_error
def get_song_lyrics(song_id: str):
    """Fetch synchronized or plain lyrics for a song using LRCLIB."""
    logger.info("Received lyrics request for song %s", song_id)

    try:
        lyrics_service = LyricsService()

        # Check if we have lyrics stored locally first
        stored_lyrics = lyrics_service.get_lyrics(song_id)
        if stored_lyrics:
            logger.info("Returning stored lyrics for song %s", song_id)
            return jsonify({"plainLyrics": stored_lyrics}), 200

        # Get song from database only
        db_song = get_song(song_id)
        if not db_song:
            raise ResourceNotFoundError("Song", song_id)

        # Use to_dict() method for consistent field conversion
        song_data = db_song.to_dict()
        title = song_data["title"]
        artist = (
            song_data["artist"]
            if song_data["artist"].lower() != "unknown artist"
            else song_data["channel"]
        )
        album = song_data["album"]

        # If missing essential info, return error
        if not title or not artist:
            raise ValidationError(
                "Missing essential info for lyrics lookup", "MISSING_METADATA"
            )

        # Search for lyrics using the service
        query_parts = [artist, title]
        if album:
            query_parts.append(album)

        query = " ".join(query_parts)
        results = lyrics_service.search_lyrics(query)

        if results:
            # Take the first result (best match)
            lyrics_data = results[0]
            logger.info("Found lyrics for %s", song_id)

            # Optionally save the lyrics locally for future use
            if lyrics_data.get("plainLyrics"):
                try:
                    lyrics_service.save_lyrics(song_id, lyrics_data["plainLyrics"])
                except OSError as e:
                    logger.warning(
                        "Failed to save lyrics locally (file system error): %s", e
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to save lyrics locally (unexpected error): %s", e
                    )

            return jsonify(lyrics_data), 200
        else:
            logger.info("No lyrics found for %s", song_id)
            raise ResourceNotFoundError("Lyrics", song_id)

    except ServiceError:
        raise  # Let error handlers deal with it
    except ConnectionError as e:
        raise NetworkError(
            "Failed to connect to lyrics service",
            "LYRICS_CONNECTION_ERROR",
            {"song_id": song_id, "error": str(e)},
        )
    except TimeoutError as e:
        raise NetworkError(
            "Lyrics service request timed out",
            "LYRICS_TIMEOUT_ERROR",
            {"song_id": song_id, "error": str(e)},
        )
    except Exception as e:
        raise ServiceError(
            "Unexpected error fetching lyrics",
            "LYRICS_FETCH_ERROR",
            {"song_id": song_id, "error": str(e)},
        )


@song_bp.route("/<string:song_id>", methods=["DELETE"])
@handle_api_error
def delete_song(song_id: str):
    """Endpoint to delete a song by its ID - direct database access."""
    logger.info("Received request to delete song: %s", song_id)

    try:
        # Check if song exists first
        db_song = get_song(song_id)
        if not db_song:
            raise ResourceNotFoundError("Song", song_id)

        # Delete song from database
        success = db_delete_song(song_id)
        if not success:
            raise DatabaseError(
                "Failed to delete song from database",
                "SONG_DELETE_ERROR",
                {"song_id": song_id},
            )

        # Also delete files using FileService
        file_service = FileService()
        file_service.delete_song_files(song_id)

        logger.info("Successfully deleted song: %s", song_id)
        return jsonify({"message": "Song deleted successfully"}), 200

    except ServiceError:
        raise  # Let error handlers deal with it
    except ConnectionError as e:
        raise DatabaseError(
            "Database connection failed during song deletion",
            "DATABASE_CONNECTION_ERROR",
            {"song_id": song_id, "error": str(e)},
        )
    except OSError as e:
        # File deletion errors
        raise FileOperationError(
            "delete", f"{song_id}/*", f"Failed to delete song files: {str(e)}"
        )
    except Exception as e:
        raise DatabaseError(
            "Unexpected error deleting song",
            "SONG_DELETE_ERROR",
            {"song_id": song_id, "error": str(e)},
        )


@song_bp.route("", methods=["POST"])
@handle_api_error
@validate_json_request(CreateSongRequest)
def create_song(validated_data: CreateSongRequest):
    """Create a new song with basic information - thin controller using service layer."""
    logger.info("Received request to create a new song")

    # Generate a unique ID for the song
    song_id = str(uuid.uuid4())
    logger.info("Creating new song with ID: %s", song_id)

    try:
        # Create song directly using create_or_update_song with validated data
        song = create_or_update_song(
            song_id=song_id,
            title=validated_data.title,
            artist=validated_data.artist,
            album=validated_data.album,
            duration_ms=validated_data.duration_ms,
            source=validated_data.source,
            video_id=validated_data.video_id,
        )

        if not song:
            raise DatabaseError(
                f"Failed to create song {song_id} in database",
                "SONG_CREATION_FAILED",
                {"song_id": song_id},
            )

        # Create the song directory
        try:
            from ..services.file_service import FileService

            file_service = FileService()
            song_dir = file_service.get_song_directory(song_id)
            song_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Created directory for song: %s", song_dir)
        except OSError as e:
            logger.warning(
                "File system error creating directory for song %s: %s", song_id, e
            )
            # Continue even if directory creation fails - we'll try again during processing
        except Exception as e:
            logger.warning(
                "Unexpected error creating directory for song %s: %s", song_id, e
            )
            # Continue even if directory creation fails - we'll try again during processing

        # Return the song data using the model's to_dict method
        response = song.to_dict()
        # Override status to pending for newly created songs
        response["status"] = "pending"

        logger.info("Successfully created song: %s", song_id)
        return jsonify(response), 201

    except DatabaseError:
        raise
    except ConnectionError as e:
        raise DatabaseError(
            "Database connection failed during song creation",
            "DATABASE_CONNECTION_ERROR",
            {"song_id": song_id, "error": str(e)},
        )
    except Exception as e:
        logger.error("Unexpected error creating song: %s", e, exc_info=True)
        raise ServiceError(
            "Unexpected error creating song",
            "SONG_CREATION_ERROR",
            {"song_id": song_id, "original_error": str(e)},
        )


@song_bp.route("/<string:song_id>", methods=["PATCH"])
@handle_api_error
def update_song(song_id: str):
    """Update a song with any provided fields - generic update endpoint."""
    logger.info("Received request to update song %s", song_id)

    try:
        # Get request data
        data = request.get_json()
        if not data:
            raise ValidationError("No data provided", "MISSING_REQUEST_DATA")

        # Get existing song from database first
        db_song = get_song(song_id)
        if not db_song:
            raise ResourceNotFoundError("Song", song_id)

        # Update song directly in database using only the provided fields
        updated_song = create_or_update_song(
            song_id=song_id,
            title=data.get("title", db_song.title),
            artist=data.get("artist", db_song.artist),
            album=data.get("album", db_song.album),
            genre=data.get("genre", db_song.genre),
            language=data.get("language", db_song.language),
            lyrics=data.get("lyrics", db_song.lyrics),
            synced_lyrics=data.get("syncedLyrics", db_song.synced_lyrics),
            favorite=data.get("favorite", db_song.favorite),
        )

        if not updated_song:
            raise DatabaseError(
                "Failed to update song metadata",
                "SONG_UPDATE_ERROR",
                {"song_id": song_id},
            )

        # Return updated song details
        return get_song_details(song_id)

    except (ValidationError, ResourceNotFoundError, DatabaseError):
        raise  # Let error handlers deal with it
    except ConnectionError as e:
        raise DatabaseError(
            "Database connection failed during song update",
            "DATABASE_CONNECTION_ERROR",
            {"song_id": song_id, "error": str(e)},
        )
    except Exception as e:
        raise DatabaseError(
            "Unexpected error updating song",
            "SONG_UPDATE_ERROR",
            {"song_id": song_id, "error": str(e)},
        )


@song_bp.route("/<string:song_id>/cover.<string:extension>", methods=["GET"])
@handle_api_error
def get_cover_art(song_id: str, extension: str):
    """Serve the cover art image for a song."""
    import os

    from flask import send_file

    # Decode the song ID to handle URL-encoded characters
    song_id = unquote(song_id)

    # Validate extension
    allowed_extensions = {"jpg", "jpeg", "png", "webp"}
    if extension.lower() not in allowed_extensions:
        raise ValidationError(
            f"Invalid image format: {extension}. Allowed: {', '.join(allowed_extensions)}",
            "INVALID_IMAGE_FORMAT",
        )

    # Construct the path to the cover art
    file_service = FileService()
    song_dir = file_service.get_song_directory(song_id)
    cover_art_path = song_dir / f"cover.{extension}"

    if not cover_art_path.exists():
        raise ResourceNotFoundError("Cover art", f"{song_id}/cover.{extension}")

    if not os.access(cover_art_path, os.R_OK):
        raise FileOperationError("read", str(cover_art_path), "File is not readable")

    # Determine correct mimetype based on extension
    mimetype_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }
    mimetype = mimetype_map.get(extension.lower(), "image/jpeg")

    try:
        return send_file(cover_art_path, mimetype=mimetype)
    except FileNotFoundError as e:
        raise ResourceNotFoundError("Cover art", f"{song_id}/cover.{extension}")
    except PermissionError as e:
        raise FileOperationError(
            "serve",
            str(cover_art_path),
            f"Permission denied accessing cover art: {str(e)}",
        )
    except Exception as e:
        raise FileOperationError(
            "serve",
            str(cover_art_path),
            f"Unexpected error serving cover art: {str(e)}",
        )


@song_bp.route("/<string:song_id>/cover", methods=["GET"])
@handle_api_error
def get_cover_art_auto(song_id: str):
    """Serve the cover art image for a song, auto-detecting format."""
    import os

    from flask import send_file

    # Decode the song ID to handle URL-encoded characters
    song_id = unquote(song_id)

    # Construct the path to the cover art
    file_service = FileService()
    song_dir = file_service.get_song_directory(song_id)

    # Try different formats in order of preference
    formats_to_try = [
        ("webp", "image/webp"),  # Best quality/compression
        ("jpg", "image/jpeg"),  # Most common
        ("jpeg", "image/jpeg"),  # Alternative JPEG extension
        ("png", "image/png"),  # High quality
    ]

    for ext, mimetype in formats_to_try:
        cover_art_path = song_dir / f"cover.{ext}"
        if cover_art_path.exists() and os.access(cover_art_path, os.R_OK):
            try:
                return send_file(cover_art_path, mimetype=mimetype)
            except FileNotFoundError:
                logger.warning("Cover art file disappeared: %s", cover_art_path)
                continue  # Try next format
            except PermissionError as e:
                logger.warning(
                    "Permission denied accessing cover art %s: %s", cover_art_path, e
                )
                continue  # Try next format
            except Exception as e:
                logger.warning("Failed to serve cover art %s: %s", cover_art_path, e)
                continue  # Try next format

    raise ResourceNotFoundError("Cover art", f"{song_id}/cover.*")
