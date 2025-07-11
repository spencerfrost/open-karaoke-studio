# backend/app/services/file_service.py
import logging
import shutil
from pathlib import Path
from typing import Optional

from app.config import get_config
from app.exceptions import ServiceError

from .interfaces.file_service import FileServiceInterface

logger = logging.getLogger(__name__)


class FileService(FileServiceInterface):
    """Handle file system operations for songs"""

    def __init__(self, base_library_dir: Optional[Path] = None):
        config = get_config()
        self.base_library_dir = base_library_dir or config.LIBRARY_DIR

    def ensure_library_exists(self) -> None:
        """Create base library directory if it doesn't exist"""
        try:
            self.base_library_dir.mkdir(parents=True, exist_ok=True)
            logger.debug("Ensured library directory exists: %s", self.base_library_dir)
        except Exception as e:
            logger.error(
                "Failed to create library directory %s: %s", self.base_library_dir, e
            )
            raise ServiceError(f"Failed to create library directory: {e}")

    def get_song_directory(self, song_id: str) -> Path:
        """Get or create song directory"""
        try:
            self.ensure_library_exists()
            song_dir = self.base_library_dir / song_id
            song_dir.mkdir(parents=True, exist_ok=True)
            return song_dir
        except Exception as e:
            logger.error("Failed to create song directory for %s: %s", song_id, e)
            raise ServiceError(f"Failed to create song directory for {song_id}: {e}")

    def get_vocals_path(self, song_id: str, extension: str = ".wav") -> Path:
        """Get vocals file path"""
        return self.get_song_directory(song_id) / f"vocals{extension}"

    def get_instrumental_path(self, song_id: str, extension: str = ".wav") -> Path:
        """Get instrumental file path"""
        return self.get_song_directory(song_id) / f"instrumental{extension}"

    def get_original_path(self, song_id: str, extension: str = ".mp3") -> Path:
        """Get original file path (always 'original.mp3' in the song directory)"""
        return self.get_song_directory(song_id) / f"original{extension}"

    def get_thumbnail_path(self, song_id: str) -> Path:
        """Get thumbnail file path"""
        return self.get_song_directory(song_id) / "thumbnail.jpg"

    def get_cover_art_path(self, song_id: str) -> Path:
        """Get cover art file path"""
        return self.get_song_directory(song_id) / "cover.jpg"

    def delete_song_files(self, song_id: str) -> bool:
        """Delete all files for a song"""
        try:
            song_dir = self.base_library_dir / song_id
            if song_dir.exists() and song_dir.is_dir():
                shutil.rmtree(song_dir)
                logger.info("Deleted song directory: %s", song_dir)
                return True
            else:
                logger.warning("Song directory does not exist: %s", song_dir)
                return False
        except Exception as e:
            logger.error("Error deleting files for song %s: %s", song_id, e)
            raise ServiceError(f"Failed to delete files for song {song_id}: {e}")

    def get_processed_song_ids(self) -> list[str]:
        """Get list of song IDs that have directories in the library"""
        try:
            if not self.base_library_dir.exists():
                return []

            song_ids = [
                d.name
                for d in self.base_library_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]

            logger.debug("Found %s processed song directories", len(song_ids))
            return song_ids

        except Exception as e:
            logger.error("Error scanning library directory: %s", e)
            raise ServiceError(f"Failed to scan library directory: {e}")

    def song_directory_exists(self, song_id: str) -> bool:
        """Check if song directory exists"""
        song_dir = self.base_library_dir / song_id
        return song_dir.exists() and song_dir.is_dir()

    def get_file_size(self, file_path: Path) -> Optional[int]:
        """Get file size in bytes"""
        try:
            if file_path.exists() and file_path.is_file():
                return file_path.stat().st_size
            return None
        except Exception as e:
            logger.error("Error getting file size for %s: %s", file_path, e)
            return None

    def list_song_files(self, song_id: str) -> list[Path]:
        """List all files in a song directory"""
        try:
            song_dir = self.base_library_dir / song_id
            if not song_dir.exists():
                return []

            return [f for f in song_dir.iterdir() if f.is_file()]
        except Exception as e:
            logger.error("Error listing files for song %s: %s", song_id, e)
            raise ServiceError(f"Failed to list files for song {song_id}: {e}")
