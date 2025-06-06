# backend/app/services/interfaces/__init__.py
"""
Service interfaces for dependency injection and testing
"""

from .audio_service import AudioServiceInterface
from .file_service import FileServiceInterface
from .lyrics_service import LyricsServiceInterface
from .song_service import SongServiceInterface
from .youtube_service import YouTubeServiceInterface

__all__ = [
    "AudioServiceInterface",
    "FileServiceInterface",
    "LyricsServiceInterface", 
    "SongServiceInterface",
    "YouTubeServiceInterface",
]
