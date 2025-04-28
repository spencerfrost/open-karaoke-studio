# backend/app/api/songs.py

from flask import Blueprint, jsonify, send_from_directory, current_app, request
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import unquote

# Import database and models
from ..db import database
from ..db.models import Song, SongMetadata, DbSong
from ..services import file_management
from ..config import Config as config
from ..services.lyrics_service import make_request

song_bp = Blueprint('songs', __name__, url_prefix='/api/songs')

@song_bp.route('/', methods=['GET'])
def get_songs():
    """Endpoint to get a list of processed songs with metadata."""
    current_app.logger.info("Received request for /api/songs")
    
    # Get songs from the database
    db_songs = database.get_all_songs()
    
    # If database has no songs, sync from filesystem first
    if not db_songs:
        current_app.logger.info("No songs found in database, syncing from filesystem")
        songs_added = database.sync_songs_with_filesystem()
        current_app.logger.info(f"Added {songs_added} songs from filesystem to database")
        db_songs = database.get_all_songs()
    
    # Convert SQLAlchemy models to Pydantic models for API response
    songs_list = [song.to_pydantic() for song in db_songs]
    
    # Use Pydantic's serialization
    response_data = [song.model_dump(mode='json') if hasattr(song, 'model_dump') else song.dict() for song in songs_list]
    current_app.logger.info(f"Returning {len(response_data)} songs.")
    return jsonify(response_data)


@song_bp.route('/<string:song_id>/download/<string:track_type>', methods=['GET'])
def download_song_track(song_id: str, track_type: str):
    """Downloads a specific track type (vocals, instrumental, original) for a song."""
    # This function remains mostly unchanged as it deals with file downloads
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
        return jsonify({"error": "An internal error occurred during download."}), 500


@song_bp.route('/<string:song_id>', methods=['GET'])
def get_song_details(song_id: str):
    """Endpoint to get details for a specific song."""
    current_app.logger.info(f"Received request for song details: {song_id}")
    try:
        # First try to get from database
        db_song = database.get_song(song_id)
        
        if db_song:
            song = db_song.to_pydantic()
            
            # Add additional fields from DbSong that aren't in the Song model
            response = song.model_dump(mode='json') if hasattr(song, 'model_dump') else song.dict()
            response.update({
                "album": db_song.release_title,
                "year": db_song.release_date,
                "genre": db_song.genre,
                "language": db_song.language,
                "musicbrainzId": db_song.mbid,
                "channelName": db_song.channel,
                "source": db_song.source,
                "sourceUrl": db_song.source_url,
                "lyrics": db_song.lyrics,
                "syncedLyrics": db_song.synced_lyrics
            })
            
            current_app.logger.info(f"Returning details for song {song_id} from database")
            return jsonify(response), 200
        
        song_dir = file_management.get_song_dir(song_id)
        
        if not song_dir.is_dir():
            current_app.logger.error(f"Song directory not found: {song_dir}")
            return jsonify({"error": "Song not found"}), 404
        
        metadata = file_management.read_song_metadata(song_id)
        
        if not metadata:
            current_app.logger.warning(f"Metadata missing for song ID {song_id}. Using defaults.")
            return jsonify({
                "id": song_id,
                "title": song_id.replace('_', ' ').title(),
                "artist": "Unknown Artist",
                "status": "processed",
                "favorite": False,
                "dateAdded": datetime.now(timezone.utc).isoformat()
            }), 200
        
        vocals_file = file_management.get_vocals_path_stem(song_dir).with_suffix(file_management.VOCALS_SUFFIX)
        instrumental_file = file_management.get_instrumental_path_stem(song_dir).with_suffix(file_management.INSTRUMENTAL_SUFFIX)
        original_suffix = config.ORIGINAL_FILENAME_SUFFIX if hasattr(config, 'ORIGINAL_FILENAME_SUFFIX') else "_original"
        original_pattern = f"{song_id}{original_suffix}.*"
        original_file = next(song_dir.glob(original_pattern), None)
        
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
            "musicbrainzId": metadata.mbid,
            "lyrics": metadata.lyrics,
            "syncedLyrics": metadata.syncedLyrics
        }
        
        database.create_or_update_song(song_id, metadata)
        
        return jsonify(response), 200
            
    except Exception as e:
        current_app.logger.error(f"Error getting song details for '{song_id}': {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred."}), 500


@song_bp.route('/<string:song_id>/metadata', methods=['PATCH'])
def update_song_metadata(song_id: str):
    """Endpoint to update song metadata."""
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
            
        # Get existing metadata from database first, then filesystem
        db_song = database.get_song(song_id)
        existing_metadata = None
        
        if db_song:
            # Convert database song to SongMetadata for file_management.write_song_metadata
            existing_metadata = SongMetadata(
                title=db_song.title,
                artist=db_song.artist,
                duration=db_song.duration,
                favorite=db_song.favorite,
                dateAdded=db_song.date_added,
                coverArt=db_song.cover_art_path,
                thumbnail=db_song.thumbnail_path,
                source=db_song.source,
                sourceUrl=db_song.source_url,
                videoId=db_song.video_id,
                channelName=db_song.channel,
                channelId=db_song.channel_id,
                description=db_song.description,
                uploadDate=db_song.upload_date,
                mbid=db_song.mbid,
                releaseTitle=db_song.release_title,
                releaseId=db_song.release_id,
                releaseDate=db_song.release_date,
                genre=db_song.genre,
                language=db_song.language,
                # Make sure to include lyrics fields
                lyrics=db_song.lyrics,
                syncedLyrics=db_song.synced_lyrics
            )
        else:
            # Get from filesystem if not in database
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
        
        # Explicitly handle the lyrics fields to ensure they're preserved
        if 'lyrics' in update_data:
            existing_metadata.lyrics = update_data['lyrics']
        if 'syncedLyrics' in update_data:
            existing_metadata.syncedLyrics = update_data['syncedLyrics']
            
        # Save updated metadata to file
        file_management.write_song_metadata(song_id, existing_metadata)
        
        # Update database entry
        database.create_or_update_song(song_id, existing_metadata)
        
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
    song_id = unquote(song_id)

    # Get song from database to find thumbnail path
    db_song = database.get_song(song_id)
    
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
    # This function can remain mostly unchanged
    current_app.logger.info(f"Received lyrics request for song {song_id}")
    
    # Try to get from database first
    db_song = database.get_song(song_id)
    
    if db_song:
        # Use database fields
        title = db_song.title
        artist = db_song.artist if db_song.artist.lower() != 'unknown artist' else db_song.channel_name
        duration = str(int(db_song.duration)) if db_song.duration else None
        album = db_song.release_title
    else:
        # Fall back to file-based approach
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

    # If missing essential info, return error
    if not title or not artist or not duration:
        return jsonify({"error": "Missing essential info for lyrics lookup"}), 400

    # 1) If we know album and duration, try cached/get endpoints
    if album:
        params = { 'track_name': title, 'artist_name': artist, 'album_name': album, 'duration': duration }
        status, data = make_request('/api/get-cached', params)
        if status == 404:
            current_app.logger.info(f"Cached lyrics not found for {song_id}, falling back to external lookup")
            status, data = make_request('/api/get', params)
        return jsonify(data), status

    # 2) Fallback: search by track+artist, pick first result, then fetch by ID
    search_params = { 'track_name': title, 'artist_name': artist }
    status, results = make_request('/api/search', search_params)
    if status != 200 or not isinstance(results, list) or not results:
        return jsonify({"error": "No lyrics found via search", "details": results}), status
    lyric_id = results[0].get('id')
    if not lyric_id:
        return jsonify({"error": "Invalid search result format", "details": results}), 500
    status, data = make_request(f'/api/get/{lyric_id}', {})
    return jsonify(data), status


@song_bp.route('/<string:song_id>', methods=['DELETE'])
def delete_song(song_id: str):
    """Endpoint to delete a song by its ID."""
    current_app.logger.info(f"Received request to delete song: {song_id}")
    try:
        # Validate that the song exists
        song_dir = file_management.get_song_dir(song_id)
        if not song_dir.is_dir():
            current_app.logger.error(f"Song directory not found: {song_dir}")
            return jsonify({"error": "Song not found"}), 404

        # Delete song files
        file_management.delete_song_files(song_id)

        # Remove song from the database
        database.delete_song(song_id)

        current_app.logger.info(f"Successfully deleted song: {song_id}")
        return jsonify({"message": "Song deleted successfully"}), 200

    except Exception as e:
        current_app.logger.error(f"Error deleting song '{song_id}': {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred while deleting the song."}), 500