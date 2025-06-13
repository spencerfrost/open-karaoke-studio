# backend/app/services/youtube_service.py
import uuid
import os
import yt_dlp
import re
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timezone

from flask import current_app
from .file_management import (
    get_song_dir,
    get_thumbnail_path,
    download_image,
)
from ..db.database import create_or_update_song
from ..db.models import SongMetadata


def search_youtube(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search YouTube for videos matching the query.

<<<<<<< Updated upstream
    Args:
        query (str): Search query
        max_results (int, optional): Maximum number of results to return. Defaults to 10.
=======
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
        title: str = None,
        search_thumbnail_url: str = None
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
>>>>>>> Stashed changes

    Returns:
        List[Dict[str, Any]]: List of video information objects
    """
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

    try:
        current_app.logger.info(f"Starting YouTube search with term: {search_term}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_term, download=False)
            current_app.logger.info(
                f"Search returned info: {bool(info)}, has entries: {'entries' in info}"
            )
            if "entries" in info:
                for entry in info["entries"]:
                    results.append(
                        {
                            "id": entry.get("id"),
                            "title": entry.get("title"),
                            "url": f"https://www.youtube.com/watch?v={entry.get('id')}",
                            "channel": entry.get("channel") or entry.get("uploader"),
                            "channelId": entry.get("channel_id")
                            or entry.get("uploader_id"),
                            "thumbnail": (
                                entry.get("thumbnails")[0]["url"]
                                if entry.get("thumbnails")
                                else None
                            ),
                            "duration": entry.get("duration"),
<<<<<<< Updated upstream
                        }
                    )
                current_app.logger.info(f"Found {len(results)} search results")
            else:
                current_app.logger.warning(
                    f"YouTube search returned no entries. Info keys: {info.keys() if info else 'None'}"
=======
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
        title: str = None,
        search_thumbnail_url: str = None
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
            
            # Enhance metadata with iTunes data (Phase 1A Task 1)
            try:
                from .itunes_service import enhance_metadata_with_itunes
                
                # Convert metadata to dict for iTunes enhancement
                metadata_dict = {
                    'artist': metadata.artist,
                    'title': metadata.title,
                    'album': getattr(metadata, 'releaseTitle', None),
                    'genre': getattr(metadata, 'genre', None),
                    'duration': metadata.duration
                }
                
                # Call iTunes enhancement
                enhanced_dict = enhance_metadata_with_itunes(metadata_dict, song_dir)
                
                # Update metadata with enhanced fields
                if enhanced_dict != metadata_dict:  # Only update if enhancement returned new data
                    # Cover art and core metadata
                    metadata.coverArt = enhanced_dict.get('coverArt')
                    metadata.genre = enhanced_dict.get('genre') or metadata.genre
                    metadata.releaseDate = enhanced_dict.get('releaseDate')
                    
                    # Additional metadata fields - use correct field names that exist in SongMetadata
                    if enhanced_dict.get('album'):
                        metadata.releaseTitle = enhanced_dict.get('album')  # Map album to releaseTitle
                    if enhanced_dict.get('itunesTrackId'):
                        metadata.mbid = str(enhanced_dict.get('itunesTrackId'))  # Map iTunes ID to mbid
                    
                    # iTunes enhancement fields
                    if enhanced_dict.get('itunesTrackId'):
                        metadata.itunesTrackId = enhanced_dict.get('itunesTrackId')
                    if enhanced_dict.get('itunesArtistId'):
                        metadata.itunesArtistId = enhanced_dict.get('itunesArtistId')
                    if enhanced_dict.get('itunesCollectionId'):
                        metadata.itunesCollectionId = enhanced_dict.get('itunesCollectionId')
                    if enhanced_dict.get('trackTimeMillis'):
                        metadata.trackTimeMillis = enhanced_dict.get('trackTimeMillis')
                    if enhanced_dict.get('itunesExplicit'):
                        metadata.itunesExplicit = enhanced_dict.get('itunesExplicit')
                    if enhanced_dict.get('itunesPreviewUrl'):
                        metadata.itunesPreviewUrl = enhanced_dict.get('itunesPreviewUrl')
                    if enhanced_dict.get('itunesArtworkUrls'):
                        metadata.itunesArtworkUrls = enhanced_dict.get('itunesArtworkUrls')
                    if enhanced_dict.get('itunesRawMetadata'):
                        metadata.itunesRawMetadata = enhanced_dict.get('itunesRawMetadata')
                    
                    # Keep original duration for now (YouTube video duration)
                    # iTunes track duration will be added in Phase 1B
                    
                    logger.info(f"Successfully enhanced metadata with iTunes for song {song_id}")
                else:
                    logger.info(f"No iTunes enhancement available for {metadata.artist} - {metadata.title}")
                    
            except Exception as e:
                # iTunes enhancement failure should not break YouTube download
                logger.warning(f"iTunes metadata enhancement failed for song {song_id}: {e}")
                # Continue with original metadata
            
            # Download thumbnail with priority for search thumbnail
            # Try search thumbnail first if provided
            if search_thumbnail_url:
                logger.info(f"[THUMBNAIL DEBUG] Prioritizing search thumbnail: {search_thumbnail_url}")
                self._download_thumbnail(song_id, search_thumbnail_url, metadata)
            
            # If search thumbnail failed or wasn't provided, use yt-dlp preference-based selection
            if not metadata.thumbnail:
                logger.info(f"[THUMBNAIL DEBUG] Search thumbnail failed/missing, using yt-dlp preference selection")
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
        song_id: str = None,
        search_thumbnail_url: str = None
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
>>>>>>> Stashed changes
                )
        return results
    except Exception as e:
        current_app.logger.error(f"YouTube search failed: {e}", exc_info=True)
        return []


def download_from_youtube(
    url: str, artist: str, song_title: str, song_id: str = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Download a song from YouTube, save it to the temporary directory,
    then move it to the song library and create metadata.

    Args:
        url (str): YouTube URL
        artist (str): Artist name
        song_title (str): Song title
        song_id (str, optional): Existing song ID to use. If not provided, generates a new one.

    Returns:
        Tuple[str, Dict[str, Any]]: (song_id, metadata)
    """
    current_app.logger.info(f"Downloading from YouTube: {url}")

    try:
        # Use provided song_id or generate a new one
        if not song_id:
            song_id = str(uuid.uuid4())
        song_dir = get_song_dir(song_id)
        outtmpl = os.path.join(song_dir, "original.%(ext)s")

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

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise ValueError(f"Could not download video info from {url}")

        if not os.path.exists(song_dir):
            raise FileNotFoundError(
                f"Download completed but file not found: {song_dir}"
            )
<<<<<<< Updated upstream

        thumbnails = info.get("thumbnails", [])
        thumbnail_url = thumbnails[0]["url"] if thumbnails else None
        if thumbnail_url:
            thumbnail_path = get_thumbnail_path(song_dir)
            current_app.logger.info(f"Downloading thumbnail from {thumbnail_url}")
            download_image(thumbnail_url, thumbnail_path)

        # Create SongMetadata object
        metadata = SongMetadata(
            title=song_title,
            artist=artist,
            duration=info.get("duration"),
=======
            
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
                "title": title or "Unknown Title",
                "searchThumbnailUrl": search_thumbnail_url  # Pass search thumbnail to worker
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
            duration=video_info.get("duration"),           # Keep as youtubeDuration 
            youtubeDuration=video_info.get("duration"),    # Explicit YouTube duration
            
>>>>>>> Stashed changes
            dateAdded=datetime.now(timezone.utc),
            source="youtube",
            sourceUrl=url,
            videoId=info.get("id"),
            videoTitle=info.get("title"),
            uploader=info.get("uploader"),
            channel=info.get("channel"),
        )

        # Process thumbnail
        thumbnails = info.get("thumbnails", [])
        thumbnail_url = None
        if thumbnails:
            best_thumb = max(thumbnails, key=lambda t: t.get("preference", -9999))
<<<<<<< Updated upstream
            thumbnail_url = best_thumb.get("url")
        elif info.get("thumbnail"):
            thumbnail_url = info.get("thumbnail")
            
        if thumbnail_url:
            thumbnail_path = get_thumbnail_path(song_dir)
            current_app.logger.info(f"Downloading thumbnail from {thumbnail_url}")
            if download_image(thumbnail_url, thumbnail_path):
                metadata.thumbnail = f"{song_id}/thumbnail.jpg"

        # Pass the SongMetadata object directly to create_or_update_song
        create_or_update_song(song_id, metadata)

        return song_id, metadata

    except Exception as e:
        current_app.logger.error(f"Failed to download from YouTube: {e}")
        raise
=======
            if best_thumb.get("url"):
                return best_thumb.get("url")
        
        # First fallback: Check for single thumbnail field  
        if video_info.get("thumbnail"):
            return video_info.get("thumbnail")
        
        # Final fallback: construct maxresdefault URL
        if video_info.get("id"):
            return f"https://i.ytimg.com/vi_webp/{video_info.get('id')}/maxresdefault.webp"
        
        return None
    
    def _download_thumbnail(self, song_id: str, thumbnail_url: str, metadata: SongMetadata) -> None:
        """Download thumbnail and update metadata"""
        try:
            song_dir = self.file_service.get_song_directory(song_id)
            logger.info(f"[THUMBNAIL DEBUG] Starting thumbnail download for song {song_id}")
            logger.info(f"[THUMBNAIL DEBUG] Song directory: {song_dir}")
            logger.info(f"[THUMBNAIL DEBUG] Thumbnail URL: {thumbnail_url}")
            
            # Determine file extension from URL or default to jpg
            import os
            from urllib.parse import urlparse
            parsed_url = urlparse(thumbnail_url)
            url_path = parsed_url.path.lower()
            
            if '.webp' in url_path:
                extension = 'webp'
            elif '.png' in url_path:
                extension = 'png'  
            else:
                extension = 'jpg'  # Default fallback
                
            thumbnail_filename = f"thumbnail.{extension}"
            thumbnail_path = song_dir / thumbnail_filename
            logger.info(f"[THUMBNAIL DEBUG] Determined extension: {extension}, filename: {thumbnail_filename}")
            logger.info(f"[THUMBNAIL DEBUG] Target path: {thumbnail_path}")
            
            # Use existing thumbnail download function
            from .file_management import download_image
            
            logger.info("[THUMBNAIL DEBUG] Calling download_image function...")
            download_result = download_image(thumbnail_url, thumbnail_path)
            logger.info(f"[THUMBNAIL DEBUG] download_image returned: {download_result}")
            
            if download_result:
                metadata.thumbnail = thumbnail_filename
                logger.info(f"[THUMBNAIL DEBUG] SUCCESS: Thumbnail downloaded and metadata.thumbnail set to: {metadata.thumbnail}")
                return
            else:
                logger.warning("[THUMBNAIL DEBUG] Primary download failed, trying fallbacks...")
                
            # First fallback: Try alternative URL formats if original failed
            video_id = metadata.videoId
            logger.info(f"[THUMBNAIL DEBUG] Attempting fallback downloads for video_id: {video_id}")
            if video_id:
                # Try different YouTube thumbnail formats, prioritizing WebP for quality
                formats_to_try = [
                    ("maxresdefault", "webp"),
                    ("maxresdefault", "jpg"), 
                    ("hqdefault", "webp"),
                    ("hqdefault", "jpg"),
                    ("mqdefault", "jpg"),
                    ("sddefault", "jpg"),
                    ("default", "jpg")
                ]
                
                for format_name, format_ext in formats_to_try:
                    if format_ext == "webp":
                        fallback_url = f"https://i.ytimg.com/vi_webp/{video_id}/{format_name}.{format_ext}"
                    else:
                        fallback_url = f"https://i.ytimg.com/vi/{video_id}/{format_name}.{format_ext}"
                        
                    if fallback_url != thumbnail_url:  # Avoid retrying the same URL
                        logger.info(f"[THUMBNAIL DEBUG] Trying fallback format {format_name}.{format_ext}: {fallback_url}")
                        fallback_filename = f"thumbnail.{format_ext}"
                        fallback_path = song_dir / fallback_filename
                        
                        fallback_result = download_image(fallback_url, fallback_path)
                        logger.info(f"[THUMBNAIL DEBUG] Fallback {format_name}.{format_ext} result: {fallback_result}")
                        
                        if fallback_result:
                            metadata.thumbnail = fallback_filename
                            logger.info(f"[THUMBNAIL DEBUG] SUCCESS: Fallback thumbnail {format_name}.{format_ext} downloaded, metadata.thumbnail set to: {metadata.thumbnail}")
                            return
            
            logger.warning(f"[THUMBNAIL DEBUG] FAILURE: All thumbnail download attempts failed for song {song_id}")
        except Exception as e:
            logger.error(f"[THUMBNAIL DEBUG] EXCEPTION: Error downloading thumbnail for song {song_id}: {e}")
            import traceback
            logger.error(f"[THUMBNAIL DEBUG] Stack trace: {traceback.format_exc()}")
            # Don't fail the whole operation for thumbnail issues
>>>>>>> Stashed changes
