# backend/app/services/youtube_service.py
import uuid
import re
import yt_dlp
import logging
from typing import Dict, List, Tuple, Optional, Any, Protocol
from datetime import datetime, timezone
from pathlib import Path

from .interfaces.file_service import FileServiceInterface  
from .interfaces.song_service import SongServiceInterface
from .file_service import FileService
from ..exceptions import ServiceError, ValidationError
from ..db.models import SongMetadata

logger = logging.getLogger(__name__)


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
    
    def download_and_process_async(
        self,
        video_id_or_url: str,
        artist: str = None,
        title: str = None,
        song_id: str = None
    ) -> str:
        """Download video and queue for audio processing, return job/song ID"""
        ...


class YouTubeService(YouTubeServiceInterface):
    """Handle YouTube video operations"""
    
    def __init__(
        self,
        file_service: FileServiceInterface = None,
        song_service: SongServiceInterface = None
    ):
        self.file_service = file_service or FileService()
        self.song_service = song_service  # Injected to avoid circular dependency
    
    def search_videos(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search YouTube for videos matching the query"""
        try:
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

            logger.info(f"Starting YouTube search with term: {search_term}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_term, download=False)
                
                if "entries" in info:
                    for entry in info["entries"]:
                        results.append({
                            "id": entry.get("id"),
                            "title": entry.get("title"),
                            "url": f"https://www.youtube.com/watch?v={entry.get('id')}",
                            "channel": entry.get("channel") or entry.get("uploader"),
                            "channelId": entry.get("channel_id") or entry.get("uploader_id"),
                            "thumbnail": (
                                entry.get("thumbnails")[0]["url"]
                                if entry.get("thumbnails")
                                else None
                            ),
                            "duration": entry.get("duration"),
                        })
                    logger.info(f"Found {len(results)} search results")
                else:
                    logger.warning(f"YouTube search returned no entries")
            
            return results
            
        except Exception as e:
            logger.error(f"YouTube search failed: {e}")
            raise ServiceError(f"Failed to search YouTube: {e}")
    
    def download_video(
        self, 
        video_id_or_url: str, 
        song_id: str = None,
        artist: str = None,
        title: str = None
    ) -> Tuple[str, SongMetadata]:
        """Download video and extract metadata, return (song_id, metadata)"""
        try:
            # Validate URL and extract video ID
            if not self.validate_video_url(video_id_or_url):
                # Assume it's already a video ID
                video_id = video_id_or_url
                url = f"https://www.youtube.com/watch?v={video_id}"
            else:
                url = video_id_or_url
                video_id = self.get_video_id_from_url(url)
                if not video_id:
                    raise ValidationError(f"Could not extract video ID from URL: {url}")
            
            # Generate or use provided song ID
            if not song_id:
                song_id = str(uuid.uuid4())
            
            logger.info(f"Downloading YouTube video {video_id} to song {song_id}")
            
            # Setup download directory
            song_dir = self.file_service.get_song_directory(song_id)
            outtmpl = str(song_dir / "original.%(ext)s")

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

            # Download video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    raise ServiceError(f"Could not download video info from {url}")

            # Verify download completed
            original_file = self.file_service.get_original_path(song_id, ".mp3")
            if not original_file.exists():
                raise ServiceError(f"Download completed but file not found: {original_file}")

            # Extract and create metadata
            metadata = self._extract_metadata_from_youtube_info(info)
            
            # Override with provided metadata if available
            if title:
                metadata.title = title
            if artist:
                metadata.artist = artist
            
            # Download thumbnail if available
            thumbnail_url = self._get_best_thumbnail_url(info)
            if thumbnail_url:
                self._download_thumbnail(song_id, thumbnail_url, metadata)
            
            logger.info(f"Successfully downloaded YouTube video {video_id} as song {song_id}")
            return song_id, metadata
            
        except Exception as e:
            logger.error(f"Failed to download YouTube video {video_id_or_url}: {e}")
            raise ServiceError(f"Failed to download YouTube video: {e}")
    
    def extract_video_info(self, video_id_or_url: str) -> Dict[str, Any]:
        """Extract video information without downloading"""
        try:
            if not self.validate_video_url(video_id_or_url):
                url = f"https://www.youtube.com/watch?v={video_id_or_url}"
            else:
                url = video_id_or_url
            
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
                
        except Exception as e:
            logger.error(f"Failed to extract video info for {video_id_or_url}: {e}")
            raise ServiceError(f"Failed to extract video information: {e}")
    
    def validate_video_url(self, url: str) -> bool:
        """Validate if URL is a valid YouTube video URL"""
        youtube_regex = re.compile(
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )
        return bool(youtube_regex.match(url))
    
    def get_video_id_from_url(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        youtube_regex = re.compile(
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )
        match = youtube_regex.match(url)
        return match.group(6) if match else None
    
    def download_and_process_async(
        self,
        video_id_or_url: str,
        artist: str = None,
        title: str = None,
        song_id: str = None
    ) -> str:
        """Download video and queue for audio processing, return job/song ID"""
        try:
            # Download video
            song_id, metadata = self.download_video(
                video_id_or_url, song_id, artist, title
            )
            
            # Create song in database using Song Service
            if self.song_service:
                self.song_service.create_song_from_metadata(song_id, metadata)
            
            # Queue for audio processing
            from ..tasks.tasks import process_audio_task, job_store
            from ..db.models import Job, JobStatus
            
            original_file = self.file_service.get_original_path(song_id, ".mp3")
            
            if original_file.exists():
                logger.info(f"Submitting audio processing task for song {song_id}")
                
                job = Job(
                    id=song_id,
                    filename=original_file.name,
                    status=JobStatus.PENDING,
                    created_at=datetime.now(timezone.utc),
                )
                job_store.save_job(job)
                
                task = process_audio_task.delay(song_id)
                
                job.task_id = task.id
                job.status = JobStatus.PROCESSING
                job_store.save_job(job)
                
                logger.info(f"Audio processing task queued for song {song_id}")
            else:
                logger.error(f"Original audio file not found at {original_file}")
                raise ServiceError(f"Original audio file not found after download")
            
            return song_id
            
        except Exception as e:
            logger.error(f"Failed to download and process video {video_id_or_url}: {e}")
            raise ServiceError(f"Failed to download and process video: {e}")
    
    def _extract_metadata_from_youtube_info(self, video_info: Dict[str, Any]) -> SongMetadata:
        """Extract metadata from YouTube video info"""
        return SongMetadata(
            title=video_info.get("title", "Unknown Title"),
            artist=video_info.get("uploader", "Unknown Artist"),
            duration=video_info.get("duration"),
            dateAdded=datetime.now(timezone.utc),
            source="youtube",
            sourceUrl=video_info.get("webpage_url"),
            videoId=video_info.get("id"),
            videoTitle=video_info.get("title"),
            uploader=video_info.get("uploader"),
            channel=video_info.get("channel"),
        )
    
    def _get_best_thumbnail_url(self, video_info: Dict[str, Any]) -> Optional[str]:
        """Get the best quality thumbnail URL from video info"""
        thumbnails = video_info.get("thumbnails", [])
        if thumbnails:
            # Get thumbnail with highest preference
            best_thumb = max(thumbnails, key=lambda t: t.get("preference", -9999))
            return best_thumb.get("url")
        elif video_info.get("thumbnail"):
            return video_info.get("thumbnail")
        return None
    
    def _download_thumbnail(self, song_id: str, thumbnail_url: str, metadata: SongMetadata) -> None:
        """Download thumbnail and update metadata"""
        try:
            song_dir = self.file_service.get_song_directory(song_id)
            thumbnail_path = song_dir / "thumbnail.jpg"
            
            # Use existing thumbnail download function
            from .file_management import download_image
            
            logger.info(f"Downloading thumbnail from {thumbnail_url}")
            if download_image(thumbnail_url, thumbnail_path):
                metadata.thumbnail = f"{song_id}/thumbnail.jpg"
                logger.info(f"Thumbnail downloaded for song {song_id}")
            else:
                logger.warning(f"Failed to download thumbnail for song {song_id}")
                
        except Exception as e:
            logger.warning(f"Error downloading thumbnail for song {song_id}: {e}")
            # Don't fail the whole operation for thumbnail issues
