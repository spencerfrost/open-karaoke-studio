# backend/app/youtube.py
import json
import os
import yt_dlp
from flask import current_app

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

def download_youtube_audio(video_id, output_dir=None):
    """
    Download audio from a YouTube video and queue it for processing.
    
    Args:
        video_id (str): YouTube video ID
        output_dir (str): Directory to save the downloaded audio file
    
    Returns:
        dict: Information about the downloaded file and processing job
    """
    from flask import current_app
    from .main import create_job, start_processing_job
    from pathlib import Path

    if output_dir is None:
        output_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a unique filename based on video ID
    output_template = os.path.join(output_dir, f"{video_id}.%(ext)s")
    
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
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
        
        if info is None:
            raise Exception(f"Failed to download video with ID {video_id}")
        
        # Determine the downloaded file path
        filename = ydl.prepare_filename(info)
        mp3_path = os.path.splitext(filename)[0] + '.mp3'
        
        if not os.path.exists(mp3_path):
            raise Exception(f"Downloaded file {mp3_path} does not exist")
        
        # Create a job for processing (reusing logic from main.py)
        job = create_job(os.path.basename(mp3_path))
        if not job:
            raise Exception("Failed to create processing job record")

        # Queue the job for processing
        processing_result = start_processing_job(job, Path(mp3_path))

        return {
            'id': info.get('id', video_id),
            'title': info.get('title', 'Unknown'),
            'filepath': mp3_path,
            'filename': os.path.basename(mp3_path),
            'duration': info.get('duration', 0),
            'uploader': info.get('uploader', 'Unknown'),
            'job_id': job.id,
            'job_status': job.status.value,
            'task_id': processing_result.get('task_id')
        }