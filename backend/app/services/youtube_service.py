# backend/app/services/youtube_service.py
import uuid
import os
import yt_dlp
import re
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timezone

from flask import current_app
from .file_management import (
    get_song_dir,
    get_thumbnail_path,
    download_image,
)
from ..db.database import create_or_update_song
from ..db.models import SongMetadata


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
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "default_search": "ytsearch",
        "noplaylist": True,
    }

    search_term = f"ytsearch{max_results}:{query}"
    results = []

    try:
        current_app.logger.info(f"Starting YouTube search with term: {search_term}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_term, download=False)
            current_app.logger.info(
                f"Search returned info: {bool(info)}, has entries: {'entries' in info}"
            )
            if "entries" in info:
                for entry in info["entries"]:
                    results.append(
                        {
                            "id": entry.get("id"),
                            "title": entry.get("title"),
                            "url": f"https://www.youtube.com/watch?v={entry.get('id')}",
                            "channel": entry.get("channel") or entry.get("uploader"),
                            "channelId": entry.get("channel_id")
                            or entry.get("uploader_id"),
                            "thumbnail": (
                                entry.get("thumbnails")[0]["url"]
                                if entry.get("thumbnails")
                                else None
                            ),
                            "duration": entry.get("duration"),
                        }
                    )
                current_app.logger.info(f"Found {len(results)} search results")
            else:
                current_app.logger.warning(
                    f"YouTube search returned no entries. Info keys: {info.keys() if info else 'None'}"
                )
        return results
    except Exception as e:
        current_app.logger.error(f"YouTube search failed: {e}", exc_info=True)
        return []


def download_from_youtube(
    url: str, artist: str, song_title: str, song_id: str = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Download a song from YouTube, save it to the temporary directory,
    then move it to the song library and create metadata.

    Args:
        url (str): YouTube URL
        artist (str): Artist name
        song_title (str): Song title
        song_id (str, optional): Existing song ID to use. If not provided, generates a new one.

    Returns:
        Tuple[str, Dict[str, Any]]: (song_id, metadata)
    """
    current_app.logger.info(f"Downloading from YouTube: {url}")

    try:
        # Use provided song_id or generate a new one
        if not song_id:
            song_id = str(uuid.uuid4())
        song_dir = get_song_dir(song_id)
        outtmpl = os.path.join(song_dir, "original.%(ext)s")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                }
            ],
            "quiet": False,
            "no_warnings": True,
            "writeinfojson": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise ValueError(f"Could not download video info from {url}")

        if not os.path.exists(song_dir):
            raise FileNotFoundError(
                f"Download completed but file not found: {song_dir}"
            )

        thumbnails = info.get("thumbnails", [])
        thumbnail_url = thumbnails[0]["url"] if thumbnails else None
        if thumbnail_url:
            thumbnail_path = get_thumbnail_path(song_dir)
            current_app.logger.info(f"Downloading thumbnail from {thumbnail_url}")
            download_image(thumbnail_url, thumbnail_path)

        # Create SongMetadata object
        metadata = SongMetadata(
            title=song_title,
            artist=artist,
            duration=info.get("duration"),
            dateAdded=datetime.now(timezone.utc),
            source="youtube",
            sourceUrl=url,
            videoId=info.get("id"),
            videoTitle=info.get("title"),
            uploader=info.get("uploader"),
            channel=info.get("channel"),
        )

        # Process thumbnail
        thumbnails = info.get("thumbnails", [])
        thumbnail_url = None
        if thumbnails:
            best_thumb = max(thumbnails, key=lambda t: t.get("preference", -9999))
            thumbnail_url = best_thumb.get("url")
        elif info.get("thumbnail"):
            thumbnail_url = info.get("thumbnail")
            
        if thumbnail_url:
            thumbnail_path = get_thumbnail_path(song_dir)
            current_app.logger.info(f"Downloading thumbnail from {thumbnail_url}")
            if download_image(thumbnail_url, thumbnail_path):
                metadata.thumbnail = f"{song_id}/thumbnail.jpg"

        # Pass the SongMetadata object directly to create_or_update_song
        create_or_update_song(song_id, metadata)

        return song_id, metadata

    except Exception as e:
        current_app.logger.error(f"Failed to download from YouTube: {e}")
        raise
