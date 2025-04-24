# backend/app/song_endpoints.py

from flask import Blueprint, jsonify, send_from_directory, current_app
from pathlib import Path
from datetime import datetime, timezone
from typing import List

# Importing SongMetadata for the metadata endpoint
from .models import Song, SongMetadata

# Assuming these modules are in the same 'app' directory or PYTHONPATH is set
from . import file_management
from . import config
from .models import Song # Import the Pydantic Song model
from .lyrics_endpoints import _make_request

# Define the Blueprint
# All routes defined here will be prefixed with /api/songs
song_bp = Blueprint('songs', __name__, url_prefix='/api/songs')

@song_bp.route('/', methods=['GET'])
def get_songs():
    """Endpoint to get a list of processed songs with metadata."""
    current_app.logger.info("Received request for /api/songs")
    song_ids = file_management.get_processed_songs()
    songs_list: List[Song] = []

    for song_id in song_ids:
        metadata = file_management.read_song_metadata(song_id)
        song_dir = file_management.get_song_dir(song_id)

        # --- Determine file paths ---
        vocals_file = file_management.get_vocals_path_stem(song_dir).with_suffix(file_management.VOCALS_SUFFIX)
        instrumental_file = file_management.get_instrumental_path_stem(song_dir).with_suffix(file_management.INSTRUMENTAL_SUFFIX)
        # Find original file using glob pattern based on song_id and suffix
        original_suffix = config.ORIGINAL_FILENAME_SUFFIX if hasattr(config, 'ORIGINAL_FILENAME_SUFFIX') else "_original"
        original_pattern = f"{song_id}{original_suffix}.*"
        original_file = next(song_dir.glob(original_pattern), None)

        # --- Create Song object ---
        song_base_data = {
            "id": song_id,
            "status": 'processed', # Assume processed if listed
            # Construct relative paths or URLs as needed for the frontend
            # Example: using relative paths from BASE_LIBRARY_DIR
            "vocalPath": str(vocals_file.relative_to(config.BASE_LIBRARY_DIR)) if vocals_file.exists() else None,
            "instrumentalPath": str(instrumental_file.relative_to(config.BASE_LIBRARY_DIR)) if instrumental_file.exists() else None,
            "originalPath": str(original_file.relative_to(config.BASE_LIBRARY_DIR)) if original_file and original_file.exists() else None,
        }

        if metadata:
            song_data = Song(
                **song_base_data,
                title=metadata.title or song_id.replace('_', ' ').title(),
                artist=metadata.artist or "Unknown Artist",
                duration=metadata.duration,
                favorite=metadata.favorite,
                dateAdded=metadata.dateAdded,
                coverArt=metadata.coverArt,
                thumbnail=metadata.thumbnail,  # Include thumbnail from metadata
            )
        else:
            # Fallback if metadata is missing
            current_app.logger.warning(f"Metadata missing for song ID {song_id}. Using defaults.")
            try:
                ctime = datetime.fromtimestamp(song_dir.stat().st_ctime, tz=timezone.utc)
            except FileNotFoundError:
                ctime = datetime.now(timezone.utc)

            song_data = Song(
                 **song_base_data,
                title=song_id.replace('_', ' ').title(),
                artist="Unknown Artist",
                favorite=False,
                dateAdded=ctime,
            )

        songs_list.append(song_data)

    # Use Pydantic's serialization
    response_data = [song.model_dump(mode='json') if hasattr(song, 'model_dump') else song.dict() for song in songs_list]
    current_app.logger.info(f"Returning {len(response_data)} songs.")
    return jsonify(response_data)


@song_bp.route('/<string:song_id>/download/<string:track_type>', methods=['GET'])
def download_song_track(song_id: str, track_type: str):
    """Downloads a specific track type (vocals, instrumental, original) for a song."""
    current_app.logger.info(f"Download request for song '{song_id}', track type '{track_type}'")
    track_type = track_type.lower() # Normalize track type

    try:
        song_dir = file_management.get_song_dir(song_id)
        if not song_dir.is_dir():
            current_app.logger.error(f"Song directory not found: {song_dir}")
            return jsonify({"error": "Song not found"}), 404

        track_file: Optional[Path] = None
        track_filename: Optional[str] = None

        if track_type == 'vocals':
            path_stem = file_management.get_vocals_path_stem(song_dir)
            suffix = file_management.VOCALS_SUFFIX
            track_file = path_stem.with_suffix(suffix)
            track_filename = track_file.name
        elif track_type == 'instrumental':
            path_stem = file_management.get_instrumental_path_stem(song_dir)
            suffix = file_management.INSTRUMENTAL_SUFFIX
            track_file = path_stem.with_suffix(suffix)
            track_filename = track_file.name
        elif track_type == 'original':
            original_suffix = config.ORIGINAL_FILENAME_SUFFIX if hasattr(config, 'ORIGINAL_FILENAME_SUFFIX') else "_original"
            original_pattern = f"{song_id}{original_suffix}.*"
            found_original = next(song_dir.glob(original_pattern), None)
            if found_original:
                track_file = found_original
                track_filename = track_file.name
        else:
            current_app.logger.warning(f"Invalid track type requested: {track_type}")
            return jsonify({"error": "Invalid track type specified. Use 'vocals', 'instrumental', or 'original'."}), 400

        if track_file and track_filename and track_file.is_file():
            # Security Check: Ensure the file is within the base library directory
            library_base_path = config.BASE_LIBRARY_DIR.resolve()
            file_path_resolved = track_file.resolve()

            if library_base_path not in file_path_resolved.parents:
                current_app.logger.error(f"Attempted download outside library bounds: {track_file}")
                return jsonify({"error": "Access denied"}), 403

            current_app.logger.info(f"Sending file '{track_filename}' from directory '{song_dir}'")
            return send_from_directory(
                song_dir, # Directory path object
                track_filename, # Just the filename string
                as_attachment=True # Trigger browser download prompt
            )
        else:
            current_app.logger.error(f"Track file not found: {track_file}")
            return jsonify({"error": f"{track_type.capitalize()} track not found for this song"}), 404

    except Exception as e:
        current_app.logger.error(f"Error during download for song '{song_id}', track '{track_type}': {e}", exc_info=True)
        # Use exc_info=True in logger to include traceback
        # traceback.print_exc() # Keep if logger isn't configured for tracebacks
        return jsonify({"error": "An internal error occurred during download."}), 500


# --- Additional song-related endpoints ---

@song_bp.route('/<string:song_id>', methods=['GET'])
def get_song_details(song_id: str):
    """Endpoint to get details for a specific song."""
    current_app.logger.info(f"Received request for song details: {song_id}")
    try:
        song_dir = file_management.get_song_dir(song_id)
        
        if not song_dir.is_dir():
            current_app.logger.error(f"Song directory not found: {song_dir}")
            return jsonify({"error": "Song not found"}), 404
        
        metadata = file_management.read_song_metadata(song_id)
        
        if not metadata:
            current_app.logger.warning(f"Metadata missing for song ID {song_id}. Using defaults.")
            # Create a minimal response with defaults
            return jsonify({
                "id": song_id,
                "title": song_id.replace('_', ' ').title(),
                "artist": "Unknown Artist",
                "status": "processed",
                "favorite": False,
                "dateAdded": datetime.now(timezone.utc).isoformat()
            }), 200
        
        # Determine file paths
        vocals_file = file_management.get_vocals_path_stem(song_dir).with_suffix(file_management.VOCALS_SUFFIX)
        instrumental_file = file_management.get_instrumental_path_stem(song_dir).with_suffix(file_management.INSTRUMENTAL_SUFFIX)
        original_suffix = config.ORIGINAL_FILENAME_SUFFIX if hasattr(config, 'ORIGINAL_FILENAME_SUFFIX') else "_original"
        original_pattern = f"{song_id}{original_suffix}.*"
        original_file = next(song_dir.glob(original_pattern), None)
        
        # Create response
        response = {
            "id": song_id,
            "title": metadata.title or song_id.replace('_', ' ').title(),
            "artist": metadata.artist or "Unknown Artist",
            "album": metadata.releaseTitle,  # Map from MusicBrainz releaseTitle
            "year": metadata.releaseDate,    # Map from MusicBrainz releaseDate
            "genre": metadata.genre,
            "language": metadata.language,
            "duration": metadata.duration,
            "favorite": metadata.favorite,
            "dateAdded": metadata.dateAdded.isoformat() if metadata.dateAdded else datetime.now(timezone.utc).isoformat(),
            "coverArt": metadata.coverArt,
            "vocalPath": str(vocals_file.relative_to(config.BASE_LIBRARY_DIR)) if vocals_file.exists() else None,
            "instrumentalPath": str(instrumental_file.relative_to(config.BASE_LIBRARY_DIR)) if instrumental_file.exists() else None,
            "originalPath": str(original_file.relative_to(config.BASE_LIBRARY_DIR)) if original_file and original_file.exists() else None,
            "status": "processed",
            "musicbrainzId": metadata.mbid
        }
        
        current_app.logger.info(f"Returning details for song {song_id}")
        # Log the song_dir for debugging
        current_app.logger.info(f"Song directory for {song_id}: {song_dir}")
        return jsonify(response), 200
            
    except Exception as e:
        current_app.logger.error(f"Error getting song details for '{song_id}': {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred."}), 500


@song_bp.route('/<string:song_id>/metadata', methods=['PATCH'])
def update_song_metadata(song_id: str):
    """Endpoint to update song metadata."""
    from flask import request  # Import here for clarity
    
    current_app.logger.info(f"Received metadata update request for song: {song_id}")
    try:
        # Validate that song exists
        song_dir = file_management.get_song_dir(song_id)
        if not song_dir.is_dir():
            current_app.logger.error(f"Song directory not found: {song_dir}")
            return jsonify({"error": "Song not found"}), 404
            
        # Get request data
        update_data = request.get_json()
        if not update_data:
            return jsonify({"error": "No update data provided"}), 400
            
        # Get existing metadata
        existing_metadata = file_management.read_song_metadata(song_id)
        if not existing_metadata:
            # Create new metadata if it doesn't exist
            current_app.logger.warning(f"Creating new metadata for song {song_id}")
            existing_metadata = SongMetadata(
                title=update_data.get('title', song_id.replace('_', ' ').title()),
                artist=update_data.get('artist', "Unknown Artist"),
                dateAdded=datetime.now(timezone.utc)
            )
            
        # Update fields
        # Handle the standard fields
        if 'title' in update_data:
            existing_metadata.title = update_data['title']
        if 'artist' in update_data:
            existing_metadata.artist = update_data['artist']
        if 'favorite' in update_data:
            existing_metadata.favorite = update_data['favorite']
            
        # Handle the new fields we're adding - map from frontend to backend naming
        if 'album' in update_data:
            existing_metadata.releaseTitle = update_data['album']
        if 'year' in update_data:
            existing_metadata.releaseDate = update_data['year']
        if 'genre' in update_data:
            existing_metadata.genre = update_data['genre']
        if 'language' in update_data:
            existing_metadata.language = update_data['language']
        if 'musicbrainzId' in update_data and update_data['musicbrainzId']:
            existing_metadata.mbid = update_data['musicbrainzId']
            
        # Save updated metadata
        file_management.write_song_metadata(song_id, existing_metadata)
        
        # Return the full song details
        return get_song_details(song_id)
            
    except Exception as e:
        current_app.logger.error(f"Error updating metadata for song '{song_id}': {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred while updating metadata."}), 500


@song_bp.route('/<string:song_id>/thumbnail.jpg', methods=['GET'])
def get_thumbnail(song_id: str):
    """Serve the thumbnail image for a song."""
    from flask import send_file
    import os

    # Decode the song ID to handle URL-encoded characters
    from urllib.parse import unquote
    song_id = unquote(song_id)

    # Construct the path to the thumbnail
    song_dir = file_management.get_song_dir(song_id)
    thumbnail_path = song_dir / "thumbnail.jpg"

    if not thumbnail_path.exists():
        return jsonify({"error": "Thumbnail not found"}), 404

    if not os.access(thumbnail_path, os.R_OK):
        return jsonify({"error": "Thumbnail is not readable"}), 403

    try:
        return send_file(thumbnail_path, mimetype='image/jpeg')
    except Exception:
        return jsonify({"error": "An internal error occurred while serving the thumbnail."}), 500


@song_bp.route('/<string:song_id>/lyrics', methods=['GET'])
def get_song_lyrics(song_id: str):
    """Fetch synchronized or plain lyrics for a song using LRCLIB."""
    current_app.logger.info(f"Received lyrics request for song {song_id}")
    # Read metadata
    metadata = file_management.read_song_metadata(song_id)
    if not metadata or not metadata.title or not metadata.duration:
        current_app.logger.warning(f"Metadata incomplete for lyrics: {song_id}")
        return jsonify({"error": "Missing metadata (title, duration) for lyrics lookup"}), 400

    # Determine best artist name: prefer metadata.artist, else channelName
    artist = metadata.artist if metadata.artist and metadata.artist.lower() != 'unknown artist' else getattr(metadata, 'channelName', None)
    if not artist:
        current_app.logger.warning(f"Artist unknown for lyrics: {song_id}")
        return jsonify({"error": "Missing artist name for lyrics lookup"}), 400

    title = metadata.title
    duration = str(int(metadata.duration))
    album = metadata.releaseTitle

    # 1) If we know album and duration, try cached/get endpoints
    if album:
        params = { 'track_name': title, 'artist_name': artist, 'album_name': album, 'duration': duration }
        status, data = _make_request('/api/get-cached', params)
        if status == 404:
            current_app.logger.info(f"Cached lyrics not found for {song_id}, falling back to external lookup")
            status, data = _make_request('/api/get', params)
        return jsonify(data), status

    # 2) Fallback: search by track+artist, pick first result, then fetch by ID
    search_params = { 'track_name': title, 'artist_name': artist }
    status, results = _make_request('/api/search', search_params)
    if status != 200 or not isinstance(results, list) or not results:
        return jsonify({"error": "No lyrics found via search", "details": results}), status
    lyric_id = results[0].get('id')
    if not lyric_id:
        return jsonify({"error": "Invalid search result format", "details": results}), 500
    status, data = _make_request(f'/api/get/{lyric_id}', {})
    return jsonify(data), status