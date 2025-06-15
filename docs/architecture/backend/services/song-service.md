# Song Service Architecture

The Song Service is the core business logic layer for all song-related operations in Open Karaoke Studio. It provides a clean interface between the API controllers and the data layer, handling song retrieval, search, synchronization, and basic CRUD operations.

## Overview

The Song Service implements a service layer pattern that removes business logic from API controllers and provides a testable, reusable interface for song operations. It handles automatic filesystem synchronization, search functionality, and ensures proper error handling and logging throughout song-related operations.

## Architecture

### Service Interface

The Song Service implements the `SongServiceInterface` protocol, providing a contract for all song-related operations:

```python
# backend/app/services/interfaces/song_service.py
from typing import Protocol, List, Optional
from ...db.models import Song, SongMetadata

class SongServiceInterface(Protocol):
    def get_all_songs(self) -> List[Song]:
        """Get all songs with automatic filesystem sync if needed"""
        
    def get_song_by_id(self, song_id: str) -> Optional[Song]:
        """Get song by ID"""
        
    def search_songs(self, query: str) -> List[Song]:
        """Search songs by title/artist"""
        
    def create_song_from_metadata(self, song_id: str, metadata: SongMetadata) -> Song:
        """Create song from metadata"""
        
    def update_song_metadata(self, song_id: str, metadata: SongMetadata) -> Optional[Song]:
        """Update song metadata"""
        
    def delete_song(self, song_id: str) -> bool:
        """Delete song and associated files"""
        
    def sync_with_filesystem(self) -> int:
        """Sync database with filesystem, return count of synced songs"""
```

### Service Implementation

The `SongService` class provides the concrete implementation with sophisticated business logic:

```python
# backend/app/services/song_service.py
class SongService(SongServiceInterface):
    def __init__(self):
        """Initialize the song service"""
        pass
    
    def get_all_songs(self) -> List[Song]:
        """
        Get all songs with automatic filesystem sync if needed.
        
        This method implements smart synchronization - if no songs are found
        in the database, it automatically triggers a filesystem sync to
        populate the database with any songs found in the file system.
        """
        try:
            db_songs = database.get_all_songs()
            
            # Smart sync: If no songs found, attempt filesystem sync
            if not db_songs:
                logger.info("No songs in database, attempting filesystem sync")
                sync_count = self.sync_with_filesystem()
                logger.info(f"Synced {sync_count} songs from filesystem")
                db_songs = database.get_all_songs()
            
            # Convert to Pydantic models for API response
            songs = [song.to_pydantic() for song in db_songs]
            return songs
            
        except Exception as e:
            logger.error(f"Error retrieving songs: {e}", exc_info=True)
            raise ServiceError("Failed to retrieve songs")
```

## Key Features

### 1. Automatic Filesystem Synchronization

The service automatically detects when the database is empty and triggers a filesystem sync, ensuring that songs in the file system are properly represented in the database.

### 2. Search Functionality

Provides robust search capabilities across song titles and artists:

```python
def search_songs(self, query: str) -> List[Song]:
    """Search songs by title or artist with proper error handling"""
    try:
        db_songs = database.search_songs(query)
        return [song.to_pydantic() for song in db_songs]
    except Exception as e:
        logger.error(f"Error searching songs with query '{query}': {e}")
        raise ServiceError("Failed to search songs")
```

### 3. Error Handling and Logging

All service methods implement comprehensive error handling with proper logging:

- **Service-level exceptions**: Uses `ServiceError` for business logic failures
- **Detailed logging**: Logs both info and error events with context
- **Exception propagation**: Converts low-level exceptions to service-level errors

### 4. Data Transformation

Handles conversion between database models and API response models:

- **Database to Pydantic**: Converts SQLAlchemy models to Pydantic for API responses
- **Metadata handling**: Processes song metadata for storage and retrieval
- **Response formatting**: Ensures consistent API response structure

## API Integration

The Song Service integrates with API controllers through a thin controller pattern:

```python
# backend/app/api/songs.py
@song_bp.route('', methods=['GET'])
def get_songs():
    """Get all songs - thin controller using service layer"""
    try:
        song_service = SongService()
        songs = song_service.get_all_songs()
        
        response_data = [
            song.model_dump(mode='json') if hasattr(song, 'model_dump') else song.dict() 
            for song in songs
        ]
        
        return jsonify(response_data)
        
    except ServiceError as e:
        current_app.logger.error(f"Service error in get_songs: {e}")
        return jsonify({"error": "Failed to fetch songs", "details": str(e)}), 500
```

## Dependencies

### Current Dependencies
- **Database Layer**: Direct integration with `backend/app/db/database.py`
- **Models**: Uses `Song`, `SongMetadata`, and `DbSong` models
- **Exceptions**: Relies on `ServiceError` and `NotFoundError` custom exceptions
- **Logging**: Standard Python logging for operation tracking

### Future Dependencies
- **Repository Layer**: Will migrate to repository pattern for better testing
- **Sync Service**: Filesystem sync will be extracted to dedicated service
- **File Service**: File operations will be delegated to file service

## Testing Approach

The service layer is designed for comprehensive testing:

### Unit Testing
- **Service methods**: Each method can be tested independently
- **Mock dependencies**: Database layer can be mocked for isolated testing
- **Error scenarios**: Exception handling can be thoroughly tested

### Integration Testing
- **API integration**: Controllers can be tested with real service instances
- **Database integration**: Service can be tested with test database
- **Filesystem integration**: Sync functionality can be tested with test directories

## Performance Considerations

### Smart Caching
- **Automatic sync**: Only triggers when necessary (empty database)
- **Minimal database calls**: Efficient query patterns
- **Pydantic conversion**: Performed only when needed for API responses

### Error Recovery
- **Graceful degradation**: Continues operation even with partial failures
- **Detailed logging**: Provides information for troubleshooting
- **Exception isolation**: Individual song failures don't break entire operations

## Future Enhancements

### Repository Pattern
The service will migrate to use repository interfaces for better testability and separation of concerns.

### Enhanced Search
- **Full-text search**: More sophisticated search capabilities
- **Metadata search**: Search across extended metadata fields
- **Performance optimization**: Caching and indexing for large libraries

### Async Operations
- **Background processing**: Long-running operations moved to background tasks
- **Real-time updates**: WebSocket integration for live updates
- **Batch operations**: Efficient handling of multiple song operations

## Related Services

- **[File Service](./file-service.md)** - Handles file system operations
- **[Metadata Service](./metadata-service.md)** - Manages song metadata
- **[Sync Service](./sync-service.md)** - Coordinates database/filesystem synchronization
- **[YouTube Service](./youtube-service.md)** - Handles YouTube integration

---

**Implementation Status**: ✅ Implemented  
**Location**: `backend/app/services/song_service.py`  
**Interface**: `backend/app/services/interfaces/song_service.py`  
**API Integration**: `backend/app/api/songs.py`
