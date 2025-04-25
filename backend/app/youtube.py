# backend/app/youtube.py
import json
import os
import yt_dlp
import logging
from flask import current_app, request, jsonify, Blueprint
from pathlib import Path
from .file_management import (
    get_song_dir, get_thumbnail_path, download_image,
    create_initial_metadata, write_song_metadata
)
from .musicbrainz import enhance_metadata_with_musicbrainz

youtube_bp = Blueprint('youtube', __name__, url_prefix='/api/youtube')

def search_youtube(query, max_results=10):
    """
    Search YouTube for videos matching the query.

    Args:
        query (str): Search query
        max_results (int): Maximum number of results to return

    Returns:
        list: List of video information dictionaries
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'extract_flat': True,
        'force_generic_extractor': False,
        'format': 'bestaudio',
        'default_search': 'ytsearch',
        'max_downloads': max_results
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        search_query = f"ytsearch{max_results}:{query}"
        info = ydl.extract_info(search_query, download=False)

        if 'entries' not in info:
            return []

        results = []
        for entry in info['entries']:
            if entry:
                # Use thumbnail URL or generate one from video ID if not available
                video_id = entry.get('id', '')
                thumbnail = entry.get('thumbnail', '')
                if not thumbnail and video_id:
                    thumbnail = f"https://img.youtube.com/vi/{video_id}/0.jpg"

                results.append({
                    'id': video_id,
                    'title': entry.get('title', 'Unknown Title'),
                    'uploader': entry.get('uploader', 'Unknown Uploader'),
                    'duration': entry.get('duration', 0),
                    'thumbnail': thumbnail,
                    'url': f"https://www.youtube.com/watch?v={video_id}"
                })

        return results

@youtube_bp.route('/search', methods=['POST'])
def search_youtube_route():
    data = request.json
    query = data.get('query', '')
    max_results = data.get('max_results', 10)

    if not query:
        return jsonify({'error': 'Query is required'}), 400

    try:
        results = search_youtube(query, max_results)
        return jsonify({'results': results})
    except Exception as e:
        current_app.logger.error(f"YouTube search error: {str(e)}")
        return jsonify({'error': f'Failed to search YouTube: {str(e)}'}), 500

def download_youtube_audio(video_id, output_dir=None, user_title=None, user_artist=None):
    """
    Download audio from a YouTube video and queue it for processing.
    Also downloads thumbnail and creates basic metadata.
    
    Args:
        video_id (str): YouTube video ID
        output_dir (str): Directory for temporary downloads
        user_title (str, optional): User-provided song title
        user_artist (str, optional): User-provided artist name
    """
    from flask import current_app
    from .main import create_job, start_processing_job
    from . import config
    from .file_management import generate_directory_name, parse_title_artist

    # First, extract info without downloading
    ydl_opts_info = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,  # Don't download yet
    }

    try:
        # Step 1: Get video info first
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            logging.info(f"Extracting info for YouTube video {video_id}")
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)

            if info is None:
                raise Exception(f"Failed to get info for video with ID {video_id}")

            # Step 2: Parse artist and title from YouTube title
            youtube_title = info.get('title', 'Unknown')
            title, artist = parse_title_artist(youtube_title)

            # Override with user-provided metadata if available
            if user_title:
                title = user_title
            if user_artist:
                artist = user_artist

            # Step 3: Generate meaningful directory name
            dir_name = generate_directory_name(artist, title)

            # Step 4: Create song directory
            song_dir = get_song_dir(dir_name)
            song_dir.mkdir(parents=True, exist_ok=True)

            # Now continue with the download to the proper directory
            output_template = os.path.join(output_dir, f"{video_id}.%(ext)s")

            # Configure yt-dlp for actual download
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': output_template,
                'quiet': False,
                'no_warnings': True,
                'ignoreerrors': False,
            }

            # Step 5: Download the audio
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
                ydl_download.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)

                # Determine downloaded file path
                filename = ydl_download.prepare_filename(info)
                temp_mp3_path = os.path.splitext(filename)[0] + '.mp3'

                if not os.path.exists(temp_mp3_path):
                    raise Exception(f"Downloaded file {temp_mp3_path} does not exist")

                # Move the MP3 file to the final song directory
                final_mp3_path = song_dir / f"original.mp3"
                import shutil
                shutil.move(temp_mp3_path, final_mp3_path)

            # Step 6: Download thumbnail
            thumbnail_url = info.get('thumbnail')
            thumbnail_path = None
            has_thumbnail = False
            if thumbnail_url:
                thumbnail_path = get_thumbnail_path(song_dir)
                logging.info(f"Downloading thumbnail from {thumbnail_url}")
                has_thumbnail = download_image(thumbnail_url, thumbnail_path)

            # Step 7: Create initial metadata
            youtube_metadata = {
                'id': info.get('id', video_id),
                'title': title,
                'artist': artist,
                'url': info.get('webpage_url'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'channel_id': info.get('channel_id'),
                'upload_date': info.get('upload_date'),
                'description': info.get('description'),
                'view_count': info.get('view_count'),
                'like_count': info.get('like_count'),
                'thumbnail': thumbnail_url
            }

            initial_metadata = create_initial_metadata(
                Path(final_mp3_path),
                song_dir,
                info.get('duration', 0),
                youtube_metadata
            )

            # Step 8: Create job record using the directory name
            from .main import create_job
            job = create_job(os.path.basename(final_mp3_path), job_id=dir_name)
            if not job:
                raise Exception("Failed to create processing job record")

            # Step 9: Queue the job for processing
            from .main import start_processing_job
            processing_result = start_processing_job(job, Path(final_mp3_path))

            # Return comprehensive info
            return {
                'id': info.get('id', video_id),
                'title': title,
                'artist': artist,
                'filepath': str(final_mp3_path),
                'filename': final_mp3_path.name,
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'job_id': job.id,
                'song_dir': str(song_dir),
                'song_id': dir_name,  # Include song_id for subsequent API calls
                'has_thumbnail': has_thumbnail,
                'job_status': job.status.value,
                'task_id': processing_result.get('task_id')
            }

    except Exception as e:
        logging.error(f"Error processing YouTube video: {e}")
        raise

@youtube_bp.route('/download', methods=['POST'])
def download_youtube_route():
    data = request.json
    video_id = data.get('video_id', '')
    user_title = data.get('title')
    user_artist = data.get('artist')

    if not video_id:
        return jsonify({'error': 'Video ID is required'}), 400

    try:
        TEMP_DOWNLOADS_DIR = current_app.config.get('TEMP_DOWNLOADS_DIR', 'uploads')
        # Pass user-provided metadata to the download function
        result = download_youtube_audio(video_id, TEMP_DOWNLOADS_DIR, 
                                       user_title=user_title, 
                                       user_artist=user_artist)

        response_data = {
            'success': True,
            'file': result['filepath'],
            'metadata': {
                'id': result['id'],
                'title': result['title'],
                'duration': result['duration'],
                'uploader': result['uploader'],
                'has_thumbnail': result.get('has_thumbnail', False),
                'has_cover_art': result.get('has_cover_art', False),
                'song_dir': result.get('song_dir')
            },
            'processing': {
                'job_id': result['job_id'],
                'status': result['job_status'],
                'task_id': result['task_id']
            }
        }
        return jsonify(response_data), 202
    except Exception as e:
        current_app.logger.error(f"YouTube download error: {str(e)}")
        return jsonify({'error': f'Failed to download from YouTube: {str(e)}'}), 500

@youtube_bp.route('/parse-metadata', methods=['POST'])
def parse_youtube_metadata():
    """Parse metadata (title and artist) from a YouTube video."""
    data = request.json
    video_id = data.get('video_id')

    if not video_id:
        return jsonify({'error': 'Video ID is required'}), 400

    try:
        # Extract video info without downloading
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)

            if not info:
                return jsonify({'error': 'Failed to extract video info'}), 500

            youtube_title = info.get('title', 'Unknown')
            title, artist = parse_title_artist(youtube_title)

            return jsonify({'title': title, 'artist': artist}), 200

    except Exception as e:
        logging.error(f"Error parsing YouTube metadata: {e}")
        return jsonify({'error': 'Failed to parse metadata'}), 500