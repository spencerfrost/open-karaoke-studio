# backend/app/api/songs.py

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from flask import Blueprint, current_app, jsonify, request, send_from_directory

from ..config import get_config

# Import database and models directly - no fake service layer
from ..db.models import DbSong
from ..db.song_operations import get_song, create_or_update_song
from ..db.song_operations import delete_song as db_delete_song
from ..exceptions import ServiceError
from ..services import FileService, file_management
from ..services.lyrics_service import LyricsService

logger = logging.getLogger(__name__)
song_bp = Blueprint("songs", __name__, url_prefix="/api/songs")


@song_bp.route("", methods=["GET"])
def get_songs():
    """
    Endpoint to get a list of processed songs with metadata
    - direct database access, no fake service layer.
    """
    logger.info("Received request for /api/songs")

    try:
        from ..db.models import DbSong
        from ..db.database import get_db_session

        with get_db_session() as session:
            songs = session.query(DbSong).order_by(DbSong.date_added.desc()).all()

            # Convert to API response format
            response_data = [song.to_dict() for song in songs]

        logger.info("Returning %s songs.", len(response_data))
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Unexpected error in get_songs: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@song_bp.route("/<string:song_id>/download/<string:track_type>", methods=["GET"])
def download_song_track(song_id: str, track_type: str):
    """Downloads a specific track type (vocals, instrumental, original) for a song."""
    logger.info("Download request for song '%s', track type '%s'", song_id, track_type)
    track_type = track_type.lower()  # Normalize track type

    if track_type not in ("vocals", "instrumental", "original"):
        logger.warning("Invalid track type requested: %s", track_type)
        return (
            jsonify(
                {
                    "error": (
                        "Invalid track type specified. "
                        "Use 'vocals', 'instrumental', or 'original'."
                    )
                }
            ),
            400,
        )

    try:
        file_service = FileService()
        song_dir = file_service.get_song_directory(song_id)
        if not song_dir.is_dir():
            logger.error("Song directory not found: %s", song_dir)
            return jsonify({"error": "Song not found"}), 404

        track_file: Optional[Path] = song_dir / f"{track_type}.mp3"

        if track_file and track_file.is_file():
            # Security Check: Ensure the file is within the base library directory
            config = get_config()
            library_base_path = config.LIBRARY_DIR.resolve()
            file_path_resolved = track_file.resolve()

            if library_base_path not in file_path_resolved.parents:
                logger.error(
                    "Attempted download outside library bounds: %s", track_file
                )
                return jsonify({"error": "Access denied"}), 403

            logger.info("Sending %s.mp3 from directory '%s'", track_type, song_dir)
            return send_from_directory(
                song_dir,  # Directory path object
                track_file.name,  # Just the filename string - use .name to get just the filename
                as_attachment=True,  # Trigger browser download prompt
            )
        else:
            logger.error("Track file not found: %s", track_file)
            return (
                jsonify(
                    {
                        "error": f"{track_type.capitalize()} track not found for this song"
                    }
                ),
                404,
            )

    except Exception as e:
        logger.error(
            f"Error during download for song '{song_id}', track '{track_type}': {e}",
            exc_info=True,
        )
        # Use exc_info=True in logger to include traceback
        return jsonify({"error": "An internal error occurred during download."}), 500


@song_bp.route("/<string:song_id>", methods=["GET"])
def get_song_details(song_id: str):
    """Endpoint to get details for a specific song - direct database access."""
    logger.info("Received request for song details: %s", song_id)

    try:
        # Get song directly from database
        db_song = get_song(song_id)

        if not db_song:
            return jsonify({"error": f"Song with ID {song_id} not found"}), 404

        # Convert to Pydantic response format using our new pattern
        from ..schemas.song import Song

        song = Song.model_validate(db_song.to_dict())
        response = song.model_dump(mode="json")

        logger.info("Returning details for song %s", song_id)
        return jsonify(response), 200

    except ServiceError as e:
        logger.error("Service error getting song %s: %s", song_id, e)
        return jsonify({"error": "Failed to fetch song", "details": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error getting song {song_id}: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@song_bp.route("/<string:song_id>/thumbnail.<string:extension>", methods=["GET"])
def get_thumbnail(song_id: str, extension: str):
    """Serve the thumbnail image for a song."""
    import os

    from flask import send_file

    # Decode the song ID to handle URL-encoded characters
    song_id = unquote(song_id)

    # Validate extension
    allowed_extensions = {"jpg", "jpeg", "png", "webp"}
    if extension.lower() not in allowed_extensions:
        return jsonify({"error": "Invalid image format"}), 400

    # Get song from database to find thumbnail path
    get_song(song_id)

    # Construct the path to the thumbnail
    file_service = FileService()
    song_dir = file_service.get_song_directory(song_id)
    thumbnail_path = song_dir / f"thumbnail.{extension}"

    if not thumbnail_path.exists():
        return jsonify({"error": "Thumbnail not found"}), 404

    if not os.access(thumbnail_path, os.R_OK):
        return jsonify({"error": "Thumbnail is not readable"}), 403

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
    except Exception:
        return (
            jsonify(
                {"error": "An internal error occurred while serving the thumbnail."}
            ),
            500,
        )


@song_bp.route("/<string:song_id>/thumbnail", methods=["GET"])
def get_thumbnail_auto(song_id: str):
    """Serve the thumbnail image for a song, auto-detecting format."""
    import os

    from flask import send_file

    # Decode the song ID to handle URL-encoded characters
    song_id = unquote(song_id)

    # Get song from database to find thumbnail path
    get_song(song_id)

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
            except Exception:
                continue  # Try next format

    return jsonify({"error": "Thumbnail not found"}), 404


# Backward compatibility route
@song_bp.route("/<string:song_id>/thumbnail.jpg", methods=["GET"])
def get_thumbnail_jpg_compat(song_id: str):
    """Legacy endpoint for thumbnail.jpg - redirects to auto-detection."""
    return get_thumbnail_auto(song_id)


@song_bp.route("/<string:song_id>/lyrics", methods=["GET"])
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

        # Try to get from database first
        db_song = get_song(song_id)

        if db_song:
            # Use to_dict() method for consistent field conversion
            song_data = db_song.to_dict()
            title = song_data["title"]
            artist = (
                song_data["artist"]
                if song_data["artist"].lower() != "unknown artist"
                else song_data["channel"]
            )
            album = song_data["album"]
        else:
            # Fall back to file-based approach
            metadata = file_management.read_song_metadata(song_id)
            if not metadata or not metadata.title:
                logger.warning("Metadata incomplete for lyrics: %s", song_id)
                return (
                    jsonify({"error": "Missing metadata (title) for lyrics lookup"}),
                    400,
                )

            # Determine best artist name: prefer metadata.artist, else channel
            artist = (
                metadata.artist
                if metadata.artist and metadata.artist.lower() != "unknown artist"
                else metadata.channel
            )
            if not artist:
                logger.warning("Artist unknown for lyrics: %s", song_id)
                return jsonify({"error": "Missing artist name for lyrics lookup"}), 400

            title = metadata.title
            album = metadata.releaseTitle

        # If missing essential info, return error
        if not title or not artist:
            return jsonify({"error": "Missing essential info for lyrics lookup"}), 400

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
                except Exception as e:
                    logger.warning("Failed to save lyrics locally: %s", e)

            return jsonify(lyrics_data), 200
        else:
            logger.info("No lyrics found for %s", song_id)
            return jsonify({"error": "No lyrics found"}), 404

    except ServiceError as e:
        logger.error("Service error getting lyrics for %s: %s", song_id, e)
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error("Unexpected error getting lyrics for %s: %s", song_id, e)
        return jsonify({"error": "Failed to fetch lyrics"}), 500


@song_bp.route("/<string:song_id>", methods=["DELETE"])
def delete_song(song_id: str):
    """Endpoint to delete a song by its ID - direct database access."""
    logger.info("Received request to delete song: %s", song_id)

    try:
        # Check if song exists first
        db_song = get_song(song_id)
        if not db_song:
            return jsonify({"error": "Song not found"}), 404

        # Delete song from database
        success = db_delete_song(song_id)
        if not success:
            return jsonify({"error": "Failed to delete song from database"}), 500

        # Also delete files using FileService
        file_service = FileService()
        file_service.delete_song_files(song_id)

        logger.info("Successfully deleted song: %s", song_id)
        return jsonify({"message": "Song deleted successfully"}), 200

    except ServiceError as e:
        logger.error("Service error deleting song %s: %s", song_id, e)
        return jsonify({"error": "Failed to delete song", "details": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error deleting song {song_id}: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@song_bp.route("", methods=["POST"])
def create_song():
    """Create a new song with basic information - thin controller using service layer."""
    logger.info("Received request to create a new song")

    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        if not data.get("title"):
            return jsonify({"error": "Song title is required"}), 400

        # Generate a unique ID for the song
        song_id = str(uuid.uuid4())
        logger.info("Creating new song with ID: %s", song_id)

        # Create song directly using create_or_update_song
        song = create_or_update_song(
            song_id=song_id,
            title=data.get("title"),
            artist=data.get("artist", "Unknown Artist"),
            source=data.get("source"),
            source_url=data.get("sourceUrl"),
            video_id=data.get("videoId"),
            uploader=data.get("uploader"),
            uploader_id=data.get("uploaderId"),
            channel=data.get("channel"),
            channel_id=data.get("channelId"),
            album=data.get("album"),
            genre=data.get("genre"),
            language=data.get("language"),
        )
        if not song:
            logger.error("Failed to create song %s in database", song_id)
            return jsonify({"error": "Failed to create song in database"}), 500

        # Create the song directory
        try:
            from ..services.file_service import FileService

            file_service = FileService()
            song_dir = file_service.get_song_directory(song_id)
            song_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Created directory for song: %s", song_dir)
        except Exception as e:
            logger.error("Error creating directory for song %s: %s", song_id, e)
            # Continue even if directory creation fails - we'll try again during processing

        # Return the song data using the model's to_dict method
        response = song.to_dict()
        # Override status to pending for newly created songs
        response["status"] = "pending"

        logger.info("Successfully created song: %s", song_id)
        return jsonify(response), 201

    except ServiceError as e:
        logger.error("Service error creating song: %s", e)
        return jsonify({"error": "Failed to create song", "details": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error creating song: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@song_bp.route("/<string:song_id>", methods=["PATCH"])
def update_song(song_id: str):
    """Update a song with any provided fields - generic update endpoint."""
    logger.info("Received request to update song %s", song_id)

    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Get existing song from database first
        db_song = get_song(song_id)
        if not db_song:
            return jsonify({"error": "Song not found"}), 404

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
            return jsonify({"error": "Failed to update song metadata"}), 500

        # Return updated song details
        return get_song_details(song_id)

    except Exception as e:
        logger.error(f"Unexpected error updating song {song_id}: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@song_bp.route("/<string:song_id>/cover.<string:extension>", methods=["GET"])
def get_cover_art(song_id: str, extension: str):
    """Serve the cover art image for a song."""
    import os

    from flask import send_file

    # Decode the song ID to handle URL-encoded characters
    song_id = unquote(song_id)

    # Validate extension
    allowed_extensions = {"jpg", "jpeg", "png", "webp"}
    if extension.lower() not in allowed_extensions:
        return jsonify({"error": "Invalid image format"}), 400

    # Construct the path to the cover art
    file_service = FileService()
    song_dir = file_service.get_song_directory(song_id)
    cover_art_path = song_dir / f"cover.{extension}"

    if not cover_art_path.exists():
        return jsonify({"error": "Cover art not found"}), 404

    if not os.access(cover_art_path, os.R_OK):
        return jsonify({"error": "Cover art is not readable"}), 403

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
    except Exception:
        return (
            jsonify(
                {"error": "An internal error occurred while serving the cover art."}
            ),
            500,
        )


@song_bp.route("/<string:song_id>/cover", methods=["GET"])
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
            except Exception:
                continue  # Try next format

    return jsonify({"error": "Cover art not found"}), 404
