# backend/app/services/interfaces/youtube_service.py
from typing import Protocol, List, Dict, Any, Optional, Tuple, runtime_checkable
from ...db.models import SongMetadata


@runtime_checkable
class YouTubeServiceInterface(Protocol):
    """Interface for YouTube Service to enable dependency injection and testing"""
    
    def search_videos(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search YouTube for videos matching the query"""
        ...
    
    def download_video(
        self, 
        video_id_or_url: str, 
        song_id: str = None,
        artist: str = None,
        title: str = None
    ) -> Tuple[str, SongMetadata]:
        """Download video and extract metadata, return (song_id, metadata)"""
        ...
    
    def extract_video_info(self, video_id_or_url: str) -> Dict[str, Any]:
        """Extract video information without downloading"""
        ...
    
    def validate_video_url(self, url: str) -> bool:
        """Validate if URL is a valid YouTube video URL"""
        ...
    
    def get_video_id_from_url(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        ...
    
    def download_and_process_async(
        self,
        video_id_or_url: str,
        artist: str = None,
        title: str = None,
        song_id: str = None
    ) -> str:
        """Download video and queue for audio processing, return job/song ID"""
        ...
