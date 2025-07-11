# YouTube Service Architecture

The YouTube Service handles all YouTube integration functionality in Open Karaoke Studio, including video search, download, metadata extraction, and thumbnail processing. It provides a clean interface for YouTube operations while coordinating with other services for complete song processing workflows.

## Overview

The YouTube Service is one of the most complex services in the application, integrating with the YouTube API via yt-dlp for video operations. It coordinates with multiple other services to provide end-to-end YouTube-to-karaoke processing, including download management, metadata extraction, and background processing integration.

## Architecture

### Service Interface

The YouTube Service implements the `YouTubeServiceInterface` protocol:

```python
# backend/app/services/interfaces/youtube_service.py
from typing import Protocol, List, Dict, Any, Optional, Tuple

class YouTubeServiceInterface(Protocol):
    def search_videos(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search YouTube for videos matching the query"""

    def download_video(
        self,
        video_id_or_url: str,
        song_id: str = None,
        artist: str = None,
        title: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Download video and extract metadata as dictionary"""

    def extract_video_info(self, video_id_or_url: str) -> Dict[str, Any]:
        """Extract video information without downloading"""

    def validate_video_url(self, url: str) -> bool:
        """Validate if URL is a valid YouTube video URL"""

    def download_and_process_async(
        self,
        video_id_or_url: str,
        artist: str = None,
        title: str = None
    ) -> str:
        """Download video and queue for audio processing"""
```

### Service Dependencies

The YouTube Service coordinates with multiple other services:

```python
class YouTubeService(YouTubeServiceInterface):
    def __init__(
        self,
        file_service: FileServiceInterface = None,
        metadata_service: MetadataServiceInterface = None,
        jobs_service: JobsServiceInterface = None
    ):
        self.file_service = file_service or FileService()
        self.metadata_service = metadata_service or MetadataService()
        self.jobs_service = jobs_service or JobsService()
```

## Core Functionality

### 1. Video Search

Provides comprehensive YouTube search with rich metadata:

```python
def search_videos(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search YouTube with comprehensive metadata extraction"""
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "extract_flat": True,
        "default_search": "ytsearch",
        "noplaylist": True,
    }

    # Returns structured results with:
    # - Video ID, title, URL
    # - Channel information
    # - Thumbnail URLs
    # - Duration and metadata
```

**Search Results Structure**:

- **Video Information**: ID, title, URL, duration
- **Channel Data**: Channel name, channel ID, uploader info
- **Visual Assets**: Thumbnail URLs in multiple resolutions
- **Metadata**: Upload date, view count, description (when available)

### 2. Video Download

Sophisticated download management with quality optimization:

```python
def download_video(
    self,
    video_id_or_url: str,
    song_id: str = None,
    artist: str = None,
    title: str = None
) -> Tuple[str, Dict[str, Any]]:
    """Download with quality optimization and metadata extraction"""

    ydl_opts = {
        "format": "bestaudio/best",           # Best audio quality
        "outtmpl": outtmpl,                   # Organized file structure
        "postprocessors": [{                  # Audio conversion
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",        # High quality MP3
        }],
        "writeinfojson": True,                # Metadata preservation
        "noplaylist": True,                   # Single video only
    }
```

**Download Features**:

- **Quality Selection**: Automatically selects best available audio quality
- **Format Conversion**: Converts to high-quality MP3 (320kbps)
- **Metadata Preservation**: Saves complete video information as JSON
- **File Organization**: Places files in structured song directories
- **Error Recovery**: Robust error handling and retry logic

### 3. Metadata Extraction

Comprehensive metadata extraction from YouTube videos:

```python
def extract_metadata_from_youtube_info(self, info: Dict[str, Any]) -> Dict[str, Any]:
    """Extract rich metadata from YouTube video information"""
    metadata = {
        # Basic video information
        "title": info.get("title"),
        "artist": info.get("uploader"),
        "duration": info.get("duration"),

        # YouTube-specific metadata
        "source": "youtube",
        "source_url": info.get("webpage_url"),
        "video_id": info.get("id"),
        "video_title": info.get("title"),
        "uploader": info.get("uploader"),
        "uploader_id": info.get("uploader_id"),
        "channel": info.get("channel"),
        "channel_id": info.get("channel_id"),
        "description": info.get("description"),
        "upload_date": parse_upload_date(info.get("upload_date")),

        # Visual assets
        "thumbnail": best_thumbnail_url,
        "youtube_thumbnail_urls": thumbnail_urls,

        # Technical information
        "youtube_duration": info.get("duration"),
    }
```

**Metadata Categories**:

- **Video Information**: Title, description, duration, upload date
- **Channel Data**: Uploader name, channel ID, channel information
- **Technical Data**: Video ID, format information, quality metrics
- **Visual Assets**: Thumbnail URLs, cover art extraction
- **Timestamps**: Upload date, processing date, last modified

### 4. Thumbnail Processing

Intelligent thumbnail download and processing:

```python
def _download_thumbnail(self, song_id: str, thumbnail_url: str, metadata: Dict[str, Any]):
    """Download and process thumbnail with multiple formats"""
    try:
        # Download original thumbnail
        thumbnail_path = self.file_service.get_thumbnail_path(song_id, "original")
        self.file_service.download_file(thumbnail_url, thumbnail_path)

        # Process for different sizes if needed
        self._process_thumbnail_sizes(song_id, thumbnail_path)

        # Update metadata with local paths
        metadata.thumbnail = str(thumbnail_path.relative_to(self.file_service.base_library_dir))

    except Exception as e:
        logger.warning(f"Failed to download thumbnail for {song_id}: {e}")
        # Continue without thumbnail - not critical for functionality
```

**Thumbnail Features**:

- **Multiple Resolutions**: Downloads best available resolution
- **Local Storage**: Stores thumbnails in song directories
- **Fallback Handling**: Gracefully handles thumbnail failures
- **Format Optimization**: Converts to optimal formats when needed

### 5. Async Processing Integration

Coordinates with background processing for complete workflows:

```python
def download_and_process_async(
    self,
    video_id_or_url: str,
    artist: str = None,
    title: str = None
) -> str:
    """Download video and queue for complete processing"""

    # Download video and extract metadata
    song_id, metadata = self.download_video(video_id_or_url, artist=artist, title=title)

    # Create background job for audio processing
    job_id = self.jobs_service.create_audio_processing_job(
        song_id=song_id,
        operation="youtube_to_karaoke",
        metadata=metadata
    )

    # Return job ID for progress tracking
    return job_id
```

## Error Handling and Resilience

### Comprehensive Error Management

```python
def download_video(self, video_id_or_url: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
    try:
        # Download and processing logic
        return song_id, metadata

    except yt_dlp.DownloadError as e:
        logger.error(f"YouTube download failed: {e}")
        raise ServiceError(f"Failed to download video: {e}")

    except ValidationError as e:
        logger.error(f"Invalid video URL: {e}")
        raise ValidationError(f"Invalid YouTube URL: {e}")

    except Exception as e:
        logger.error(f"Unexpected error in YouTube download: {e}", exc_info=True)
        raise ServiceError("YouTube service temporarily unavailable")
```

### Error Categories

1. **Network Errors**: Connectivity issues, API rate limits
2. **Validation Errors**: Invalid URLs, unsupported content
3. **Download Errors**: Video unavailable, region restrictions
4. **Processing Errors**: File system issues, conversion failures
5. **Integration Errors**: Service coordination failures

### Recovery Strategies

- **Retry Logic**: Automatic retry with exponential backoff
- **Graceful Degradation**: Continue with partial functionality when possible
- **User Feedback**: Clear error messages and suggested actions
- **Monitoring Integration**: Error tracking and alerting

## Performance Optimization

### Download Efficiency

- **Quality Selection**: Optimizes for audio quality while minimizing download time
- **Parallel Processing**: Concurrent downloads when processing multiple videos
- **Caching Strategy**: Avoids re-downloading recently processed videos
- **Bandwidth Management**: Respectful of system resources

### Memory Management

- **Streaming Downloads**: Processes large files without loading entirely into memory
- **Cleanup Routines**: Automatically removes temporary files
- **Resource Monitoring**: Tracks and manages system resource usage

## Integration Patterns

### Service Coordination

The YouTube Service coordinates with multiple other services:

```python
# File Service Integration
song_dir = self.file_service.get_song_directory(song_id)
original_file = self.file_service.get_original_path(song_id, ".mp3")

# Metadata Service Integration
metadata = self.metadata_service.extract_metadata_from_youtube_info(info)
self.metadata_service.write_song_metadata(song_id, metadata)

# Jobs Service Integration
job_id = self.jobs_service.create_audio_processing_job(song_id, metadata)
```

### API Integration

```python
# Thin controller pattern
@youtube_bp.route('/download', methods=['POST'])
def download_youtube_video():
    try:
        youtube_service = YouTubeService()
        job_id = youtube_service.download_and_process_async(
            video_id_or_url=data["url"],
            artist=data.get("artist"),
            title=data.get("title")
        )

        return jsonify({"jobId": job_id, "status": "processing"})

    except ServiceError as e:
        return jsonify({"error": str(e)}), 400
```

## Testing Strategy

### Unit Testing

- **Mock yt-dlp**: Test business logic without actual downloads
- **Service isolation**: Test YouTube service independently
- **Error simulation**: Test all error scenarios and recovery paths

### Integration Testing

- **Live API testing**: Test with real YouTube videos (test-specific)
- **File system testing**: Verify proper file creation and organization
- **Service coordination**: Test integration with other services

### Performance Testing

- **Download benchmarks**: Measure download performance and optimization
- **Memory usage**: Monitor resource consumption during processing
- **Concurrent processing**: Test multiple simultaneous downloads

## Security Considerations

### Content Validation

- **URL validation**: Ensures only valid YouTube URLs are processed
- **Content filtering**: Respects age restrictions and availability
- **Rate limiting**: Prevents abuse of YouTube API

### File Security

- **Path validation**: Prevents directory traversal attacks
- **File type validation**: Ensures only expected file types are created
- **Size limits**: Prevents excessive disk usage

## Related Services

- **[File Service](./file-service.md)** - File system operations and organization
- **[Metadata Service](./metadata-service.md)** - Metadata extraction and processing
- **[Audio Service](./audio-service.md)** - Audio processing coordination
- **[Jobs Service](./jobs-service.md)** - Background processing integration

---

**Implementation Status**: ✅ Implemented
**Location**: `backend/app/services/youtube_service.py`
**Interface**: `backend/app/services/interfaces/youtube_service.py`
**API Integration**: `backend/app/api/youtube.py`
