# Service Layer Design

The Open Karaoke Studio backend implements a comprehensive service layer architecture that provides clean separation of concerns between API controllers, business logic, and data access. This design follows domain-driven principles with clear interfaces and dependency injection for maintainability and testability.

## Architecture Overview

The service layer sits between the API controllers and the data layer, encapsulating all business logic and providing a clean interface for complex operations. This architecture removes "fat controller" patterns and enables better testing, modularity, and code reuse.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Layer     │    │  Service Layer  │    │   Data Layer    │
│                 │    │                 │    │                 │
│ • Controllers   │───▶│ • Business Logic│───▶│ • Database      │
│ • HTTP Handling │    │ • Validation    │    │ • File System   │
│ • Response      │    │ • Coordination  │    │ • External APIs │
│   Formatting    │    │ • Error Handling│    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Service Directory Structure

```
backend/app/services/
├── __init__.py
├── interfaces/              # Service contracts (protocols)
│   ├── __init__.py
│   ├── song_service.py      # Song operations interface
│   ├── audio_service.py     # Audio processing interface
│   ├── file_service.py      # File management interface
│   ├── metadata_service.py  # Metadata operations interface
│   ├── lyrics_service.py    # Lyrics handling interface
│   ├── youtube_service.py   # YouTube integration interface
│   └── jobs_service.py      # Background job interface
├── song_service.py          # Song business logic
├── audio_service.py         # Audio processing coordination
├── file_service.py          # File system operations
├── metadata_service.py      # Metadata processing
├── lyrics_service.py        # Lyrics management
├── youtube_service.py       # YouTube integration
├── sync_service.py          # Database/filesystem sync
└── jobs_service.py          # Background job coordination
```

## Core Design Principles

### 1. Interface-Driven Design

All services implement well-defined interfaces using Python protocols:

```python
# Example: Song Service Interface
from typing import Protocol, List, Optional
from app..db.models import Song

class SongServiceInterface(Protocol):
    def get_songs(self) -> List[Song]:
        """Get all songs with automatic sync if needed"""

    def get_song_by_id(self, song_id: str) -> Optional[Song]:
        """Get song by ID"""

    def search_songs(self, query: str) -> List[Song]:
        """Search songs by title/artist"""

    def sync_with_filesystem(self) -> int:
        """Sync database with filesystem"""
```

### 2. Dependency Injection

Services use constructor injection for dependencies, enabling testing and modularity:

```python
class SongService(SongServiceInterface):
    def __init__(self,
                 file_service: FileServiceInterface = None,
                 metadata_service: MetadataServiceInterface = None):
        self.file_service = file_service or FileService()
        self.metadata_service = metadata_service or MetadataService()
```

### 3. Error Handling and Logging

Consistent error handling across all services with proper logging:

```python
def get_songs(self) -> List[Song]:
    try:
        # Business logic here
        return songs
    except Exception as e:
        logger.error(f"Error retrieving songs: {e}", exc_info=True)
        raise ServiceError("Failed to retrieve songs")
```

### 4. Single Responsibility

Each service has a focused responsibility:

- **Song Service**: Song CRUD operations, search, synchronization
- **File Service**: File system operations, directory management
- **Metadata Service**: Metadata processing, external API integration
- **Audio Service**: Audio processing coordination, Demucs integration
- **YouTube Service**: YouTube API integration, video processing
- **Lyrics Service**: Lyrics retrieval, processing, and synchronization

## Service Implementations

### Song Service

**Location**: `backend/app/services/song_service.py`
**Purpose**: Core song operations, search, and automatic synchronization
**Key Features**:

- Smart filesystem synchronization
- Comprehensive search functionality
- Metadata transformation and validation
- Integration with other services for complex operations

### File Service

**Location**: `backend/app/services/file_service.py`
**Purpose**: File system operations and directory management
**Key Features**:

- Song directory creation and management
- File path resolution and validation
- Safe file operations with error handling
- Integration with library structure

### Metadata Service

**Location**: `backend/app/services/metadata_service.py`
**Purpose**: Metadata processing and external API coordination
**Key Features**:

- iTunes API integration for rich metadata
- Metadata validation and normalization
- Cover art and thumbnail handling
- Multi-source metadata aggregation

### Audio Service

**Location**: `backend/app/services/audio_service.py`
**Purpose**: Audio processing workflow coordination
**Key Features**:

- Demucs audio separation orchestration
- Progress tracking and status updates
- Quality validation and error recovery
- Background job integration

### YouTube Service

**Location**: `backend/app/services/youtube_service.py`
**Purpose**: YouTube integration and video processing
**Key Features**:

- Video search and metadata extraction
- Download coordination with quality selection
- Thumbnail processing and storage
- Integration with audio processing pipeline

### Sync Service

**Location**: `backend/app/services/sync_service.py`
**Purpose**: Database and filesystem synchronization
**Key Features**:

- Bi-directional sync between database and filesystem
- Conflict resolution and error handling
- Batch processing for large libraries
- Integration with all other services

## API Integration Pattern

Controllers use services through a thin controller pattern:

```python
# Example: Thin controller using service layer
@song_bp.route('', methods=['GET'])
def get_songs():
    """Get all songs - thin controller"""
    try:
        song_service = SongService()
        songs = song_service.get_songs()

        response_data = [song.model_dump(mode='json') for song in songs]
        return jsonify(response_data)

    except ServiceError as e:
        logger.error(f"Service error: {e}")
        return jsonify({"error": "Failed to fetch songs"}), 500
```

## Testing Strategy

### Unit Testing

- **Service isolation**: Each service can be tested independently
- **Mock dependencies**: Interfaces enable easy mocking
- **Business logic focus**: Tests focus on business rules, not infrastructure

### Integration Testing

- **Service composition**: Test how services work together
- **Real dependencies**: Test with actual database and file system
- **End-to-end workflows**: Test complete user scenarios

### API Testing

- **Controller testing**: Test thin controllers with mocked services
- **Error handling**: Verify proper error response formatting
- **Response validation**: Ensure API contracts are maintained

## Performance Considerations

### Caching Strategy

- **Service-level caching**: Intelligent caching within services
- **Cross-service coordination**: Shared cache invalidation strategies
- **Memory management**: Efficient resource usage patterns

### Async Operations

- **Background processing**: Long operations delegated to Celery
- **Progress tracking**: Real-time status updates via WebSockets
- **Error recovery**: Robust failure handling and retry logic

## Current Implementation Status

### ✅ Implemented Services

- **Song Service**: Full implementation with filesystem sync
- **File Service**: Complete file system operations
- **Metadata Service**: iTunes integration and processing
- **Audio Service**: Demucs integration and workflow
- **YouTube Service**: Complete YouTube integration
- **Lyrics Service**: Lyrics retrieval and processing
- **Sync Service**: Database/filesystem synchronization

### 🔄 Ongoing Improvements

- **Repository Pattern**: Migrating to repository interfaces for data access
- **Enhanced Error Handling**: Standardizing error responses across services
- **Performance Optimization**: Caching and batch operation improvements
- **Testing Coverage**: Expanding unit and integration test coverage

## Benefits Achieved

### Code Organization

- **Clear separation**: Business logic separated from HTTP concerns
- **Modular design**: Services can be developed and maintained independently
- **Reusability**: Services can be used across different API endpoints

### Testability

- **Isolated testing**: Each service can be tested without external dependencies
- **Mock-friendly**: Interfaces enable comprehensive mocking strategies
- **Business logic focus**: Tests validate business rules, not infrastructure

### Maintainability

- **Single responsibility**: Each service has a focused purpose
- **Dependency injection**: Easy to modify and extend functionality
- **Error handling**: Consistent error patterns across the application

## Related Documentation

- **[Song Service](./services/song-service.md)** - Core song operations
- **[File Service](./services/file-service.md)** - File system management
- **[Metadata Service](./services/metadata-service.md)** - Metadata processing
- **[Audio Service](./services/audio-service.md)** - Audio processing coordination
- **[YouTube Service](./services/youtube-service.md)** - YouTube integration
- **[Background Jobs](./background-jobs.md)** - Async processing architecture

---

**Implementation Status**: ✅ Mostly Complete
**Remaining Work**: Repository pattern migration, enhanced error handling
**Location**: `backend/app/services/`
