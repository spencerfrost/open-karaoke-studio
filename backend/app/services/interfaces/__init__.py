# backend/app/services/interfaces/__init__.py
"""
Service interfaces for dependency injection and testing
"""

from .audio_service import AudioServiceInterface
from .file_service import FileServiceInterface
from .lyrics_service import LyricsServiceInterface
from .metadata_service import MetadataServiceInterface
from .youtube_service import YouTubeServiceInterface

__all__ = [
    "AudioServiceInterface",
    "FileServiceInterface",
    "LyricsServiceInterface",
    "MetadataServiceInterface",
    "YouTubeServiceInterface",
]
