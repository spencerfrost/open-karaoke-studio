# Service Interface Standardization

## Overview

Open Karaoke Studio implements standardized service interfaces using Python protocols to ensure consistent APIs, improve testability, and enable dependency injection throughout the service layer.

## Architecture

### Service Interface Structure

```
backend/app/services/
├── interfaces/                    # Protocol definitions
│   ├── __init__.py
│   ├── audio_service.py          # Audio processing interface
│   ├── file_service.py           # File management interface
│   ├── jobs_service.py           # Background job interface
│   ├── lyrics_service.py         # Lyrics service interface
│   ├── metadata_service.py       # Metadata processing interface
│   ├── song_service.py           # Song business logic interface
│   └── youtube_service.py        # YouTube integration interface
├── audio_service.py              # Audio processing implementation
├── file_service.py               # File management implementation
├── song_service.py               # Song business logic implementation
└── youtube_service.py            # YouTube integration implementation
```

## Protocol-Based Interfaces

### Base Service Interface Pattern

```python
from typing import Protocol, Dict, Any

class BaseServiceInterface(Protocol):
    """Base interface that all services should follow"""

    @property
    def service_name(self) -> str:
        """Return the name of this service for logging"""
        ...

    def health_check(self) -> Dict[str, Any]:
        """Check if the service is healthy and return status"""
        ...
```

### Service-Specific Interfaces

#### Song Service Interface

```python
from typing import Protocol, List, Optional, Dict, Any
from ...db.models import Song

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

    def create_song(
        self,
        song_id: str,
        title: str,
        artist: str,
        **kwargs
    ) -> Song:
        """Create song with direct parameters"""
        ...

    def update_song(
        self,
        song_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Song]:
        """Update song with field dictionary"""
        ...

    def delete_song(self, song_id: str) -> bool:
        """Delete song and associated files"""
        ...
```

#### File Service Interface

```python
from typing import Protocol
from pathlib import Path

class FileServiceInterface(Protocol):
    """Interface for File Service operations"""

    def get_song_directory(self, song_id: str) -> Path:
        """Get the directory path for a song"""
        ...

    def get_original_path(self, song_id: str) -> Path:
        """Get path to original audio file"""
        ...

    def get_vocals_path(self, song_id: str) -> Path:
        """Get path to vocals track"""
        ...

    def get_instrumental_path(self, song_id: str) -> Path:
        """Get path to instrumental track"""
        ...

    def delete_song_files(self, song_id: str) -> bool:
        """Delete all files associated with a song"""
        ...
```

#### YouTube Service Interface

```python
from typing import Protocol, Dict, Any, Optional

class YouTubeServiceInterface(Protocol):
    """Interface for YouTube Service operations"""

    def validate_video_url(self, url: str) -> bool:
        """Validate if URL is a valid YouTube video URL"""
        ...

    def extract_video_info(self, url: str) -> Dict[str, Any]:
        """Extract metadata from YouTube video"""
        ...

    def download_video(self, url: str) -> str:
        """Download YouTube video and return song_id"""
        ...

    def get_video_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """Get video metadata dictionary without downloading"""
        ...
```

## Implementation Benefits

### Consistent API Patterns

All services follow standardized patterns:

```python
# Consistent error handling
def get_song_by_id(self, song_id: str) -> Optional[Song]:
    """Standard return pattern: None for not found"""
    ...

# Consistent parameter naming
def search_songs(self, query: str, limit: Optional[int] = None) -> List[Song]:
    """Standard search pattern with optional limit"""
    ...

# Consistent boolean returns for operations
def delete_song(self, song_id: str) -> bool:
    """Standard success/failure boolean return"""
    ...
```

### Improved Testability

Interfaces enable easy mocking for unit tests:

```python
# Test with mock service
def test_song_controller_with_mock():
    mock_service = Mock(spec=SongServiceInterface)
    mock_service.get_all_songs.return_value = [test_song]

    controller = SongController(song_service=mock_service)
    result = controller.get_songs()

    assert result == expected_response
    mock_service.get_all_songs.assert_called_once()
```

### Dependency Injection Support

Services can be easily swapped:

```python
# Production service
production_service = SongService()

# Test service
test_service = MockSongService()

# Service container pattern
class ServiceContainer:
    def __init__(self, song_service: SongServiceInterface):
        self._song_service = song_service

    def get_song_service(self) -> SongServiceInterface:
        return self._song_service
```

## Service Implementation Patterns

### Standard Service Structure

```python
class SongService(SongServiceInterface):
    """Song service implementation following interface contract"""

    def __init__(self):
        self.config = get_config()
        self.logger = logging.getLogger(__name__)

    @property
    def service_name(self) -> str:
        return "SongService"

    def get_all_songs(self) -> List[Song]:
        """Implementation following interface contract"""
        try:
            db_songs = song_operations.get_all_songs()
            return [self._convert_to_api_response(song) for song in db_songs]
        except Exception as e:
            self.logger.error(f"Error getting all songs: {e}")
            raise ServiceError(f"Failed to retrieve songs: {e}")

    def _convert_to_api_response(self, db_song: DbSong) -> Song:
        """Internal helper method"""
        return Song.model_validate(db_song.to_dict())
        )
```

### Error Handling Standards

All services follow consistent error handling:

```python
from ..exceptions import ServiceError, NotFoundError, ValidationError

class StandardServiceErrorHandling:
    """Standard error handling patterns for all services"""

    def handle_not_found(self, resource_id: str, resource_type: str = "Resource"):
        """Standard not found handling"""
        raise NotFoundError(f"{resource_type} not found: {resource_id}")

    def handle_validation_error(self, message: str):
        """Standard validation error handling"""
        raise ValidationError(f"Validation failed: {message}")

    def handle_service_error(self, operation: str, error: Exception):
        """Standard service error handling"""
        self.logger.error(f"Service error in {operation}: {error}")
        raise ServiceError(f"Service operation failed: {operation}")
```

## Interface Documentation Standards

### Method Documentation

```python
def search_songs(
    self,
    query: str,
    limit: Optional[int] = None,
    filters: Optional[Dict[str, Any]] = None
) -> List[Song]:
    """
    Search songs with optional filters.

    Args:
        query: Search query string for title/artist matching
        limit: Maximum number of results to return (None = no limit)
        filters: Additional filters (e.g., {'artist': 'Queen'})

    Returns:
        List of Song objects matching the search criteria

    Raises:
        ValidationError: If query is invalid
        ServiceError: If search operation fails

    Example:
        songs = service.search_songs("Bohemian", limit=10)
        filtered = service.search_songs("rock", filters={'artist': 'Queen'})
    """
    ...
```

### Parameter Standards

```python
# Standard parameter patterns across all interfaces
song_id: str              # Always string UUID
query: str                # Search query string
limit: Optional[int]      # Optional result limiting
offset: int = 0          # Pagination offset
metadata: Dict[str, Any] # Dictionary for metadata
cleanup_files: bool      # Boolean flags for operations
```

## Testing with Interfaces

### Mock Service Creation

```python
class MockSongService:
    """Mock implementation for testing"""

    def __init__(self):
        self.songs = []

    def get_all_songs(self) -> List[Song]:
        return self.songs

    def get_song_by_id(self, song_id: str) -> Optional[Song]:
        return next((s for s in self.songs if s.id == song_id), None)

    def add_test_song(self, song: Song):
        """Test helper method"""
        self.songs.append(song)
```

### Interface Compliance Testing

```python
def test_service_implements_interface():
    """Test that service properly implements interface"""
    service = SongService()

    # Verify interface compliance
    assert isinstance(service, SongServiceInterface)

    # Test all interface methods exist
    assert hasattr(service, 'get_all_songs')
    assert hasattr(service, 'get_song_by_id')
    assert hasattr(service, 'search_songs')
```

## Service Container Pattern

### Container Implementation

```python
class ServiceContainer:
    """Dependency injection container for services"""

    def __init__(self):
        self._services = {}

    def register_song_service(self, service: SongServiceInterface):
        """Register song service implementation"""
        self._services['song'] = service

    def get_song_service(self) -> SongServiceInterface:
        """Get song service instance"""
        return self._services['song']
```

### Usage in Controllers

```python
class SongController:
    """API controller using dependency injection"""

    def __init__(self, container: ServiceContainer):
        self.song_service = container.get_song_service()

    def get_songs(self):
        """Controller method using injected service"""
        songs = self.song_service.get_all_songs()
        return [song.dict() for song in songs]
```

## Benefits Achieved

### Code Quality

- **Consistent APIs** across all services
- **Clear contracts** defined by interfaces
- **Type safety** with Protocol typing
- **Better IDE support** with interface definitions

### Testing

- **Easy mocking** with interface specifications
- **Test isolation** through dependency injection
- **Interface compliance** testing
- **Behavior verification** independent of implementation

### Maintainability

- **Swappable implementations** for different environments
- **Clear boundaries** between service contracts and implementations
- **Documentation enforcement** through interface definitions
- **Refactoring safety** with interface constraints

### Future Extensibility

- **Plugin architecture** support through interfaces
- **Service composition** through interface dependencies
- **Multi-implementation support** (e.g., different storage backends)
- **Clean service boundaries** for microservice evolution

## Best Practices

### Interface Design

1. **Keep interfaces focused** on single responsibilities
2. **Use clear, descriptive method names** following conventions
3. **Document all methods** with args, returns, and exceptions
4. **Follow consistent parameter patterns** across interfaces
5. **Use type hints** for all method signatures

### Implementation Guidelines

1. **Implement all interface methods** completely
2. **Follow interface contracts** exactly
3. **Use consistent error handling** patterns
4. **Log appropriately** for debugging and monitoring
5. **Test interface compliance** with unit tests

### Service Dependencies

1. **Inject dependencies** through constructors
2. **Use interfaces** for all service dependencies
3. **Avoid circular dependencies** between services
4. **Keep service boundaries** clear and minimal
5. **Test with mock dependencies** for isolation

## Related Documentation

- [Service Layer Design](../../architecture/backend/service-layer-design.md)
- [Testing Infrastructure](../guides/testing.md)
- [Dependency Injection](../reference/dependency-injection.md)
- [Error Handling](../reference/error-handling.md)
