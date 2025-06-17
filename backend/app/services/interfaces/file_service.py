# backend/app/services/interfaces/file_service.py
from pathlib import Path
from typing import Optional, Protocol


class FileServiceInterface(Protocol):
    """Interface for file system operations related to song storage"""

    def ensure_library_exists(self) -> None:
        """Create base library directory if it doesn't exist"""
        ...

    def get_song_directory(self, song_id: str) -> Path:
        """Get or create song directory"""
        ...

    def get_vocals_path(self, song_id: str, extension: str = ".wav") -> Path:
        """Get vocals file path"""
        ...

    def get_instrumental_path(self, song_id: str, extension: str = ".wav") -> Path:
        """Get instrumental file path"""
        ...

    def get_original_path(self, song_id: str, extension: str = ".mp3") -> Path:
        """Get original file path"""
        ...

    def get_thumbnail_path(self, song_id: str) -> Path:
        """Get thumbnail file path"""
        ...

    def get_cover_art_path(self, song_id: str) -> Path:
        """Get cover art file path"""
        ...

    def delete_song_files(self, song_id: str) -> bool:
        """Delete all files for a song"""
        ...

    def get_processed_song_ids(self) -> list[str]:
        """Get list of song IDs that have directories in the library"""
        ...

    def song_directory_exists(self, song_id: str) -> bool:
        """Check if song directory exists"""
        ...

    def get_file_size(self, file_path: Path) -> Optional[int]:
        """Get file size in bytes"""
        ...

    def list_song_files(self, song_id: str) -> list[Path]:
        """List all files in a song directory"""
        ...
