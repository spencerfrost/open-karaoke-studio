# backend/app/api/youtube.py
from flask import Blueprint, request, jsonify, current_app
from pathlib import Path
import logging
import os
import json
from datetime import datetime, timezone

# Import from services
from ..services.youtube_service import search_youtube, download_from_youtube, parse_title_artist
from ..services.file_management import get_song_dir
from ..services.lyrics_service import fetch_lyrics, update_song_with_lyrics
from ..tasks.tasks import process_audio_task, job_store
from ..db.models import Job, JobStatus

# Define blueprint
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
        
        logging.info(f"Received data for download: {json.dumps(data, indent=2)}")

        video_id = data['videoId']
        artist = data.get('artist', '')
        song_title = data.get('title', '')
        
        current_app.logger.info(f"Downloading YouTube video: {video_id}")
        
        # Call the service function
        song_id, metadata = download_from_youtube(video_id, artist, song_title)
        
        # Send the downloaded audio to the audio processing service
        song_dir = get_song_dir(song_id)
        original_file_path = song_dir / "original.mp3"
        
        if original_file_path.exists():
            current_app.logger.info(f"Submitting audio processing task for song {song_id}")
            try:
                # Create a job record in the database first
                filename = original_file_path.name
                job = Job(
                    id=song_id,
                    filename=filename,
                    status=JobStatus.PENDING,
                    created_at=datetime.now(timezone.utc)
                )
                
                # Save the job to the database
                job_store.save_job(job)

                # Submit the task to Celery with only the job ID
                task = process_audio_task.delay(song_id)  # Only pass the song_id/job_id
                                
                # Update the job with the task ID
                job.task_id = task.id
                job.status = JobStatus.PROCESSING
                job_store.save_job(job)
                
                # Add task ID to the response
                metadata['processingTaskId'] = task.id
                metadata['processingStatus'] = 'processing'
                current_app.logger.info(f"Task submitted successfully with ID: {task.id}")
            except Exception as task_error:
                current_app.logger.error(f"Failed to submit processing task: {task_error}", exc_info=True)
                metadata['processingStatus'] = 'error'
                metadata['processingError'] = f"Failed to queue processing task: {str(task_error)}"
        else:
            current_app.logger.error(f"Original audio file not found at {original_file_path}")
            metadata['processingStatus'] = 'error'
            metadata['processingError'] = 'Original audio file not found'
        
        # Try to fetch and add lyrics if we have enough metadata
        if song_id and metadata and metadata.get('title') and metadata.get('artist'):
            current_app.logger.info(f"Attempting to fetch lyrics for {metadata['title']} by {metadata['artist']}")
            lyrics_data = fetch_lyrics(
                title=metadata['title'], 
                artist=metadata['artist'],
                duration=metadata.get('duration')
            )
            
            if lyrics_data:
                current_app.logger.info(f"Lyrics found! Updating metadata for {song_id}")
                update_song_with_lyrics(song_id, lyrics_data)
                metadata['lyricsFound'] = True
            else:
                current_app.logger.info(f"No lyrics found for {metadata['title']} by {metadata['artist']}")
                metadata['lyricsFound'] = False
        
        response = {
            'songId': song_id,
            'metadata': metadata,
            'status': 'downloaded',
            'processingStatus': metadata.get('processingStatus', 'pending')
        }
        
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