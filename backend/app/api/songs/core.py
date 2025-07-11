"""Songs API Core Module"""

import uuid

from app.db.database import get_db_session
from app.exceptions import (
    DatabaseError,
    FileOperationError,
    ResourceNotFoundError,
    ServiceError,
    ValidationError,
)
from app.repositories.song_repository import SongRepository
from app.schemas.requests import CreateSongRequest, UpdateSongRequest
from app.schemas.song import Song
from app.services.file_service import FileService
from app.utils.error_handlers import handle_api_error
from app.utils.validation import validate_json_request
from flask import jsonify, request

from . import logger, song_bp


@song_bp.route("", methods=["GET"])
@handle_api_error
def get_songs():
    """
    Endpoint to get a list of processed songs with metadata.
    Supports query params: limit, offset, sort_by, direction.
    """
    logger.info("Received request for /api/songs")

    try:

        # Query params
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int, default=0)
        sort_by = request.args.get("sort_by", default="date_added")
        direction = request.args.get("direction", default="desc").lower()

        # Validate sort_by
        valid_sort_fields = {"date_added", "title", "artist", "album", "year"}
        if sort_by not in valid_sort_fields:
            sort_by = "date_added"

        with get_db_session() as session:
            repo = SongRepository(session)
            # Build filters dict if needed (currently none)
            songs = repo.fetch_all(
                sort_by=sort_by,
                direction=direction,
                limit=limit,
                offset=offset
            )
            response_data = [song.to_dict() for song in songs]

        logger.info("Returning %s songs.", len(response_data))
        return jsonify(response_data)

    except ConnectionError as e:
        logger.error(
            "Database connection failed retrieving songs: %s", e, exc_info=True
        )
        raise DatabaseError(
            "Database connection failed while retrieving songs",
            "DATABASE_CONNECTION_ERROR",
            {"operation": "select_songs", "error": str(e)},
        ) from e
    except Exception as e:
        logger.error("Unexpected error retrieving songs: %s", e, exc_info=True)
        raise DatabaseError(
            "Unexpected error retrieving songs from database",
            "DATABASE_QUERY_ERROR",
            {"operation": "select_songs", "table": "songs", "error": str(e)},
        ) from e


@song_bp.route("/<string:song_id>", methods=["GET"])
@handle_api_error
def get_song_details(song_id: str):
    """Endpoint to get details for a specific song - direct database access."""
    logger.info("Received request for song details: %s", song_id)

    try:
        # Get song directly from database
        with get_db_session() as session:
            repo = SongRepository(session)
            db_song = repo.fetch(song_id)
        if not db_song:
            raise ResourceNotFoundError("Song", song_id)

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
        ) from e
    except Exception as e:
        raise DatabaseError(
            "Unexpected error fetching song details",
            "SONG_DETAILS_ERROR",
            {"song_id": song_id, "error": str(e)},
        ) from e


@song_bp.route("/<string:song_id>", methods=["DELETE"])
@handle_api_error
def delete_song(song_id: str):
    """Endpoint to delete a song by its ID using SongRepository."""
    logger.info("Received request to delete song: %s", song_id)

    try:
        with get_db_session() as session:
            repo = SongRepository(session)
            db_song = repo.fetch(song_id)
            if not db_song:
                raise ResourceNotFoundError("Song", song_id)
            success = repo.delete(song_id)
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
        ) from e
    except OSError as e:
        # File deletion errors
        raise FileOperationError(
            "delete", f"{song_id}/*", f"Failed to delete song files: {str(e)}"
        ) from e
    except Exception as e:
        raise DatabaseError(
            "Unexpected error deleting song",
            "SONG_DELETE_ERROR",
            {"song_id": song_id, "error": str(e)},
        ) from e


@song_bp.route("", methods=["POST"])
@handle_api_error
@validate_json_request(CreateSongRequest)
def create_song(validated_data: CreateSongRequest):
    """Create a new song with basic information - thin controller using service layer."""
    logger.info("Received request to create a new song")

    # Use provided ID if present, else generate a new one
    song_id = getattr(validated_data, "id", None) or str(uuid.uuid4())
    logger.info("Creating new song with ID: %s", song_id)

    try:
        # Create song using SongRepository
        with get_db_session() as session:
            repo = SongRepository(session)
            song_data = {
                "id": song_id,
                "title": validated_data.title,
                "artist": validated_data.artist,
                "album": validated_data.album,
                "duration_ms": validated_data.durationMs,
                "source": validated_data.source,
                "video_id": validated_data.video_id,
            }
            song = repo.create(song_data)

        if not song:
            raise DatabaseError(
                f"Failed to create song {song_id} in database",
                "SONG_CREATION_FAILED",
                {"song_id": song_id},
            )

        # Create the song directory
        try:
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
        ) from e
    except Exception as e:
        logger.error("Unexpected error creating song: %s", e, exc_info=True)
        raise ServiceError(
            "Unexpected error creating song",
            "SONG_CREATION_ERROR",
            {"song_id": song_id, "original_error": str(e)},
        ) from e


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

        # Validate using UpdateSongRequest
        try:
            validated = UpdateSongRequest(**data)
        except Exception as e:
            raise ValidationError(str(e), "INVALID_UPDATE_DATA") from e

        with get_db_session() as session:
            repo = SongRepository(session)
            db_song = repo.fetch(song_id)
            if not db_song:
                raise ResourceNotFoundError("Song", song_id)
            # Only update provided fields
            update_fields = {}
            for field in [
                "title",
                "artist",
                "album",
                "genre",
                "language",
                "plain_lyrics",
                "synced_lyrics",
                "durationMs",
            ]:
                # Map camelCase to snake_case for synced_lyrics and durationMs
                if field == "synced_lyrics":
                    val = data.get("syncedLyrics", getattr(db_song, field))
                elif field == "plain_lyrics":
                    val = data.get("plainLyrics", getattr(db_song, field))
                elif field == "durationMs":
                    val = data.get("durationMs", getattr(db_song, "duration_ms", None))
                    # Validation already done by pydantic
                    if val is not None:
                        update_fields["duration_ms"] = val
                    continue
                else:
                    val = data.get(field, getattr(db_song, field))
                update_fields[field] = val
            updated_song = repo.update(song_id, **update_fields)
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
        ) from e
    except Exception as e:
        raise DatabaseError(
            "Unexpected error updating song",
            "SONG_UPDATE_ERROR",
            {"song_id": song_id, "error": str(e)},
        ) from e
