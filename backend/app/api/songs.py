# backend/app/api/songs.py

from flask import Blueprint, jsonify, send_from_directory, current_app, request
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import unquote
import uuid

# Import database and models
from ..db import database
from ..db.models import Song, SongMetadata, DbSong
from ..services import file_management, FileService
from ..services.song_service import SongService
from ..exceptions import ServiceError, NotFoundError
from ..config import get_config
from ..services.lyrics_service import LyricsService

song_bp = Blueprint("songs", __name__, url_prefix="/api/songs")


@song_bp.route("", methods=["GET"])
def get_songs():
    """Endpoint to get a list of processed songs with metadata - thin controller using service layer."""
    current_app.logger.info("Received request for /api/songs")

    try:
        song_service = SongService()
        songs = song_service.get_all_songs()

        # Convert to JSON response format
        response_data = [
            song.model_dump(mode="json") if hasattr(song, "model_dump") else song.dict()
            for song in songs
        ]

        current_app.logger.info(f"Returning {len(response_data)} songs.")
        return jsonify(response_data)

    except ServiceError as e:
        current_app.logger.error(f"Service error in get_songs: {e}")
        return jsonify({"error": "Failed to fetch songs", "details": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_songs: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@song_bp.route("/<string:song_id>/download/<string:track_type>", methods=["GET"])
def download_song_track(song_id: str, track_type: str):
    """Downloads a specific track type (vocals, instrumental, original) for a song."""
    current_app.logger.info(
        f"Download request for song '{song_id}', track type '{track_type}'"
    )
    track_type = track_type.lower()  # Normalize track type

    if track_type not in ("vocals", "instrumental", "original"):
        current_app.logger.warning(f"Invalid track type requested: {track_type}")
        return (
            jsonify(
                {
                    "error": "Invalid track type specified. Use 'vocals', 'instrumental', or 'original'."
                }
            ),
            400,
        )

    try:
        file_service = FileService()
        song_dir = file_service.get_song_directory(song_id)
        if not song_dir.is_dir():
            current_app.logger.error(f"Song directory not found: {song_dir}")
            return jsonify({"error": "Song not found"}), 404

        track_file: Optional[Path] = song_dir / f"{track_type}.mp3"

        if track_file and track_file.is_file():
            # Security Check: Ensure the file is within the base library directory
            config = get_config()
            library_base_path = config.LIBRARY_DIR.resolve()
            file_path_resolved = track_file.resolve()

            if library_base_path not in file_path_resolved.parents:
                current_app.logger.error(
                    f"Attempted download outside library bounds: {track_file}"
                )
                return jsonify({"error": "Access denied"}), 403

            current_app.logger.info(
                f"Sending {track_type}.mp3 from directory '{song_dir}'"
            )
            return send_from_directory(
                song_dir,  # Directory path object
                track_file.name,  # Just the filename string - use .name to get just the filename
                as_attachment=True,  # Trigger browser download prompt
            )
        else:
            current_app.logger.error(f"Track file not found: {track_file}")
            return (
                jsonify(
                    {
                        "error": f"{track_type.capitalize()} track not found for this song"
                    }
                ),
                404,
            )

    except Exception as e:
        current_app.logger.error(
            f"Error during download for song '{song_id}', track '{track_type}': {e}",
            exc_info=True,
        )
        # Use exc_info=True in logger to include traceback
        return jsonify({"error": "An internal error occurred during download."}), 500


@song_bp.route("/<string:song_id>", methods=["GET"])
def get_song_details(song_id: str):
    """Endpoint to get details for a specific song - thin controller using service layer."""
    current_app.logger.info(f"Received request for song details: {song_id}")

    try:
        song_service = SongService()
        song = song_service.get_song_by_id(song_id)

        if not song:
            return jsonify({"error": f"Song with ID {song_id} not found"}), 404

        # Convert to response format
        response = (
            song.model_dump(mode="json") if hasattr(song, "model_dump") else song.dict()
        )

        # Add additional fields from database if needed (legacy compatibility)
        db_song = database.get_song(song_id)
        if db_song:
            response.update(
                {
                    "album": db_song.album,
                    "year": db_song.release_date,
                    "genre": db_song.genre,
                    "language": db_song.language,
                    "metadataId": db_song.mbid,
                    "channelName": db_song.channel,
                    "source": db_song.source,
                    "sourceUrl": db_song.source_url,
                    "lyrics": db_song.lyrics,
                    "syncedLyrics": db_song.synced_lyrics,
                    # iTunes metadata
                    "itunesTrackId": db_song.itunes_track_id,
                    "itunesArtistId": db_song.itunes_artist_id,
                    "itunesCollectionId": db_song.itunes_collection_id,
                    "trackTimeMillis": db_song.track_time_millis,
                    "itunesExplicit": db_song.itunes_explicit,
                    "itunesPreviewUrl": db_song.itunes_preview_url,
                    "itunesArtworkUrls": db_song.itunes_artwork_urls,
                    # YouTube metadata
                    "youtubeDuration": db_song.youtube_duration,
                    "youtubeThumbnailUrls": db_song.youtube_thumbnail_urls,
                    "youtubeTags": db_song.youtube_tags,
                    "youtubeCategories": db_song.youtube_categories,
                    "youtubeChannelId": db_song.youtube_channel_id,
                    "youtubeChannelName": db_song.youtube_channel_name,
                }
            )

        current_app.logger.info(f"Returning details for song {song_id}")
        return jsonify(response), 200

    except ServiceError as e:
        current_app.logger.error(f"Service error getting song {song_id}: {e}")
        return jsonify({"error": "Failed to fetch song", "details": str(e)}), 500
    except Exception as e:
        current_app.logger.error(
            f"Unexpected error getting song {song_id}: {e}", exc_info=True
        )
        return jsonify({"error": "Internal server error"}), 500


# Removed redundant metadata endpoint - use generic PATCH /api/songs/<song_id> instead


@song_bp.route("/<string:song_id>/thumbnail.<string:extension>", methods=["GET"])
def get_thumbnail(song_id: str, extension: str):
    """Serve the thumbnail image for a song."""
    from flask import send_file
    import os

    # Decode the song ID to handle URL-encoded characters
    song_id = unquote(song_id)

    # Validate extension
    allowed_extensions = {'jpg', 'jpeg', 'png', 'webp'}
    if extension.lower() not in allowed_extensions:
        return jsonify({"error": "Invalid image format"}), 400

    # Get song from database to find thumbnail path
    db_song = database.get_song(song_id)

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
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg', 
        'png': 'image/png',
        'webp': 'image/webp'
    }
    mimetype = mimetype_map.get(extension.lower(), 'image/jpeg')

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
    from flask import send_file
    import os

    # Decode the song ID to handle URL-encoded characters
    song_id = unquote(song_id)

    # Get song from database to find thumbnail path
    db_song = database.get_song(song_id)

    # Construct the path to the thumbnail
    file_service = FileService()
    song_dir = file_service.get_song_directory(song_id)
    
    # Try different formats in order of preference
    formats_to_try = [
        ('webp', 'image/webp'),      # Best quality/compression
        ('jpg', 'image/jpeg'),       # Most common
        ('jpeg', 'image/jpeg'),      # Alternative JPEG extension
        ('png', 'image/png')         # Lossless fallback
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
    current_app.logger.info(f"Received lyrics request for song {song_id}")

    try:
        lyrics_service = LyricsService()
        
        # Check if we have lyrics stored locally first
        stored_lyrics = lyrics_service.get_lyrics(song_id)
        if stored_lyrics:
            current_app.logger.info(f"Returning stored lyrics for song {song_id}")
            return jsonify({"plainLyrics": stored_lyrics}), 200

        # Try to get from database first
        db_song = database.get_song(song_id)

        if db_song:
            # Use database fields
            title = db_song.title
            artist = (
                db_song.artist
                if db_song.artist.lower() != "unknown artist"
                else db_song.channel
            )
            album = db_song.album
        else:
            # Fall back to file-based approach
            metadata = file_management.read_song_metadata(song_id)
            if not metadata or not metadata.title:
                current_app.logger.warning(f"Metadata incomplete for lyrics: {song_id}")
                return (
                    jsonify(
                        {"error": "Missing metadata (title) for lyrics lookup"}
                    ),
                    400,
                )

            # Determine best artist name: prefer metadata.artist, else channel
            artist = (
                metadata.artist
                if metadata.artist and metadata.artist.lower() != "unknown artist"
                else metadata.channel
            )
            if not artist:
                current_app.logger.warning(f"Artist unknown for lyrics: {song_id}")
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
            current_app.logger.info(f"Found lyrics for {song_id}")
            
            # Optionally save the lyrics locally for future use
            if lyrics_data.get("plainLyrics"):
                try:
                    lyrics_service.save_lyrics(song_id, lyrics_data["plainLyrics"])
                except Exception as e:
                    current_app.logger.warning(f"Failed to save lyrics locally: {e}")
            
            return jsonify(lyrics_data), 200
        else:
            current_app.logger.info(f"No lyrics found for {song_id}")
            return jsonify({"error": "No lyrics found"}), 404

    except ServiceError as e:
        current_app.logger.error(f"Service error getting lyrics for {song_id}: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error getting lyrics for {song_id}: {e}")
        return jsonify({"error": "Failed to fetch lyrics"}), 500


@song_bp.route("/<string:song_id>", methods=["DELETE"])
def delete_song(song_id: str):
    """Endpoint to delete a song by its ID - thin controller using service layer."""
    current_app.logger.info(f"Received request to delete song: {song_id}")

    try:
        song_service = SongService()
        success = song_service.delete_song(song_id)

        if not success:
            return jsonify({"error": "Song not found"}), 404

        # Also delete files using FileService
        file_service = FileService()
        file_service.delete_song_files(song_id)

        current_app.logger.info(f"Successfully deleted song: {song_id}")
        return jsonify({"message": "Song deleted successfully"}), 200

    except ServiceError as e:
        current_app.logger.error(f"Service error deleting song {song_id}: {e}")
        return jsonify({"error": "Failed to delete song", "details": str(e)}), 500
    except Exception as e:
        current_app.logger.error(
            f"Unexpected error deleting song {song_id}: {e}", exc_info=True
        )
        return jsonify({"error": "Internal server error"}), 500


@song_bp.route("", methods=["POST"])
def create_song():
    """Create a new song with basic information - thin controller using service layer."""
    current_app.logger.info("Received request to create a new song")

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
        current_app.logger.info(f"Creating new song with ID: {song_id}")

        # Prepare metadata
        metadata = SongMetadata(
            title=data.get("title"),
            artist=data.get("artist", "Unknown Artist"),
            dateAdded=datetime.now(timezone.utc),
            source=data.get("source"),
            sourceUrl=data.get("sourceUrl"),
            videoId=data.get("videoId"),
            videoTitle=data.get("videoTitle"),
            uploader=data.get("uploader"),
            uploaderId=data.get("uploaderId"),
            channel=data.get("channel"),
            channelId=data.get("channelId"),
            releaseTitle=data.get("album"),
            releaseDate=data.get("year"),
            genre=data.get("genre"),
            language=data.get("language"),
        )

        # Use service to create song
        song_service = SongService()
        song = song_service.create_song_from_metadata(song_id, metadata)

        # Verify the song was created successfully in the database
        db_song = database.get_song(song_id)
        if not db_song:
            current_app.logger.error(f"Failed to create song {song_id} in database")
            return jsonify({"error": "Failed to create song in database"}), 500

        # Create the song directory
        try:
            from ..services.file_service import FileService

            file_service = FileService()
            song_dir = file_service.get_song_directory(song_id)
            song_dir.mkdir(parents=True, exist_ok=True)
            current_app.logger.info(f"Created directory for song: {song_dir}")
        except Exception as e:
            current_app.logger.error(
                f"Error creating directory for song {song_id}: {e}"
            )
            # Continue even if directory creation fails - we'll try again during processing

        # Return the song data
        response = {
            "id": song_id,
            "title": song.title,
            "artist": song.artist,
            "album": data.get("album"),
            "dateAdded": song.dateAdded.isoformat() if song.dateAdded else None,
            "status": "pending",
        }

        current_app.logger.info(f"Successfully created song: {song_id}")
        return jsonify(response), 201

    except ServiceError as e:
        current_app.logger.error(f"Service error creating song: {e}")
        return jsonify({"error": "Failed to create song", "details": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error creating song: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@song_bp.route("/search", methods=["GET"])
def search_songs():
    """Search songs endpoint - thin controller using service layer."""
    query = request.args.get("q", "").strip()
    current_app.logger.info(f"Received search request with query: '{query}'")

    if not query:
        return jsonify([])

    try:
        song_service = SongService()
        songs = song_service.search_songs(query)

        response_data = [
            song.model_dump(mode="json") if hasattr(song, "model_dump") else song.dict()
            for song in songs
        ]

        current_app.logger.info(f"Found {len(response_data)} songs matching '{query}'")
        return jsonify(response_data)

    except ServiceError as e:
        current_app.logger.error(f"Service error searching songs: {e}")
        return jsonify({"error": "Failed to search songs", "details": str(e)}), 500
    except Exception as e:
        current_app.logger.error(
            f"Unexpected error searching songs: {e}", exc_info=True
        )
        return jsonify({"error": "Internal server error"}), 500


@song_bp.route("/<string:song_id>", methods=["PATCH"])
def update_song(song_id: str):
    """Update a song with any provided fields - generic update endpoint."""
    current_app.logger.info(f"Received request to update song {song_id}")

    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Get existing song from database first
        db_song = database.get_song(song_id)
        if not db_song:
            return jsonify({"error": "Song not found"}), 404

        # Start with existing values from database
        metadata_dict = {
            "title": db_song.title,
            "artist": db_song.artist,
            "duration": db_song.duration,
            "favorite": db_song.favorite,
            "dateAdded": db_song.date_added,
            "coverArt": db_song.cover_art_path,
            "thumbnail": db_song.thumbnail_path,
            "source": db_song.source,
            "sourceUrl": db_song.source_url,
            "videoId": db_song.video_id,
            "uploader": db_song.uploader,
            "uploaderId": db_song.uploader_id,
            "channel": db_song.channel,
            "channelId": db_song.channel_id,
            "description": db_song.description,
            "uploadDate": db_song.upload_date,
            "mbid": db_song.mbid,
            "releaseTitle": db_song.album,  # Keeping for backwards compatibility
            "releaseId": db_song.release_id,
            "releaseDate": db_song.release_date,
            "genre": db_song.genre,
            "language": db_song.language,
            "lyrics": db_song.lyrics,
            "syncedLyrics": db_song.synced_lyrics,
            # iTunes metadata
            "itunesTrackId": db_song.itunes_track_id,
            "itunesArtistId": db_song.itunes_artist_id,
            "itunesCollectionId": db_song.itunes_collection_id,
            "trackTimeMillis": db_song.track_time_millis,
            "itunesExplicit": db_song.itunes_explicit,
            "itunesPreviewUrl": db_song.itunes_preview_url,
            "itunesArtworkUrls": db_song.itunes_artwork_urls,
            # YouTube metadata
            "youtubeDuration": db_song.youtube_duration,
            "youtubeThumbnailUrls": db_song.youtube_thumbnail_urls,
            "youtubeTags": db_song.youtube_tags,
            "youtubeCategories": db_song.youtube_categories,
            "youtubeChannelId": db_song.youtube_channel_id,
            "youtubeChannelName": db_song.youtube_channel_name,
        }
        
        # Apply updates from request data
        # Handle direct field mappings
        for field in ["title", "artist", "favorite", "duration", "source", "sourceUrl", 
                     "videoId", "uploader", "uploaderId", "channel", "channelId", 
                     "description", "uploadDate", "mbid", "genre", "language", 
                     "lyrics", "syncedLyrics", "itunesArtworkUrls"]:
            if field in data:
                metadata_dict[field] = data[field]
        
        # Handle frontend-to-backend field name mappings
        if "album" in data:
            metadata_dict["releaseTitle"] = data["album"]
        if "year" in data:
            metadata_dict["releaseDate"] = data["year"]
        if "metadataId" in data:
            metadata_dict["mbid"] = data["metadataId"]
        if "coverArt" in data:
            metadata_dict["coverArt"] = data["coverArt"]
        if "thumbnail" in data:
            metadata_dict["thumbnail"] = data["thumbnail"]
        
        # Create SongMetadata object
        updated_metadata = SongMetadata(**metadata_dict)
        
        # Save to database using file_management function
        file_management.write_song_metadata(song_id, updated_metadata)
        
        # Return updated song details
        return get_song_details(song_id)

    except Exception as e:
        current_app.logger.error(f"Unexpected error updating song {song_id}: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@song_bp.route("/<string:song_id>/cover.<string:extension>", methods=["GET"])
def get_cover_art(song_id: str, extension: str):
    """Serve the cover art image for a song."""
    from flask import send_file
    import os

    # Decode the song ID to handle URL-encoded characters
    song_id = unquote(song_id)

    # Validate extension
    allowed_extensions = {'jpg', 'jpeg', 'png', 'webp'}
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
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg', 
        'png': 'image/png',
        'webp': 'image/webp'
    }
    mimetype = mimetype_map.get(extension.lower(), 'image/jpeg')

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
    from flask import send_file
    import os

    # Decode the song ID to handle URL-encoded characters
    song_id = unquote(song_id)

    # Construct the path to the cover art
    file_service = FileService()
    song_dir = file_service.get_song_directory(song_id)
    
    # Try different formats in order of preference
    formats_to_try = [
        ('webp', 'image/webp'),      # Best quality/compression
        ('jpg', 'image/jpeg'),       # Most common
        ('jpeg', 'image/jpeg'),      # Alternative JPEG extension
        ('png', 'image/png'),        # High quality
    ]
    
    for ext, mimetype in formats_to_try:
        cover_art_path = song_dir / f"cover.{ext}"
        if cover_art_path.exists() and os.access(cover_art_path, os.R_OK):
            try:
                return send_file(cover_art_path, mimetype=mimetype)
            except Exception:
                continue  # Try next format
    
    return jsonify({"error": "Cover art not found"}), 404
