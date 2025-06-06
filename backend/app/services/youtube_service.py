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
            # Check for the actual file path created by yt-dlp first
            expected_file_path = song_dir / "original.mp3"
            if expected_file_path.exists():
                original_file = expected_file_path
            else:
                # Try the configured path as fallback
                original_file = self.file_service.get_original_path(song_id, ".mp3")
                if not original_file.exists():
                    raise ServiceError(f"Download completed but file not found: {original_file}")

            # Extract and create metadata
            metadata = self._extract_metadata_from_youtube_info(info)
            
            # Ensure sourceUrl is set correctly
            if not metadata.sourceUrl:
                metadata.sourceUrl = url
            
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
        if not url or not isinstance(url, str):
            return False
            
        youtube_regex = re.compile(
            r'(https?://)?(www\.|m\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )
        return bool(youtube_regex.match(url))
    
    def get_video_id_from_url(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        if not url or not isinstance(url, str):
            return None
            
        youtube_regex = re.compile(
            r'(https?://)?(www\.|m\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
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
        """Download video and queue for unified YouTube processing, return job ID"""
        try:
            # Extract video ID using same logic as download_video
            if not self.validate_video_url(video_id_or_url):
                # Assume it's already a video ID
                video_id = video_id_or_url
            else:
                video_id = self.get_video_id_from_url(video_id_or_url)
                if not video_id:
                    raise ValidationError(f"Could not extract video ID from URL: {video_id_or_url}")
            
            # Validate song_id is provided
            if not song_id:
                raise ValidationError("song_id is required for YouTube processing")
                
            # Ensure song exists in database before creating job
            from ..db import database
            existing_song = database.get_song(song_id)
            if not existing_song:
                # Create song record with basic metadata
                metadata = SongMetadata(
                    title=title or "Unknown Title",
                    artist=artist or "Unknown Artist",
                    dateAdded=datetime.now(timezone.utc),
                    source="youtube",
                    videoId=video_id,
                )
                created_song = database.create_or_update_song(song_id, metadata)
                if created_song:
                    logger.info(f"Created song record {song_id} in database")
                else:
                    raise ServiceError(f"Failed to create song record {song_id}")
            
            # Generate unique job ID
            job_id = str(uuid.uuid4())
            
            # Create and save job to database FIRST, before queuing Celery task
            from ..jobs.jobs import job_store, process_youtube_job
            from ..db.models import Job, JobStatus
            import json
            
            # Store video_id in notes for reference
            job_notes = json.dumps({"video_id": video_id})
            
            job = Job(
                id=job_id,
                filename="original.mp3",
                status=JobStatus.PENDING,
                status_message="Queued for YouTube processing",
                progress=0,
                song_id=song_id,
                title=title or "Unknown Title",
                artist=artist or "Unknown Artist",
                notes=job_notes,
                created_at=datetime.now(timezone.utc),
            )
            
            # Save job to database and verify it was saved
            job_store.save_job(job)
            
            # Verify job was actually saved before proceeding
            saved_job = job_store.get_job(job_id)
            if not saved_job:
                raise ServiceError(f"Failed to save job {job_id} to database")
            
            logger.info(f"Job {job_id} successfully saved to database")
            
            # Now queue the Celery task
            metadata_dict = {
                "artist": artist or "Unknown Artist", 
                "title": title or "Unknown Title"
            }
            
            logger.info(f"Submitting unified YouTube processing job {job_id} for video {video_id}")
            
            task = process_youtube_job.delay(job_id, video_id, metadata_dict)
            
            # Update job with task ID
            job.task_id = task.id
            job_store.save_job(job)
            
            logger.info(f"Unified YouTube processing job {job_id} queued successfully with task {task.id}")
            
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to queue YouTube processing for {video_id_or_url}: {e}")
            raise ServiceError(f"Failed to queue YouTube processing: {e}")
    
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
        
        # Strategy 1: Look for a maxres or high-resolution thumbnail first
        if thumbnails:
            # First pass: Check for thumbnails with "maxres" or high resolution in the URL or ID
            for thumb in thumbnails:
                url = thumb.get("url", "")
                thumb_id = thumb.get("id", "")
                if ("maxres" in url.lower() or "maxres" in thumb_id.lower() or 
                    "hqdefault" in url.lower() or "hqdefault" in thumb_id.lower()):
                    logger.info(f"Selected high-res thumbnail: {url}")
                    return url
            
            # Strategy 2: Select by preference if available
            try:
                # Find thumbnail with highest preference value
                best_thumb = max(thumbnails, key=lambda t: t.get("preference", -9999))
                if best_thumb.get("url"):
                    logger.info(f"Selected thumbnail by preference: {best_thumb.get('url')}")
                    return best_thumb.get("url")
            except (ValueError, TypeError):
                logger.warning("Could not find thumbnail by preference")
            
            # Strategy 3: Select by resolution/width if available
            try:
                # Find thumbnail with highest width/resolution
                best_thumb = max(thumbnails, key=lambda t: int(t.get("width", 0)))
                if best_thumb.get("url"):
                    logger.info(f"Selected thumbnail by width: {best_thumb.get('url')}")
                    return best_thumb.get("url")
            except (ValueError, TypeError):
                logger.warning("Could not find thumbnail by width")
            
            # Strategy 4: Just use the first thumbnail as fallback
            if thumbnails and thumbnails[0].get("url"):
                logger.info(f"Selected first available thumbnail: {thumbnails[0].get('url')}")
                return thumbnails[0].get("url")
        
        # Strategy 5: Use the direct thumbnail property if available
        if video_info.get("thumbnail"):
            logger.info(f"Using direct thumbnail property: {video_info.get('thumbnail')}")
            return video_info.get("thumbnail")
        
        # Last resort: Construct a thumbnail URL based on video ID
        if video_info.get("id"):
            video_id = video_info.get("id")
            # YouTube standard thumbnail URL format
            constructed_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            logger.info(f"Constructed thumbnail URL from video ID: {constructed_url}")
            return constructed_url
            
        logger.warning("Could not find any thumbnail URL")
        return None
    
    def _download_thumbnail(self, song_id: str, thumbnail_url: str, metadata: SongMetadata) -> None:
        """Download thumbnail and update metadata"""
        try:
            song_dir = self.file_service.get_song_directory(song_id)
            thumbnail_path = song_dir / "thumbnail.jpg"
            
            # Use existing thumbnail download function
            from .file_management import download_image
            
            logger.info(f"Attempting to download thumbnail from {thumbnail_url}")
            if download_image(thumbnail_url, thumbnail_path):
                metadata.thumbnail = f"{song_id}/thumbnail.jpg"
                logger.info(f"Thumbnail successfully downloaded for song {song_id}")
                return
                
            # First fallback: Try alternative URL format if original failed
            video_id = metadata.videoId
            if video_id:
                # Try different YouTube thumbnail formats
                for format_name in ["maxresdefault", "hqdefault", "mqdefault", "sddefault", "default"]:
                    fallback_url = f"https://i.ytimg.com/vi/{video_id}/{format_name}.jpg"
                    if fallback_url != thumbnail_url:  # Avoid retrying the same URL
                        logger.info(f"Trying fallback thumbnail format {format_name}: {fallback_url}")
                        if download_image(fallback_url, thumbnail_path):
                            metadata.thumbnail = f"{song_id}/thumbnail.jpg"
                            logger.info(f"Fallback thumbnail {format_name} downloaded successfully for song {song_id}")
                            return
            
            logger.warning(f"All thumbnail download attempts failed for song {song_id}")
        except Exception as e:
            logger.warning(f"Error downloading thumbnail for song {song_id}: {e}")
            # Don't fail the whole operation for thumbnail issues
