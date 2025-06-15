# File Service Architecture

The File Service provides a centralized interface for all file system operations in Open Karaoke Studio. It manages the organized storage structure for songs, handles file path resolution, and provides safe file operations with comprehensive error handling.

## Overview

The File Service abstracts all file system interactions, providing a clean interface for song file management. It enforces the library's organizational structure, ensures directory consistency, and provides path resolution for different file types (original audio, separated vocals, instrumentals, metadata, thumbnails).

## Architecture

### Service Interface

The File Service implements the `FileServiceInterface` protocol:

```python
# backend/app/services/interfaces/file_service.py
from typing import Protocol, List, Optional
from pathlib import Path

class FileServiceInterface(Protocol):
    def ensure_library_exists(self) -> None:
        """Create base library directory if it doesn't exist"""
        
    def get_song_directory(self, song_id: str) -> Path:
        """Get or create song directory"""
        
    def get_vocals_path(self, song_id: str, extension: str = ".wav") -> Path:
        """Get vocals file path"""
        
    def get_instrumental_path(self, song_id: str, extension: str = ".wav") -> Path:
        """Get instrumental file path"""
        
    def get_original_path(self, song_id: str, extension: str = ".mp3") -> Path:
        """Get original file path"""
        
    def get_thumbnail_path(self, song_id: str, filename: str = "thumbnail.jpg") -> Path:
        """Get thumbnail file path"""
        
    def delete_song_files(self, song_id: str) -> bool:
        """Delete all files for a song"""
        
    def get_processed_song_ids(self) -> List[str]:
        """Get list of song IDs that have directories"""
        
    def song_directory_exists(self, song_id: str) -> bool:
        """Check if song directory exists"""
```

### Service Implementation

The `FileService` class provides robust file system operations:

```python
# backend/app/services/file_service.py
class FileService(FileServiceInterface):
    def __init__(self, base_library_dir: Path = None):
        config = get_config()
        self.base_library_dir = base_library_dir or config.LIBRARY_DIR
    
    def get_song_directory(self, song_id: str) -> Path:
        """Get or create song directory with automatic parent creation"""
        try:
            self.ensure_library_exists()
            song_dir = self.base_library_dir / song_id
            song_dir.mkdir(parents=True, exist_ok=True)
            return song_dir
        except Exception as e:
            logger.error(f"Failed to create song directory for {song_id}: {e}")
            raise ServiceError(f"Failed to create song directory: {e}")
```

## Library Organization Structure

The File Service enforces a consistent directory structure:

```
karaoke_library/
├── {song_id_1}/
│   ├── original.mp3          # Source audio file
│   ├── vocals.wav            # Separated vocals track
│   ├── instrumental.wav      # Separated instrumental track
│   ├── no_vocals.wav         # Alternative name for instrumental
│   ├── metadata.json         # Song metadata
│   ├── thumbnail.jpg         # Cover art/thumbnail
│   └── *.info.json          # YouTube download metadata (if applicable)
├── {song_id_2}/
│   └── ...
└── temp_downloads/           # Temporary processing files
```

## Core Functionality

### 1. Directory Management

**Automatic Directory Creation**:
```python
def get_song_directory(self, song_id: str) -> Path:
    """Creates directory structure automatically"""
    self.ensure_library_exists()  # Ensure base library exists
    song_dir = self.base_library_dir / song_id
    song_dir.mkdir(parents=True, exist_ok=True)  # Create with parents
    return song_dir
```

**Library Initialization**:
```python
def ensure_library_exists(self) -> None:
    """Ensures base library directory exists"""
    try:
        self.base_library_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Library directory ready: {self.base_library_dir}")
    except Exception as e:
        raise ServiceError(f"Failed to create library directory: {e}")
```

### 2. File Path Resolution

**Standardized Path Methods**:
```python
def get_vocals_path(self, song_id: str, extension: str = ".wav") -> Path:
    """Returns path for vocals track"""
    return self.get_song_directory(song_id) / f"vocals{extension}"

def get_instrumental_path(self, song_id: str, extension: str = ".wav") -> Path:
    """Returns path for instrumental track (supports aliases)"""
    # Primary path
    instrumental_path = self.get_song_directory(song_id) / f"instrumental{extension}"
    
    # Check for alternative naming
    no_vocals_path = self.get_song_directory(song_id) / f"no_vocals{extension}"
    
    return instrumental_path if instrumental_path.exists() else no_vocals_path

def get_original_path(self, song_id: str, extension: str = ".mp3") -> Path:
    """Returns path for original audio file"""
    return self.get_song_directory(song_id) / f"original{extension}"
```

**Flexible Extensions**:
- Supports multiple audio formats (.mp3, .wav, .m4a, .ogg)
- Handles format conversion naming conventions
- Provides fallback path resolution for alternative naming

### 3. File Discovery and Inventory

**Song Directory Discovery**:
```python
def get_processed_song_ids(self) -> List[str]:
    """Discovers all song directories in library"""
    try:
        if not self.base_library_dir.exists():
            return []
        
        song_ids = [
            d.name for d in self.base_library_dir.iterdir() 
            if d.is_dir() and not d.name.startswith('.')  # Exclude hidden dirs
        ]
        
        logger.debug(f"Found {len(song_ids)} song directories")
        return song_ids
        
    except Exception as e:
        logger.error(f"Error scanning library directory: {e}")
        raise ServiceError("Failed to scan library directory")
```

**Directory Validation**:
```python
def song_directory_exists(self, song_id: str) -> bool:
    """Check if song directory exists and is valid"""
    song_dir = self.base_library_dir / song_id
    return song_dir.exists() and song_dir.is_dir()
```

### 4. File Operations

**Safe File Deletion**:
```python
def delete_song_files(self, song_id: str) -> bool:
    """Safely delete all files for a song"""
    try:
        song_dir = self.base_library_dir / song_id
        if song_dir.exists() and song_dir.is_dir():
            shutil.rmtree(song_dir)
            logger.info(f"Deleted song directory: {song_dir}")
            return True
        else:
            logger.warning(f"Song directory does not exist: {song_dir}")
            return False
    except Exception as e:
        logger.error(f"Error deleting files for song {song_id}: {e}")
        raise ServiceError(f"Failed to delete files for song {song_id}: {e}")
```

**File Size and Metadata**:
```python
def get_file_size(self, file_path: Path) -> Optional[int]:
    """Get file size in bytes with error handling"""
    try:
        if file_path.exists() and file_path.is_file():
            return file_path.stat().st_size
        return None
    except Exception as e:
        logger.warning(f"Could not get size for {file_path}: {e}")
        return None
```

## Error Handling and Resilience

### Comprehensive Error Management

**File System Errors**:
```python
try:
    # File operation
    return result
except PermissionError as e:
    logger.error(f"Permission denied: {e}")
    raise ServiceError("Insufficient file system permissions")
except OSError as e:
    logger.error(f"File system error: {e}")
    raise ServiceError(f"File system operation failed: {e}")
except Exception as e:
    logger.error(f"Unexpected file error: {e}", exc_info=True)
    raise ServiceError("File operation failed")
```

### Error Categories

1. **Permission Errors**: Insufficient file system permissions
2. **Space Errors**: Disk space exhaustion
3. **Path Errors**: Invalid paths or characters
4. **Concurrency Errors**: Multiple processes accessing same files
5. **Network Errors**: Network-attached storage issues

### Recovery Strategies

- **Automatic Retry**: Temporary failures with exponential backoff
- **Path Validation**: Sanitize and validate all file paths
- **Graceful Degradation**: Continue operations when non-critical files missing
- **Cleanup Routines**: Automatic cleanup of incomplete operations

## Integration Patterns

### Service Coordination

The File Service integrates with multiple other services:

```python
# YouTube Service Integration
class YouTubeService:
    def download_video(self, video_id: str, song_id: str):
        # Get organized download location
        song_dir = self.file_service.get_song_directory(song_id)
        original_path = self.file_service.get_original_path(song_id, ".mp3")
        
        # Download with organized structure
        self._download_to_path(video_id, original_path)

# Audio Service Integration  
class AudioService:
    def separate_audio(self, song_id: str):
        # Get file paths for processing
        original_path = self.file_service.get_original_path(song_id)
        vocals_path = self.file_service.get_vocals_path(song_id)
        instrumental_path = self.file_service.get_instrumental_path(song_id)
        
        # Process with known paths
        self._run_demucs(original_path, vocals_path, instrumental_path)
```

### Configuration Integration

```python
# Configurable storage location
class FileService:
    def __init__(self, base_library_dir: Path = None):
        config = get_config()
        self.base_library_dir = base_library_dir or Path(config.LIBRARY_DIR)
        
        # Support for different storage backends
        if config.STORAGE_TYPE == "s3":
            self.storage_backend = S3StorageBackend()
        else:
            self.storage_backend = LocalStorageBackend()
```

## Testing Strategy

### Unit Testing

**Mock File System**:
```python
def test_file_service_with_mock_fs(tmp_path):
    file_service = FileService(base_library_dir=tmp_path)
    
    # Test directory creation
    song_dir = file_service.get_song_directory("test-song-id")
    assert song_dir.exists()
    
    # Test path resolution
    vocals_path = file_service.get_vocals_path("test-song-id")
    assert vocals_path.parent == song_dir
```

**Error Simulation**:
```python
def test_permission_error_handling(tmp_path):
    file_service = FileService(base_library_dir=tmp_path)
    
    # Create read-only directory
    song_dir = tmp_path / "read-only-song"
    song_dir.mkdir(mode=0o444)
    
    # Test error handling
    with pytest.raises(ServiceError):
        file_service.delete_song_files("read-only-song")
```

### Integration Testing

**Real File System**:
```python
def test_complete_file_workflow(tmp_path):
    file_service = FileService(base_library_dir=tmp_path)
    song_id = "integration-test-song"
    
    # Test complete workflow
    song_dir = file_service.get_song_directory(song_id)
    original_path = file_service.get_original_path(song_id)
    
    # Create test file
    original_path.write_text("test audio data")
    
    # Verify discovery
    assert song_id in file_service.get_processed_song_ids()
    
    # Test cleanup
    assert file_service.delete_song_files(song_id)
    assert not file_service.song_directory_exists(song_id)
```

## Performance Considerations

### File System Optimization

- **Batch Operations**: Group file operations when possible
- **Path Caching**: Cache frequently accessed path calculations
- **Directory Scanning**: Efficient directory traversal for large libraries
- **Concurrent Access**: Thread-safe operations for multi-process environments

### Storage Efficiency

- **Cleanup Routines**: Remove orphaned and temporary files
- **Compression**: Support for compressed audio formats
- **Deduplication**: Avoid storing duplicate files
- **Monitoring**: Track storage usage and growth

## Security Considerations

### Path Security

```python
def _validate_song_id(self, song_id: str) -> bool:
    """Validate song ID to prevent directory traversal"""
    # No path separators or special characters
    if any(char in song_id for char in ['/', '\\', '..', '~']):
        raise ValidationError("Invalid song ID: contains unsafe characters")
    
    # UUID format validation (recommended)
    try:
        uuid.UUID(song_id)
        return True
    except ValueError:
        raise ValidationError("Invalid song ID: must be valid UUID")
```

### Access Control

- **Path Validation**: Prevent directory traversal attacks
- **Permission Checks**: Validate file system permissions before operations
- **Sandboxing**: Restrict operations to library directory
- **Audit Logging**: Log all file operations for security monitoring

## Related Services

- **[Song Service](./song-service.md)** - Uses file service for song file operations
- **[YouTube Service](./youtube-service.md)** - Downloads files via file service
- **[Audio Service](./audio-service.md)** - Processes files using file service paths
- **[Metadata Service](./metadata-service.md)** - Stores metadata files via file service

---

**Implementation Status**: ✅ Implemented  
**Location**: `backend/app/services/file_service.py`  
**Interface**: `backend/app/services/interfaces/file_service.py`  
**Configuration**: Via `LIBRARY_DIR` environment variable
