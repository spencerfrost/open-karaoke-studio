# backend/app/services/interfaces/lyrics_service.py
# pylint: disable=unnecessary-ellipsis
from typing import Any, Optional, Protocol


class LyricsServiceInterface(Protocol):
    """Interface for lyrics operations"""

    def search_lyrics(self, query: str) -> list[dict[str, Any]]:
        """Search for lyrics using a general query string

        Args:
            query: Search query string

        Returns:
            List of lyrics records matching the query
        """
        ...

    def get_lyrics(self, song_id: str) -> Optional[str]:
        """Get lyrics for a song from storage

        Args:
            song_id: Unique identifier for the song

        Returns:
            Lyrics text if found, None otherwise
        """
        ...

    def save_lyrics(self, song_id: str, lyrics: str) -> bool:
        """Save lyrics for a song to storage

        Args:
            song_id: Unique identifier for the song
            lyrics: Lyrics text to save

        Returns:
            True if successful, False otherwise
        """
        ...

    def validate_lyrics(self, lyrics: str) -> bool:
        """Validate lyrics format and completeness

        Args:
            lyrics: Lyrics text to validate

        Returns:
            True if valid, False otherwise
        """
        ...

    def lyrics_file_exists(self, song_id: str) -> bool:
        """Check if lyrics file exists for a song

        Args:
            song_id: Unique identifier for the song

        Returns:
            True if lyrics file exists, False otherwise
        """
        ...

    def get_lyrics_file_path(self, song_id: str) -> str:
        """Get path to lyrics file for a song

        Args:
            song_id: Unique identifier for the song

        Returns:
            Path to the lyrics file
        """
        ...

    def create_default_lyrics(self, song_id: str) -> str:
        """Create default lyrics for a song

        Args:
            song_id: Unique identifier for the song

        Returns:
            Default lyrics text
        """
        ...
