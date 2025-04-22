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
                results.append({
                    'id': entry.get('id', ''),
                    'title': entry.get('title', 'Unknown Title'),
                    'uploader': entry.get('uploader', 'Unknown Uploader'),
                    'duration': entry.get('duration', 0),
                    'thumbnail': entry.get('thumbnail', ''),
                    'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                })
        
        return results

def download_youtube_audio(video_id, output_dir=None):
    """
    Download audio from a YouTube video.
    
    Args:
        video_id (str): YouTube video ID
        output_dir (str): Directory to save the downloaded audio file
    
    Returns:
        dict: Information about the downloaded file
    """
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
        
        return {
            'id': info.get('id', video_id),
            'title': info.get('title', 'Unknown'),
            'filepath': mp3_path,
            'filename': os.path.basename(mp3_path),
            'duration': info.get('duration', 0),
            'uploader': info.get('uploader', 'Unknown')
        }