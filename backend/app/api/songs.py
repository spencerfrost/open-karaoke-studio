# backend/app/api/songs.py

import logging
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from flask import Blueprint, jsonify, request, send_from_directory

from app.schemas.requests import UpdateSongRequest
from app.schemas.song import Song

from ..config import get_config

# Import database and models directly - no fake service layer
from ..db.database import get_db_session
from ..exceptions import (
    DatabaseError,
    FileOperationError,
    InvalidTrackTypeError,
    NetworkError,
    ResourceNotFoundError,
    ServiceError,
    ValidationError,
)
from ..repositories.song_repository import SongRepository
from ..schemas.requests import CreateSongRequest
from ..services import FileService
from ..services.lyrics_service import LyricsService
from ..utils.error_handlers import handle_api_error
from ..utils.validation import validate_json_request, validate_path_params

logger = logging.getLogger(__name__)
song_bp = Blueprint("songs", __name__, url_prefix="/api/songs")

# --- Consolidated artist and search routes from songs_artists.py ---

from app.db.models.song import DbSong
from app.schemas.requests import UpdateSongRequest


@song_bp.route("/artists", methods=["GET"])
@handle_api_error
def get_artists():
    """Get all unique artists with song counts and optional filtering.

    Query Parameters:
        search: Optional search term to filter artists
        limit: Maximum number of artists to return (default: 100)
        offset: Number of artists to skip (default: 0)
    """
    try:
        search_term = request.args.get("search", "").strip()
        limit = min(int(request.args.get("limit", 100)), 200)  # Cap at 200
        offset = int(request.args.get("offset", 0))

        # Get artists with song counts from database
        with get_db_session() as session:
            repo = SongRepository(session)
            from sqlalchemy import func

            artists_query = session.query(
                DbSong.artist, func.count(DbSong.id).label("song_count")
            )
            if search_term:
                artists_query = artists_query.filter(
                    DbSong.artist.ilike(f"%{search_term}%")
                )
            artists_query = artists_query.group_by(DbSong.artist).order_by(
                DbSong.artist
            )
            artists = artists_query.offset(offset).limit(limit).all()
            artists = [
                {
                    "name": artist,
                    "songCount": song_count,
                    "firstLetter": artist[0].upper() if artist else "?",
                }
                for artist, song_count in artists
            ]

        total_count = 0
        with get_db_session() as session:
            repo = SongRepository(session)
            from sqlalchemy import func

            total_query = session.query(DbSong.artist).distinct()
            if search_term:
                total_query = total_query.filter(
                    DbSong.artist.ilike(f"%{search_term}%")
                )
            total_count = total_query.count()

        response = {
            "artists": artists,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "hasMore": offset + limit < total_count,
            },
        }

        logger.info("Returning %s artists (total: %s)", len(artists), total_count)
        return jsonify(response)

    except ValueError as e:
        raise ValidationError(
            f"Invalid query parameters: {str(e)}", "INVALID_PARAMETERS"
        )
    except ConnectionError as e:
        raise DatabaseError(
            "Database connection failed while fetching artists",
            "DATABASE_CONNECTION_ERROR",
            {"error": str(e)},
        )
    except Exception as e:
        raise DatabaseError(
            "Unexpected error fetching artists",
            "ARTISTS_FETCH_ERROR",
            {"error": str(e)},
        )


@song_bp.route("/by-artist/<string:artist_name>", methods=["GET"])
@handle_api_error
def get_songs_by_artist_route(artist_name: str):
    """Get songs for a specific artist with pagination.

    Query Parameters:
        limit: Maximum number of songs to return (default: 20)
        offset: Number of songs to skip (default: 0)
        sort: Sort order - 'title', 'album', 'year', 'dateAdded' (default: 'title')
        direction: 'asc' or 'desc' (default: 'asc')
    """
    try:
        limit = min(int(request.args.get("limit", 20)), 100)  # Cap at 100 per page
        offset = int(request.args.get("offset", 0))
        sort_by = request.args.get("sort", "title")
        direction = request.args.get("direction", "asc")

        # Validate sort parameters
        valid_sorts = ["title", "album", "year", "dateAdded"]
        if sort_by not in valid_sorts:
            raise ValidationError(
                f"Invalid sort field: {sort_by}. Must be one of: {', '.join(valid_sorts)}",
                "INVALID_SORT_FIELD",
            )

        if direction not in ["asc", "desc"]:
            raise ValidationError(
                f"Invalid sort direction: {direction}. Must be 'asc' or 'desc'",
                "INVALID_SORT_DIRECTION",
            )

        # Get songs for artist from database
        with get_db_session() as session:
            repo = SongRepository(session)
            base_query = session.query(DbSong).filter(DbSong.artist == artist_name)
            sort_field = getattr(DbSong, sort_by, DbSong.title)
            if direction.lower() == "desc":
                base_query = base_query.order_by(sort_field.desc())
            else:
                base_query = base_query.order_by(sort_field.asc())
            total_count = base_query.count()
            songs = base_query.offset(offset).limit(limit).all()
            songs_data = {"songs": songs, "total": total_count}

            # Convert DbSong objects to Pydantic Song models for API response
            songs = [
                Song.model_validate(song.to_dict()).model_dump()
                for song in songs_data["songs"]
            ]
            total_count = songs_data["total"]

            response = {
                "songs": songs,
                "artist": artist_name,
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "hasMore": offset + limit < total_count,
                },
            }

            logger.info(
                "Returning %s songs for artist '%s' (total: %s)",
                len(songs),
                artist_name,
                total_count,
            )
            return jsonify(response)

    except ValidationError:
        raise  # Let error handlers deal with it
    except ValueError as e:
        raise ValidationError(
            f"Invalid query parameters: {str(e)}", "INVALID_PARAMETERS"
        )
    except ConnectionError as e:
        raise DatabaseError(
            f"Database connection failed while fetching songs for artist '{artist_name}'",
            "DATABASE_CONNECTION_ERROR",
            {"artist": artist_name, "error": str(e)},
        )
    except Exception as e:
        raise DatabaseError(
            f"Unexpected error fetching songs for artist '{artist_name}'",
            "ARTIST_SONGS_FETCH_ERROR",
            {"artist": artist_name, "error": str(e)},
        )


@song_bp.route("/search", methods=["GET"])
@handle_api_error
def search_songs():
    """Enhanced search with pagination and artist grouping options.

    Query Parameters:
        q: Search query (required)
        limit: Maximum number of songs to return (default: 20)
        offset: Number of songs to skip (default: 0)
        group_by_artist: If true, group results by artist (default: false)
        sort: Sort order (default: 'relevance')
        direction: 'asc' or 'desc' (default: 'desc')
    """
    try:
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify(
                {
                    "songs": [],
                    "pagination": {
                        "total": 0,
                        "limit": 0,
                        "offset": 0,
                        "hasMore": False,
                    },
                }
            )

        limit = min(int(request.args.get("limit", 20)), 100)
        offset = int(request.args.get("offset", 0))
        group_by_artist = request.args.get("group_by_artist", "false").lower() == "true"
        sort_by = request.args.get("sort", "relevance")
        direction = request.args.get("direction", "desc")

        # Validate parameters
        if direction not in ["asc", "desc"]:
            raise ValidationError(
                f"Invalid sort direction: {direction}. Must be 'asc' or 'desc'",
                "INVALID_SORT_DIRECTION",
            )

        # Get search results from database
        with get_db_session() as session:
            repo = SongRepository(session)
            from sqlalchemy import func, or_

            search_filter = or_(
                DbSong.title.ilike(f"%{query}%"),
                DbSong.artist.ilike(f"%{query}%"),
                DbSong.album.ilike(f"%{query}%"),
            )
            if group_by_artist:
                artist_query = (
                    session.query(
                        DbSong.artist,
                        func.count(DbSong.id).label("song_count"),
                    )
                    .filter(search_filter)
                    .group_by(DbSong.artist)
                )
                total_artists = artist_query.count()
                artist_results = artist_query.offset(offset).limit(limit).all()
                artists_data = []
                total_songs = 0
                for artist, count in artist_results:
                    songs_query = (
                        session.query(DbSong).filter(DbSong.artist == artist).limit(5)
                    )
                    songs = songs_query.all()
                    total_songs += count
                    artists_data.append(
                        {
                            "artist": artist,
                            "songCount": count,
                            "songs": songs,
                        }
                    )
                search_results = {
                    "artists": artists_data,
                    "total_songs": total_songs,
                    "total_artists": total_artists,
                    "pagination": {
                        "total": total_artists,
                        "limit": limit,
                        "offset": offset,
                        "hasMore": offset + limit < total_artists,
                    },
                }
            else:
                base_query = session.query(DbSong).filter(search_filter)
                if sort_by == "relevance":
                    base_query = base_query.order_by(
                        DbSong.title,
                        DbSong.artist,
                        DbSong.date_added.desc(),
                    )
                else:
                    sort_field = getattr(DbSong, sort_by, DbSong.title)
                    if direction.lower() == "desc":
                        base_query = base_query.order_by(sort_field.desc())
                    else:
                        base_query = base_query.order_by(sort_field.asc())
                total_count = base_query.count()
                songs = base_query.offset(offset).limit(limit).all()
                search_results = {
                    "songs": songs,
                    "pagination": {
                        "total": total_count,
                        "limit": limit,
                        "offset": offset,
                        "hasMore": offset + limit < total_count,
                    },
                }

        if group_by_artist:
            # Group results by artist
            response = {
                "artists": search_results[
                    "artists"
                ],  # [{artist: "...", songs: [...], count: N}]
                "totalSongs": search_results["total_songs"],
                "totalArtists": search_results["total_artists"],
                "pagination": search_results["pagination"],
            }
        else:
            # Flat list of songs - convert using new pattern
            songs = [
                Song.model_validate(song.to_dict()).model_dump()
                for song in search_results["songs"]
            ]
            response = {"songs": songs, "pagination": search_results["pagination"]}

        logger.info(
            "Search '%s' returned %s results",
            query,
            search_results["pagination"]["total"],
        )
        return jsonify(response)

    except ValidationError:
        raise  # Let error handlers deal with it
    except ValueError as e:
        raise ValidationError(
            f"Invalid query parameters: {str(e)}", "INVALID_PARAMETERS"
        )
    except ConnectionError as e:
        raise DatabaseError(
            "Database connection failed during song search",
            "DATABASE_CONNECTION_ERROR",
            {"query": query, "error": str(e)},
        )
    except Exception as e:
        raise DatabaseError(
            "Unexpected error searching songs",
            "SONGS_SEARCH_ERROR",
            {"query": query, "error": str(e)},
        )


@song_bp.route("/metadata/auto", methods=["POST"])
@handle_api_error
def auto_save_itunes_metadata() -> tuple:
    """
    Accepts artist, title, album, and song_id. Fetches iTunes metadata and saves the first result to the song. Returns only success/failure JSON.
    """
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
        with get_db_session() as session:
            repo = SongRepository(session)
            song = repo.fetch(song_id)
        if not song:
            logger.error(f"Song not found: {song_id}")
            return jsonify({"success": False, "error": "Song not found"}), 404
        # Update song with new metadata (using DB model)
        update_fields = {k: v for k, v in results[0].items() if hasattr(song, k)}
        with get_db_session() as session:
            repo = SongRepository(session)
            updated_song = repo.update(song_id, **update_fields)
        if not updated_song:
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
        from ..repositories.song_repository import SongRepository

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
            songs = repo.fetch_all()
            # Sorting and pagination (if needed)
            if sort_by != "date_added" or direction != "desc":
                songs = sorted(
                    songs,
                    key=lambda s: getattr(s, sort_by, None),
                    reverse=(direction == "desc"),
                )
            if offset:
                songs = songs[offset:]
            if limit:
                songs = songs[:limit]
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
        )
    except Exception as e:
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
        with get_db_session() as session:
            repo = SongRepository(session)
            db_song = repo.fetch(song_id)
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
    with get_db_session() as session:
        repo = SongRepository(session)
        db_song = repo.fetch(song_id)
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
        with get_db_session() as session:
            repo = SongRepository(session)
            db_song = repo.fetch(song_id)
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
    """Endpoint to delete a song by its ID using SongRepository."""
    logger.info("Received request to delete song: %s", song_id)

    try:
        from ..db.database import get_db_session
        from ..repositories.song_repository import SongRepository
        from ..services.file_service import FileService

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

        # Validate using UpdateSongRequest
        try:
            validated = UpdateSongRequest(**data)
        except Exception as e:
            raise ValidationError(str(e), "INVALID_UPDATE_DATA")

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
