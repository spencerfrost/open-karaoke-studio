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
from ..services.lyrics_service import make_request

song_bp = Blueprint('songs', __name__, url_prefix='/api/songs')

@song_bp.route('', methods=['GET'])
def get_songs():
    """Endpoint to get a list of processed songs with metadata - thin controller using service layer."""
    current_app.logger.info("Received request for /api/songs")
    
    try:
        song_service = SongService()
        songs = song_service.get_all_songs()
        
        # Convert to JSON response format
        response_data = [
            song.model_dump(mode='json') if hasattr(song, 'model_dump') else song.dict() 
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


@song_bp.route('/<string:song_id>/download/<string:track_type>', methods=['GET'])
def download_song_track(song_id: str, track_type: str):
    """Downloads a specific track type (vocals, instrumental, original) for a song."""
    current_app.logger.info(f"Download request for song '{song_id}', track type '{track_type}'")
    track_type = track_type.lower() # Normalize track type
    
    if track_type not in ("vocals", "instrumental", "original"):
        current_app.logger.warning(f"Invalid track type requested: {track_type}")
        return jsonify({"error": "Invalid track type specified. Use 'vocals', 'instrumental', or 'original'."}), 400

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
                current_app.logger.error(f"Attempted download outside library bounds: {track_file}")
                return jsonify({"error": "Access denied"}), 403

            current_app.logger.info(f"Sending {track_type}.mp3 from directory '{song_dir}'")
            return send_from_directory(
                song_dir, # Directory path object
                track_file.name, # Just the filename string - use .name to get just the filename
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
    """Endpoint to get details for a specific song - thin controller using service layer."""
    current_app.logger.info(f"Received request for song details: {song_id}")
    
    try:
        song_service = SongService()
        song = song_service.get_song_by_id(song_id)
        
        if not song:
            return jsonify({"error": f"Song with ID {song_id} not found"}), 404
        
        # Convert to response format
        response = song.model_dump(mode='json') if hasattr(song, 'model_dump') else song.dict()
        
        # Add additional fields from database if needed (legacy compatibility)
        db_song = database.get_song(song_id)
        if db_song:
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
        
        current_app.logger.info(f"Returning details for song {song_id}")
        return jsonify(response), 200
        
    except ServiceError as e:
        current_app.logger.error(f"Service error getting song {song_id}: {e}")
        return jsonify({"error": "Failed to fetch song", "details": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error getting song {song_id}: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@song_bp.route('/<string:song_id>/metadata', methods=['PATCH'])
def update_song_metadata(song_id: str):
    """Endpoint to update song metadata."""
    current_app.logger.info(f"Received metadata update request for song: {song_id}")
    try:
        # Validate that song exists in filesystem
        file_service = FileService()
        song_dir = file_service.get_song_directory(song_id)
        if not song_dir.is_dir():
            current_app.logger.error(f"Song directory not found: {song_dir}")
            return jsonify({"error": "Song not found"}), 404
            
        # Get request data
        update_data = request.get_json()
        if not update_data:
            return jsonify({"error": "No update data provided"}), 400
            
        # Get existing metadata from database
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
                uploader=db_song.uploader,
                uploaderId=db_song.uploader_id,
                channel=db_song.channel,
                channelId=db_song.channel_id,
                description=db_song.description,
                uploadDate=db_song.upload_date,
                mbid=db_song.mbid,
                releaseTitle=db_song.release_title,
                releaseId=db_song.release_id,
                releaseDate=db_song.release_date,
                genre=db_song.genre,
                language=db_song.language,
                lyrics=db_song.lyrics,
                syncedLyrics=db_song.synced_lyrics
            )
        else:
            # Try to get from legacy metadata
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
            
        # Save updated metadata to database
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
    song_id = unquote(song_id)

    # Get song from database to find thumbnail path
    db_song = database.get_song(song_id)
    
    # Construct the path to the thumbnail
    file_service = FileService()
    song_dir = file_service.get_song_directory(song_id)
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
    
    # Try to get from database first
    db_song = database.get_song(song_id)
    
    if db_song:
        # Use database fields
        title = db_song.title
        artist = db_song.artist if db_song.artist.lower() != 'unknown artist' else db_song.channel
        duration = str(int(db_song.duration)) if db_song.duration else None
        album = db_song.release_title
    else:
        # Fall back to file-based approach
        metadata = file_management.read_song_metadata(song_id)
        if not metadata or not metadata.title or not metadata.duration:
            current_app.logger.warning(f"Metadata incomplete for lyrics: {song_id}")
            return jsonify({"error": "Missing metadata (title, duration) for lyrics lookup"}), 400

        # Determine best artist name: prefer metadata.artist, else channel
        artist = metadata.artist if metadata.artist and metadata.artist.lower() != 'unknown artist' else metadata.channel
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
        current_app.logger.error(f"Unexpected error deleting song {song_id}: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@song_bp.route('', methods=['POST'])
def create_song():
    """Create a new song with basic information - thin controller using service layer."""
    current_app.logger.info("Received request to create a new song")
    
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        # Validate required fields
        if not data.get('title'):
            return jsonify({"error": "Song title is required"}), 400
        
        # Generate a unique ID for the song
        song_id = str(uuid.uuid4())
        current_app.logger.info(f"Creating new song with ID: {song_id}")
        
        # Prepare metadata
        metadata = SongMetadata(
            title=data.get('title'),
            artist=data.get('artist', 'Unknown Artist'),
            dateAdded=datetime.now(timezone.utc),
            source=data.get('source'),
            sourceUrl=data.get('sourceUrl'),
            videoId=data.get('videoId'),
            videoTitle=data.get('videoTitle'),
            uploader=data.get('uploader'),
            uploaderId=data.get('uploaderId'),
            channel=data.get('channel'),
            channelId=data.get('channelId'),
            releaseTitle=data.get('album'),
            releaseDate=data.get('year'),
            genre=data.get('genre'),
            language=data.get('language')
        )
        
        # Use service to create song
        song_service = SongService()
        song = song_service.create_song_from_metadata(song_id, metadata)
        
        # Return the song data
        response = {
            "id": song_id,
            "title": song.title,
            "artist": song.artist,
            "album": data.get('album'),
            "dateAdded": song.dateAdded.isoformat() if song.dateAdded else None,
            "status": "pending"
        }
        
        current_app.logger.info(f"Successfully created song: {song_id}")
        return jsonify(response), 201
        
    except ServiceError as e:
        current_app.logger.error(f"Service error creating song: {e}")
        return jsonify({"error": "Failed to create song", "details": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error creating song: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@song_bp.route('/search', methods=['GET'])
def search_songs():
    """Search songs endpoint - thin controller using service layer."""
    query = request.args.get('q', '').strip()
    current_app.logger.info(f"Received search request with query: '{query}'")
    
    if not query:
        return jsonify([])
    
    try:
        song_service = SongService()
        songs = song_service.search_songs(query)
        
        response_data = [
            song.model_dump(mode='json') if hasattr(song, 'model_dump') else song.dict() 
            for song in songs
        ]
        
        current_app.logger.info(f"Found {len(response_data)} songs matching '{query}'")
        return jsonify(response_data)
        
    except ServiceError as e:
        current_app.logger.error(f"Service error searching songs: {e}")
        return jsonify({"error": "Failed to search songs", "details": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error searching songs: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500