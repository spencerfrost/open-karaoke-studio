# backend/app/services/youtube_service.py
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

import yt_dlp

from ..db.models import SongMetadata
from ..exceptions import ServiceError, ValidationError
from .file_service import FileService
from .interfaces.file_service import FileServiceInterface
from .interfaces.song_service import SongServiceInterface

logger = logging.getLogger(__name__)


class YouTubeServiceInterface(Protocol):
    """Interface for YouTube Service to enable dependency injection and testing"""

    def search_videos(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Search YouTube for videos matching the query"""
        ...

    def download_video(
        self, video_id_or_url: str, song_id: str = None, artist: str = None, title: str = None
    ) -> tuple[str, SongMetadata]:
        """Download video and extract metadata, return (song_id, metadata)"""
        ...

    def download_and_process_async(
        self, video_id_or_url: str, artist: str = None, title: str = None, song_id: str = None
    ) -> str:
        """Download video and queue for audio processing, return job/song ID"""
        ...


class YouTubeService(YouTubeServiceInterface):
    """Handle YouTube video operations"""

    def __init__(
        self, file_service: FileServiceInterface = None, song_service: SongServiceInterface = None
    ):
        self.file_service = file_service or FileService()
        self.song_service = song_service  # Injected to avoid circular dependency

    def search_videos(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
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

            logger.info("Starting YouTube search with term: %s", search_term)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_term, download=False)

                if "entries" in info:
                    for entry in info["entries"]:
                        results.append(
                            {
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
                            }
                        )
                    logger.info("Found %s search results", len(results))
                else:
                    logger.warning("YouTube search returned no entries")

            return results

        except Exception as e:
            logger.error("YouTube search failed: %s", e)
            raise ServiceError(f"Failed to search YouTube: {e}")

    def download_video(
        self, video_id_or_url: str, song_id: str = None, artist: str = None, title: str = None
    ) -> tuple[str, SongMetadata]:
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

            logger.info("Downloading YouTube video %s to song %s", video_id, song_id)

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

            # Extract duration from downloaded audio file if not available from YouTube
            if not metadata.duration:
                try:
                    duration = self._extract_audio_duration(original_file)
                    if duration:
                        metadata.duration = duration
                        logger.info(
                            "Extracted duration %ss from audio file for song %s", duration, song_id
                        )
                except Exception as e:
                    logger.warning(
                        "Failed to extract duration from audio file for song %s: %s", song_id, e
                    )

            # Ensure sourceUrl is set correctly
            if not metadata.sourceUrl:
                metadata.sourceUrl = url

            # Override with provided metadata if available
            if title:
                metadata.title = title
            if artist:
                metadata.artist = artist

            # Enhance metadata with iTunes data (Phase 1A Task 1)
            try:
                from .itunes_service import enhance_metadata_with_itunes

                # Convert metadata to dict for iTunes enhancement
                metadata_dict = {
                    "artist": metadata.artist,
                    "title": metadata.title,
                    "album": getattr(metadata, "releaseTitle", None),
                    "genre": getattr(metadata, "genre", None),
                    "duration": metadata.duration,
                }

                # Call iTunes enhancement
                enhanced_dict = enhance_metadata_with_itunes(metadata_dict, song_dir)

                # Update metadata with enhanced fields
                if enhanced_dict != metadata_dict:  # Only update if enhancement returned new data
                    # Cover art and core metadata
                    metadata.coverArt = enhanced_dict.get("coverArt")
                    metadata.genre = enhanced_dict.get("genre") or metadata.genre
                    metadata.releaseDate = enhanced_dict.get("releaseDate")

                    # Additional metadata fields - use correct field names that exist in
                    # SongMetadata
                    if enhanced_dict.get("album"):
                        metadata.releaseTitle = enhanced_dict.get(
                            "album"
                        )  # Map album to releaseTitle
                    if enhanced_dict.get("itunesTrackId"):
                        metadata.mbid = str(
                            enhanced_dict.get("itunesTrackId")
                        )  # Map iTunes ID to mbid

                    # iTunes enhancement fields
                    if enhanced_dict.get("itunesTrackId"):
                        metadata.itunesTrackId = enhanced_dict.get("itunesTrackId")
                    if enhanced_dict.get("itunesArtistId"):
                        metadata.itunesArtistId = enhanced_dict.get("itunesArtistId")
                    if enhanced_dict.get("itunesCollectionId"):
                        metadata.itunesCollectionId = enhanced_dict.get("itunesCollectionId")
                    if enhanced_dict.get("trackTimeMillis"):
                        metadata.trackTimeMillis = enhanced_dict.get("trackTimeMillis")
                    if enhanced_dict.get("itunesExplicit"):
                        metadata.itunesExplicit = enhanced_dict.get("itunesExplicit")
                    if enhanced_dict.get("itunesPreviewUrl"):
                        metadata.itunesPreviewUrl = enhanced_dict.get("itunesPreviewUrl")
                    if enhanced_dict.get("itunesArtworkUrls"):
                        metadata.itunesArtworkUrls = enhanced_dict.get("itunesArtworkUrls")
                    if enhanced_dict.get("itunesRawMetadata"):
                        metadata.itunesRawMetadata = enhanced_dict.get("itunesRawMetadata")

                    # Keep original duration for now (YouTube video duration)
                    # iTunes track duration will be added in Phase 1B

                    logger.info("Successfully enhanced metadata with iTunes for song %s", song_id)
                else:
                    logger.info(
                        "No iTunes enhancement available for %s - %s",
                        metadata.artist,
                        metadata.title,
                    )

            except Exception as e:
                # iTunes enhancement failure should not break YouTube download
                logger.warning("iTunes metadata enhancement failed for song %s: %s", song_id, e)
                # Continue with original metadata

            # NOTE: Thumbnail download removed from download_video() to prevent
            # stepper interference. Thumbnails are now handled separately in
            # the Celery job (process_youtube_job) after audio processing completes.

            logger.info("Successfully downloaded YouTube video %s as song %s", video_id, song_id)
            return song_id, metadata

        except Exception as e:
            logger.error("Failed to download YouTube video %s: %s", video_id_or_url, e)
            raise ServiceError(f"Failed to download YouTube video: {e}")

    def extract_video_info(self, video_id_or_url: str) -> dict[str, Any]:
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
            logger.error("Failed to extract video info for %s: %s", video_id_or_url, e)
            raise ServiceError(f"Failed to extract video information: {e}")

    def validate_video_url(self, url: str) -> bool:
        """Validate if URL is a valid YouTube video URL"""
        if not url or not isinstance(url, str):
            return False

        youtube_regex = re.compile(
            r"(https?://)?(www\.|m\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/"
            r"(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})"
        )
        return bool(youtube_regex.match(url))

    def get_video_id_from_url(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        if not url or not isinstance(url, str):
            return None

        youtube_regex = re.compile(
            r"(https?://)?(www\.|m\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/"
            r"(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})"
        )
        match = youtube_regex.match(url)
        return match.group(6) if match else None

    def download_and_process_async(
        self, video_id_or_url: str, artist: str = None, title: str = None, song_id: str = None
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
            from ..db.song_operations import create_or_update_song, get_song

            existing_song = get_song(song_id)
            if not existing_song:
                # Create song record with basic metadata
                metadata = SongMetadata(
                    title=title or "Unknown Title",
                    artist=artist or "Unknown Artist",
                    dateAdded=datetime.now(timezone.utc),
                    source="youtube",
                    videoId=video_id,
                )
                created_song = create_or_update_song(song_id, metadata)
                if created_song:
                    logger.info("Created song record %s in database", song_id)
                else:
                    raise ServiceError(f"Failed to create song record {song_id}")

            # Generate unique job ID
            job_id = str(uuid.uuid4())

            # Create and save job to database FIRST, before queuing Celery task
            import json

            from ..db.models import Job, JobStatus
            from ..jobs.jobs import job_store, process_youtube_job

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

            logger.info("Job %s successfully saved to database", job_id)

            # Note: Thumbnail download is now handled by the Celery job to avoid
            # interfering with frontend stepper state due to database updates

            # Queue the Celery task for both audio processing and thumbnail download
            metadata_dict = {
                "artist": artist or "Unknown Artist",
                "title": title or "Unknown Title",
            }

            logger.info(
                "Submitting unified YouTube processing job %s for video %s", job_id, video_id
            )

            task = process_youtube_job.delay(job_id, video_id, metadata_dict)

            # Update job with task ID
            job.task_id = task.id
            job_store.save_job(job)

            logger.info(
                "Unified YouTube processing job %s queued successfully with task %s",
                job_id,
                task.id,
            )

            return job_id

        except Exception as e:
            logger.error("Failed to queue YouTube processing for %s: %s", video_id_or_url, e)
            raise ServiceError(f"Failed to queue YouTube processing: {e}")

    def _extract_metadata_from_youtube_info(self, video_info: dict[str, Any]) -> SongMetadata:
        """Extract metadata from YouTube video info"""
        from .metadata_service import filter_youtube_metadata_for_storage

        # Extract channel ID with fallback to uploader_id
        channel_id = video_info.get("channel_id") or video_info.get("uploader_id")

        # Helper function to extract selected thumbnails
        def _extract_selected_thumbnails(video_info):
            thumbnails = video_info.get("thumbnails", [])
            if not thumbnails:
                return None

            # Select a few key thumbnail URLs
            selected = []
            for thumb in thumbnails:
                url = thumb.get("url")
                if url and any(res in str(thumb.get("height", 0)) for res in ["120", "320", "640"]):
                    selected.append(url)

            return selected[:3] if selected else None  # Limit to 3 thumbnails

        return SongMetadata(
            title=video_info.get("title", "Unknown Title"),
            artist=video_info.get("uploader", "Unknown Artist"),
            # Dual duration strategy
            duration=video_info.get("duration"),  # Keep as youtubeDuration
            youtubeDuration=video_info.get("duration"),  # Explicit YouTube duration
            dateAdded=datetime.now(timezone.utc),
            source="youtube",
            sourceUrl=video_info.get("webpage_url"),
            videoId=video_info.get("id"),
            videoTitle=video_info.get("title"),
            uploader=video_info.get("uploader"),
            uploaderId=video_info.get("uploader_id"),
            channel=video_info.get("channel"),
            description=video_info.get("description"),
            uploadDate=self._parse_upload_date(video_info.get("upload_date")),
            # Phase 1A Task 2: Focus on Channel ID as the key YouTube field
            channelId=channel_id,
            # Phase 1B: Enhanced YouTube fields
            youtubeThumbnailUrls=_extract_selected_thumbnails(video_info),
            youtubeTags=video_info.get("tags", []),
            youtubeCategories=video_info.get("categories", []),
            youtubeChannelId=channel_id,
            youtubeChannelName=video_info.get("channel") or video_info.get("uploader"),
            # Phase 1B: Store filtered raw YouTube metadata
            youtubeRawMetadata=filter_youtube_metadata_for_storage(video_info),
        )

    def _parse_upload_date(self, upload_date_str: str) -> Optional[datetime]:
        """Parse upload date string to datetime object"""
        if not upload_date_str:
            return None

        try:
            # yt-dlp typically provides dates in YYYYMMDD format
            if len(upload_date_str) == 8:
                return datetime.strptime(upload_date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass

        return None

    def _get_best_thumbnail_url(self, video_info: dict[str, Any]) -> Optional[str]:
        """Get the best quality thumbnail URL from video info"""
        thumbnails = video_info.get("thumbnails", [])

        if thumbnails:
            # Sort by preference (higher = better) and take the best
            best_thumb = max(thumbnails, key=lambda t: t.get("preference", -9999))
            if best_thumb.get("url"):
                return best_thumb.get("url")

        # First fallback: Check for single thumbnail field
        if video_info.get("thumbnail"):
            return video_info.get("thumbnail")

        # Final fallback: construct maxresdefault URL
        if video_info.get("id"):
            return f"https://i.ytimg.com/vi_webp/{video_info.get('id')}/maxresdefault.webp"

        return None

    def fetch_and_save_thumbnail(self, video_id: str, song_id: str) -> Optional[str]:
        """Fetch and save thumbnail for a video, returns best thumbnail URL on success"""
        try:
            # Extract video info without downloading
            video_info = self.extract_video_info(video_id)

            # Try multiple thumbnail sources with fallback
            successful_url = self._download_thumbnail_with_fallback(video_info, song_id)

            if not successful_url:
                logger.warning("All thumbnail sources failed for video %s", video_id)
                raise ServiceError("No valid thumbnail found")

            return successful_url

        except ServiceError:
            raise
        except Exception as e:
            logger.error("Failed to fetch and save thumbnail for video %s: %s", video_id, e)
            raise ServiceError(f"Failed to fetch thumbnail: {e}")

    def _download_thumbnail_with_fallback(
        self, video_info: dict[str, Any], song_id: str
    ) -> Optional[str]:
        """Try multiple thumbnail sources with fallback, returns successful URL or None"""
        video_id = video_info.get("id")
        if not video_id:
            return None

        # Strategy 1: Try yt-dlp thumbnail URLs first
        thumbnails = video_info.get("thumbnails", [])
        if thumbnails:
            logger.info("Trying yt-dlp provided thumbnails for video %s", video_id)
            # Sort by preference and resolution for best quality first
            sorted_thumbnails = sorted(
                thumbnails,
                key=lambda t: (t.get("preference", -9999), t.get("width", 0) * t.get("height", 0)),
                reverse=True,
            )

            for thumb in sorted_thumbnails[:3]:  # Try top 3 best thumbnails
                url = thumb.get("url")
                if url:
                    logger.info("Trying yt-dlp thumbnail: %s", url)
                    success, thumbnail_filename = self._download_and_save_thumbnail(song_id, url)
                    if success:
                        logger.info("✅ Successfully downloaded yt-dlp thumbnail: %s", url)
                        self._update_song_thumbnail_in_db(song_id, thumbnail_filename)
                        return url
                    else:
                        logger.warning("❌ Failed to download yt-dlp thumbnail: %s", url)

        # Strategy 2: Systematic URL construction fallback
        logger.info("Falling back to systematic URL construction for video %s", video_id)
        formats_to_try = [
            ("maxresdefault", "webp"),  # 1920x1080 WebP
            ("maxresdefault", "jpg"),  # 1920x1080 JPG
            ("hqdefault", "webp"),  # 480x360 WebP
            ("hqdefault", "jpg"),  # 480x360 JPG
            ("mqdefault", "webp"),  # 320x180 WebP
            ("mqdefault", "jpg"),  # 320x180 JPG
            ("sddefault", "jpg"),  # 640x480 JPG
            ("default", "jpg"),  # 120x90 JPG
        ]

        for format_name, format_ext in formats_to_try:
            if format_ext == "webp":
                url = f"https://i.ytimg.com/vi_webp/{video_id}/{format_name}.{format_ext}"
            else:
                url = f"https://i.ytimg.com/vi/{video_id}/{format_name}.{format_ext}"

            logger.info("Trying systematic URL: %s", url)
            success, thumbnail_filename = self._download_and_save_thumbnail(song_id, url)
            if success:
                logger.info("✅ Successfully downloaded systematic thumbnail: %s", url)
                self._update_song_thumbnail_in_db(song_id, thumbnail_filename)
                return url
            else:
                logger.warning("❌ Failed to download systematic thumbnail: %s", url)

        logger.error("All thumbnail download attempts failed for video %s", video_id)
        return None

    def _get_best_quality_thumbnail(self, video_info: dict[str, Any]) -> Optional[str]:
        """Get best quality thumbnail using systematic fallback chain"""
        video_id = video_info.get("id")
        if not video_id:
            return None

        # Fallback chain as described in architecture
        formats_to_try = [
            ("maxresdefault", "webp"),  # 1920x1080 WebP
            ("maxresdefault", "jpg"),  # 1920x1080 JPG
            ("hqdefault", "webp"),  # 480x360 WebP
            ("hqdefault", "jpg"),  # 480x360 JPG
            ("mqdefault", "webp"),  # 320x180 WebP
            ("mqdefault", "jpg"),  # 320x180 JPG
            ("sddefault", "jpg"),  # 640x480 JPG
            ("default", "jpg"),  # 120x90 JPG
        ]

        # First, try to use yt-dlp's preference system
        thumbnails = video_info.get("thumbnails", [])
        if thumbnails:
            # Sort by preference (higher = better) and resolution
            best_thumb = max(
                thumbnails,
                key=lambda t: (t.get("preference", -9999), t.get("width", 0) * t.get("height", 0)),
            )
            if best_thumb.get("url"):
                return best_thumb.get("url")

        # Fallback to systematic URL construction
        for format_name, format_ext in formats_to_try:
            if format_ext == "webp":
                url = f"https://i.ytimg.com/vi_webp/{video_id}/{format_name}.{format_ext}"
            else:
                url = f"https://i.ytimg.com/vi/{video_id}/{format_name}.{format_ext}"

            # Quick check if this format exists (optional, can be removed for performance)
            if self._check_thumbnail_exists(url):
                logger.info(
                    "Selected thumbnail format %s.%s for video %s",
                    format_name,
                    format_ext,
                    video_id,
                )
                return url

        logger.warning("No valid thumbnail found for video %s", video_id)
        return None

    def _check_thumbnail_exists(self, url: str) -> bool:
        """Quick HTTP HEAD request to check if thumbnail exists"""
        try:
            import requests

            response = requests.head(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False  # Return False if we can't check

    def _download_and_save_thumbnail(self, song_id: str, thumbnail_url: str) -> tuple[bool, str]:
        """Download and save thumbnail to file system, returns (success, filename)"""
        try:
            # Determine file extension from URL (prefer WebP, fallback to JPG)
            from urllib.parse import urlparse

            parsed_url = urlparse(thumbnail_url)
            url_path = parsed_url.path.lower()

            if ".webp" in url_path:
                extension = "webp"
            elif ".png" in url_path:
                extension = "png"
            else:
                extension = "jpg"  # Default fallback

            # Get song directory and create proper thumbnail path
            song_dir = self.file_service.get_song_directory(song_id)
            thumbnail_filename = f"thumbnail.{extension}"
            thumbnail_path = song_dir / thumbnail_filename

            # Use existing thumbnail download function
            from .file_management import download_image

            logger.info("Downloading thumbnail from %s to %s", thumbnail_url, thumbnail_path)
            success = download_image(thumbnail_url, thumbnail_path)

            if success:
                logger.info(
                    "Thumbnail successfully downloaded for song %s as %s",
                    song_id,
                    thumbnail_filename,
                )
                return True, thumbnail_filename
            else:
                logger.warning("Failed to download thumbnail for song %s", song_id)
                return False, ""

        except Exception as e:
            logger.error("Error downloading thumbnail for song %s: %s", song_id, e)
            return False, ""

    def _update_song_thumbnail_in_db(self, song_id: str, thumbnail_filename: str) -> None:
        """Update database with thumbnail information"""
        try:
            from ..db.song_operations import update_song_thumbnail

            # Update thumbnail path in database
            # Use the actual filename that was saved (includes correct extension)
            thumbnail_path = f"{song_id}/{thumbnail_filename}"

            # Call database update function
            success = update_song_thumbnail(song_id, thumbnail_path)

            if success:
                logger.info(
                    "Updated database thumbnail path for song %s: %s", song_id, thumbnail_path
                )
            else:
                logger.warning("Failed to update thumbnail in database for song %s", song_id)

        except Exception as e:
            logger.error("Failed to update database thumbnail for song %s: %s", song_id, e)

    def _extract_audio_duration(self, audio_path) -> Optional[float]:
        """Extract duration from audio file using librosa"""
        try:
            import librosa

            duration = librosa.get_duration(path=str(audio_path))
            return float(duration)
        except Exception as e:
            logger.warning("Failed to extract duration from audio file %s: %s", audio_path, e)
            return None
