# backend/app/services/interfaces/song_service.py
"""
Song Service Interface for dependency injection and testing
"""

from typing import Protocol, List, Optional
from ...db.models import Song, SongMetadata, DbSong


class SongServiceInterface(Protocol):
    """Interface for Song Service to enable dependency injection and testing"""
    
    def get_all_songs(self) -> List[Song]:
        """Get all songs with automatic filesystem sync if needed"""
        ...
    
    def get_song_by_id(self, song_id: str) -> Optional[Song]:
        """Get song by ID"""
        ...
    
    def search_songs(self, query: str) -> List[Song]:
        """Search songs by title/artist"""
        ...
    
    def create_song_from_metadata(
        self, 
        song_id: str, 
        metadata: SongMetadata
    ) -> Song:
        """Create song from metadata"""
        ...
    
    def update_song_metadata(
        self, 
        song_id: str, 
        metadata: SongMetadata
    ) -> Optional[Song]:
        """Update song metadata"""
        ...
    
    def delete_song(self, song_id: str) -> bool:
        """Delete song and associated files"""
        ...
    
    def sync_with_filesystem(self) -> int:
        """Sync database with filesystem, return count of synced songs"""
        ...
