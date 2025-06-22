# backend/app/services/interfaces/youtube_service.py
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class YouTubeServiceInterface(Protocol):
    """Interface for YouTube Service to enable dependency injection and testing"""

    def search_videos(self, query: str, max_results: int = 10) -> "list[dict[str, Any]]":
        """Search YouTube for videos matching the query"""
        ...

    def download_video(
        self,
        video_id_or_url: str,
        song_id: Optional[str] = None,
        artist: Optional[str] = None,
        title: Optional[str] = None,
    ) -> "tuple[str, dict[str, Any]]":
        """Download video and extract metadata, return (song_id, metadata_dict)

        Returns:
            tuple: (song_id, metadata_dict) where metadata_dict contains raw metadata
                   that can be passed directly to create_or_update_song()
        """
        ...

    def extract_video_info(self, video_id_or_url: str) -> "dict[str, Any]":
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
        artist: Optional[str] = None,
        title: Optional[str] = None,
        song_id: Optional[str] = None,
    ) -> str:
        """Download video and queue for audio processing, return job/song ID"""
        ...
