# backend/app/services/youtube_service.py
import uuid
import os
import yt_dlp
import logging
import shutil
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from flask import current_app
from ..config import Config as config
from .file_management import (
    get_song_dir, get_thumbnail_path, download_image,
    create_initial_metadata, write_song_metadata
)
from .musicbrainz_service import enhance_metadata_with_musicbrainz

def search_youtube(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search YouTube for videos matching the query.
    
    Args:
        query (str): Search query
        max_results (int, optional): Maximum number of results to return. Defaults to 10.
        
    Returns:
        List[Dict[str, Any]]: List of video information objects
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'default_search': 'ytsearch',
        'noplaylist': True
    }
    
    search_term = f"ytsearch{max_results}:{query}"
    results = []
    
    try:
        logging.info(f"Starting YouTube search with term: {search_term}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_term, download=False)
            logging.info(f"Search returned info: {bool(info)}, has entries: {'entries' in info}")
            if 'entries' in info:
                for entry in info['entries']:
                    results.append({
                        'id': entry.get('id'),
                        'title': entry.get('title'),
                        'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                        'channel': entry.get('channel') or entry.get('uploader'),
                        'channelId': entry.get('channel_id') or entry.get('uploader_id'),
                        'thumbnail': entry.get('thumbnails')[0]['url'] if entry.get('thumbnails') else None,
                        'duration': entry.get('duration'),
                    })
                logging.info(f"Found {len(results)} search results")
            else:
                logging.warning(f"YouTube search returned no entries. Info keys: {info.keys() if info else 'None'}")
        return results
    except Exception as e:
        logging.error(f"YouTube search failed: {e}", exc_info=True)
        return []


def download_from_youtube(url: str, artist: str, song_title: str) -> Tuple[str, Dict[str, Any]]:
    """
    Download a song from YouTube, save it to the temporary directory,
    then move it to the song library and create metadata.
    
    Args:
        url (str): YouTube URL
        artist (str): Artist name
        song_title (str): Song title
        
    Returns:
        Tuple[str, Dict[str, Any]]: (song_id, metadata)
    """
    logging.info(f"Downloading from YouTube: {url}")
    logging.info(f"Artist: {artist}, Title: {song_title}")
    
    try:
        song_id = str(uuid.uuid4())
        song_dir = get_song_dir(song_id)
        logging.info(f"Song directory: {song_dir}")
        outtmpl = os.path.join(song_dir, "original.%(ext)s")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': outtmpl,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'quiet': False,
            'no_warnings': True,
            'writeinfojson': True,
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise ValueError(f"Could not download video info from {url}")
        
        logging.info(f"Saving original file to {song_dir}")
        

        if not os.path.exists(song_dir):
            raise FileNotFoundError(f"Download completed but file not found: {song_dir}")
        
        thumbnails = info.get('thumbnails', [])
        thumbnail_url = thumbnails[0]['url'] if thumbnails else None
        if thumbnail_url:
            thumbnail_path = get_thumbnail_path(song_dir)
            logging.info(f"Downloading thumbnail from {thumbnail_url}")
            download_image(thumbnail_url, thumbnail_path)
            
        
        
        metadata = create_initial_metadata(
            song_dir=song_dir,
            title=song_title,
            artist=artist,
            duration=info.get('duration'),
            youtube_info={
                'videoId': info.get('id'),
                'videoTitle': info.get('title'),
                'uploader': info.get('uploader'),
                'channel': info.get('channel'),
                # 'description': info.get('description'),
                'upload_date': info.get('upload_date'),
                'thumbnail': thumbnail_url,
                'sourceUrl': url,
            },
        )
        
        # Try to enhance with MusicBrainz data
        enhanced_metadata = enhance_metadata_with_musicbrainz(metadata, song_dir)
        if enhanced_metadata:
            metadata = enhanced_metadata
        
        # Save metadata to JSON file
        write_song_metadata(song_id, metadata)
        
        # Return the song ID (directory name) and metadata
        metadata_dict = {
            "id": song_id,
            "title": metadata.title,
            "artist": metadata.artist,
            "duration": metadata.duration,
            "source": "youtube", 
            "sourceUrl": url
        }
        
        return song_id, metadata_dict
        
    except Exception as e:
        logging.error(f"Failed to download from YouTube: {e}")
        raise


def parse_title_artist(youtube_title: str) -> Tuple[str, str]:
    """
    Try to parse YouTube video title into song title and artist.
    
    Args:
        youtube_title (str): YouTube video title
        
    Returns:
        Tuple[str, str]: (title, artist)
    """
    # Common patterns to extract title and artist from YouTube video titles
    patterns = [
        # "Artist - Title" format
        r'^(.*?)\s*-\s*(.*?)$',
        # "Artist "Title"" format
        r'^(.*?)\s*[\'"]+(.*?)[\'"]+$',
        # "Title by Artist" format
        r'^(.*?)\s+by\s+(.*?)$',
        # "Title || Artist" format
        r'^(.*?)\s*[\|]+\s*(.*?)$',
        # "Artist: Title" format
        r'^(.*?):\s*(.*?)$',
    ]
    
    for pattern in patterns:
        match = re.match(pattern, youtube_title, re.IGNORECASE)
        if match:
            parts = match.groups()
            if len(parts) == 2:
                # Determine which part is artist and which is title
                part1, part2 = parts
                
                # If the second part is clearly an artist (contains "official", etc.)
                if re.search(r'official|music\s*video|audio|lyrics', part2, re.IGNORECASE):
                    return part1.strip(), ""  # Part 1 is the full title, no artist
                
                # For "Artist - Title" pattern, part1 is the artist
                if re.match(r'^(.*?)\s*-\s*(.*?)$', youtube_title):
                    return part2.strip(), part1.strip()
                
                # For "Title by Artist" pattern, part2 is the artist
                if re.match(r'^(.*?)\s+by\s+(.*?)$', youtube_title):
                    return part1.strip(), part2.strip()
                
                # Default: assume part1 is artist, part2 is title (most common)
                return part2.strip(), part1.strip()
    
    # If no pattern matches, return the whole title and empty artist
    return youtube_title, ""