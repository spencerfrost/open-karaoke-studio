# backend/app/api/youtube.py
from flask import Blueprint, request, jsonify, current_app
from pathlib import Path
import logging
import os
import json
from datetime import datetime, timezone

from ..services.youtube_service import search_youtube, download_from_youtube, parse_title_artist
from ..services.file_management import get_song_dir
from ..services.lyrics_service import fetch_lyrics
from ..tasks.tasks import process_audio_task, job_store
from ..db.models import Job, JobStatus
from ..db.database import create_or_update_song

youtube_bp = Blueprint('youtube', __name__, url_prefix='/api/youtube')

@youtube_bp.route('/search', methods=['POST'])
def search_youtube_endpoint():
    """Endpoint to search YouTube for videos."""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Missing query parameter'}), 400

        query = data['query']
        max_results = data.get('maxResults', 10)

        current_app.logger.info(f"Searching YouTube for: {query}")
        results = search_youtube(query, max_results)
        logging.info(f"Search results: {json.dumps(results, indent=2)}")
        return jsonify(results)
    except Exception as e:
        current_app.logger.error(f"YouTube search error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Error during YouTube search: {str(e)}'}), 500


@youtube_bp.route('/download', methods=['POST'])
def download_youtube_endpoint():
    """Endpoint to download a video from YouTube and fetch lyrics."""
    try:
        data = request.get_json()
        if not data or 'videoId' not in data:
            return jsonify({'error': 'Missing videoId parameter'}), 400
        
        artist = data.get('artist', '')
        song_title = data.get('title', '')
        album = data.get('album', '')
        
        song_id, metadata = download_from_youtube(data['videoId'], artist, song_title)
        
        song_dir = get_song_dir(song_id)
        original_file_path = song_dir / "original.mp3"
        
        if original_file_path.exists():
            current_app.logger.info(f"Submitting audio processing task for song {song_id}")
            try:
                job = Job(
                    id=song_id,
                    filename=original_file_path.name,
                    status=JobStatus.PENDING,
                    created_at=datetime.now(timezone.utc)
                )
                job_store.save_job(job)
                
                task = process_audio_task.delay(song_id)
                
                job.task_id = task.id
                job.status = JobStatus.PROCESSING
                job_store.save_job(job)
            except Exception as task_error:
                current_app.logger.error(f"Failed to submit processing task: {task_error}", exc_info=True)
        else:
            current_app.logger.error(f"Original audio file not found at {original_file_path}")
        
        params = {
            'title': song_title,
            'artist': artist,
        }
        if album:
            params['album'] = album
            
        lyrics_data = fetch_lyrics(**params)
        
        if lyrics_data and lyrics_data[0]:
            metadata = metadata.copy(update={
                'lyrics': lyrics_data[0].get('lyrics'),
                'syncedLyrics': lyrics_data[0].get('syncedLyrics')
            })
        else:
            current_app.logger.warning(f"No lyrics found for {metadata['title']} by {metadata['artist']}")
        
        response = {
            'songId': song_id,
            'metadata': metadata.dict(),  # Convert Pydantic model to dictionary
            'status': 'downloaded',
        }
        
        create_or_update_song(song_id, metadata)
        
        return jsonify(response), 200
    except Exception as e:
        current_app.logger.error(f"YouTube download error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to download from YouTube: {str(e)}'}), 500


@youtube_bp.route('/parse-metadata', methods=['POST'])
def parse_metadata_endpoint():
    """Endpoint to parse video title into artist and title."""
    try:
        data = request.get_json()
        if not data or 'videoTitle' not in data:
            return jsonify({'error': 'Missing videoTitle parameter'}), 400

        youtube_title = data['videoTitle']
        title, artist = parse_title_artist(youtube_title)
        
        return jsonify({
            'title': title,
            'artist': artist,
            'original': youtube_title
        })
    except Exception as e:
        current_app.logger.error(f"Metadata parsing error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to parse metadata: {str(e)}'}), 500