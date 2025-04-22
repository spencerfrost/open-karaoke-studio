# backend/app/song_endpoints.py

from flask import Blueprint, jsonify, send_from_directory, current_app
from pathlib import Path
from datetime import datetime, timezone
from typing import List

# Assuming these modules are in the same 'app' directory or PYTHONPATH is set
from . import file_management
from . import config
from .models import Song # Import the Pydantic Song model

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


# --- Add other song-related endpoints here later ---
# Example: Get single song details
# @song_bp.route('/<string:song_id>', methods=['GET'])
# def get_song_details(song_id: str):
#     # ... implementation ...
#     pass

# Example: Update song metadata (e.g., toggle favorite)
# @song_bp.route('/<string:song_id>', methods=['PUT']) # Or PATCH
# def update_song_details(song_id: str):
#     # ... implementation ...
#     pass

# Example: Delete song
# @song_bp.route('/<string:song_id>', methods=['DELETE'])
# def delete_song_endpoint(song_id: str):
#     # ... implementation ...
#     pass