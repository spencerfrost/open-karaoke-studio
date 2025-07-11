# API Layer Architecture

## Service Layer & Repository Overview

| Domain/Feature      | Service Layer Present? | Repository Present? | Current Usage Pattern                | Recommendation                                      |
|---------------------|------------------------|---------------------|--------------------------------------|-----------------------------------------------------|
| Songs               | Partial (legacy, not used) | Yes                | Controllers use `SongRepository` directly | **Use repository only.** No service layer needed for CRUD. |
| Jobs                | Yes (`JobsService`)    | Yes                | Controllers use `JobsService` (orchestrates jobs, uses repo) | **Keep service layer** for orchestration/business logic. |
| Karaoke Queue       | No                     | Yes                | Controllers use `KaraokeQueueItem`/repo directly | **Use repository only.** No service layer needed.         |
| Users               | No                     | Yes                | Controllers use `User` model/repo directly | **Use repository only.** No service layer needed.         |
| Lyrics              | Yes (`LyricsService`)  | No                 | Controllers use `LyricsService` (external API) | **Keep service layer** for API integration.               |
| Metadata            | Yes (`MetadataService`)| No                 | Controllers use `MetadataService` (external API) | **Keep service layer** for API integration.               |
| YouTube             | Yes (`YouTubeService`) | No                 | Controllers use `YouTubeService` (external API, jobs) | **Keep service layer** for orchestration/API.             |
| YouTube Music       | Yes (`YouTubeMusicService`)| No              | Controllers use `YouTubeMusicService` (external API) | **Keep service layer** for API integration.               |

**Legend:**
- "Service Layer Present?" = Is there a dedicated service class for this domain?
- "Repository Present?" = Is there a repository or model abstraction for CRUD?
- "Current Usage Pattern" = How do controllers interact with data/business logic?
- "Recommendation" = Should you use a service, a repository, or both?

> **Summary:** Use repositories for CRUD and simple logic. Use service layers only for orchestration, external APIs, or complex business rules.



## Overview

The API Layer provides a clean HTTP interface to the application's business logic through thin controllers that handle only HTTP concerns. It implements standardized response formats, request validation, error handling, and logging patterns across all endpoints while delegating all business logic to the service layer.

## Current Implementation Status

**Framework**: Flask with Blueprint architecture  
**Endpoints**: 35+ REST endpoints across 8 blueprints  
**Blueprints**: `songs`, `jobs`, `karaoke_queue`, `users`, `lyrics`, `metadata`, `youtube`, `youtube_music`  
**Status**: Partially refactored. Some endpoints use thin controller pattern and standardized responses, but others (notably users, queue, and some legacy endpoints) use direct model access and do not always use the `APIResponse` utility or validation decorators. Full standardization is in progress.

### Decorators and Response Utilities
- The `APIResponse` utility is defined in `backend/app/api/responses.py` but not all endpoints use it yet. Some use `success_response`/`error_response`, others return raw `jsonify`.
- Logging and error handling decorators exist (`log_api_call`, `handle_api_error`), but are inconsistently applied.
- Request validation is handled by custom decorators in some endpoints, but not all.

### Service Layer Usage
- Many endpoints delegate to service classes, but some (notably in `songs.py`, `users.py`, and `karaoke_queue.py`) access the database or models directly, bypassing the service layer.
- Migration to a fully interface-driven, thin-controller pattern is ongoing.

## Core Responsibilities

1. **HTTP Request/Response Handling**
    - Route requests to appropriate service methods (where implemented)
    - Validate incoming request data and parameters (in progress)
    - Transform service responses to standardized HTTP format (in progress)
    - Handle HTTP-specific concerns (headers, status codes, content types)

2. **Request Validation and Security**
    - Validate request payloads using schemas (in progress)
    - Sanitize input data before passing to services
    - Implement authentication and authorization checks (minimal, only for users)
    - Handle CORS and other security headers

3. **Standardized Response Formatting**
    - Consistent JSON response structure across all endpoints (in progress)
    - Standardized error response formats (in progress)
    - Pagination support for list endpoints (where implemented)
    - Meta information inclusion (timing, pagination, etc.)

4. **Error Handling and Logging**
    - Convert service exceptions to appropriate HTTP status codes (in progress)
    - Log all API requests and responses for debugging (in progress)
    - Provide detailed error information in development
    - Sanitize error messages for production

> **Note:** Not all endpoints currently meet these responsibilities. See migration plan for details.
## API Architecture Pattern

### Thin Controller Design

Controllers should be thin and focus only on HTTP concerns:

```python
@song_bp.route('', methods=['GET'])
@handle_api_errors
@log_api_call(logger)
@validate_query_params(SongListSchema())
def get_songs(query_params):
    """Thin controller that delegates to service layer"""
    song_service: SongServiceInterface = get_song_service()

    # Delegate business logic to service
    songs = song_service.get_songs(
        limit=query_params.get('limit'),
        offset=query_params.get('offset')
    )

    # Transform to HTTP response
    response_data = [song.dict() for song in songs]
    return APIResponse.success(
        data=response_data,
        message=f"Retrieved {len(response_data)} songs"
    )
```

### Standardized Response Format

All API responses follow a consistent structure:

```python
# Success Response
{
    "success": true,
    "message": "Operation completed successfully",
    "data": {...},
    "meta": {
        "pagination": {...},
        "timing": {...}
    }
}

# Error Response
{
    "success": false,
    "error": {
        "message": "Human-readable error message",
        "code": "MACHINE_READABLE_CODE",
        "details": {...}
    }
}
```

## Implementation Components

### Response Utilities
- `APIResponse` (as described) is not universally used. Many endpoints use `success_response`/`error_response` from `api/responses.py`, and some return raw `jsonify`.
- Standardized response structure is the goal, but not all endpoints are migrated yet.

### Request Validation
- Decorators for validation exist, but are inconsistently applied. Some endpoints validate manually or not at all.
- Marshmallow schemas are used for some request validation, but not all endpoints use them.

### Error Handling
- Centralized error handling is implemented via decorators (e.g., `handle_api_error`), but not all endpoints use them.
- Some endpoints return raw error JSON or HTTP status codes directly.

### Logging
- Logging decorators exist (`log_api_call`), but are not consistently applied across all endpoints.

> **Summary:**
> The API layer is in transition: some endpoints are fully standardized, while others use legacy patterns. Full migration to thin controllers, standardized responses, and validation is ongoing.
## Blueprint Organization

The following blueprints are currently registered in the application:

- **Songs API** (`/api/songs`): Song management, search, artist listing, file download, lyrics, cover art, etc.
- **Jobs API** (`/api/jobs`): Background job management, job status, job details, cancel/dismiss jobs.
- **Karaoke Queue API** (`/karaoke-queue`): Real-time queue management (add, remove, reorder, clear queue).
- **Users API** (`/users`): User registration, login, and profile update (minimal authentication, not fully standardized).
- **Lyrics API** (`/api/lyrics`): Lyrics search, save, and retrieval.
- **Metadata API** (`/api/metadata`): Song metadata search (iTunes, MusicBrainz, etc.).
- **YouTube API** (`/api/youtube`): YouTube video search and download.
- **YouTube Music API** (`/api/youtube-music`): YouTube Music search (experimental).

> **Note:** Some endpoints (notably in `users` and `karaoke_queue`) do not use the thin controller/service pattern and return raw `jsonify` responses. Migration to full standardization is ongoing.

### Example Endpoints

```python
# /api/songs endpoints
GET    /api/songs              # List all songs with pagination
GET    /api/songs/<id>         # Get specific song details
PUT    /api/songs/<id>         # Update song metadata
DELETE /api/songs/<id>         # Delete song and files
GET    /api/songs/search       # Search songs by query
POST   /api/songs/sync         # Sync filesystem with database
GET    /api/songs/artists      # List artists with song counts

# /api/jobs endpoints
GET    /api/jobs               # List all jobs with status
GET    /api/jobs/<id>          # Get specific job details
POST   /api/jobs/<id>/cancel   # Cancel running job
DELETE /api/jobs/<id>          # Delete completed job
GET    /api/jobs/status        # Get job system status
GET    /api/jobs/dismissed     # List dismissed jobs

# /karaoke-queue endpoints
GET    /karaoke-queue/         # Get current queue state
POST   /karaoke-queue/         # Add song to queue
PUT    /karaoke-queue/reorder  # Reorder queue items
DELETE /karaoke-queue/<id>     # Remove song from queue
POST   /karaoke-queue/clear    # Clear entire queue

# /users endpoints
POST   /users/register         # Register new user
POST   /users/login            # User login
PATCH  /users/<id>             # Update user profile

# /api/lyrics endpoints
GET    /api/lyrics/search      # Search for lyrics
POST   /api/lyrics/save        # Save lyrics for a song
GET    /api/lyrics/<song_id>   # Get lyrics for a song

# /api/metadata endpoints
GET    /api/metadata/search    # Search for song metadata

# /api/youtube endpoints
GET    /api/youtube/search     # Search YouTube videos
POST   /api/youtube/download   # Download and process video

# /api/youtube-music endpoints
GET    /api/youtube-music/search # Search YouTube Music
```
## Request/Response Examples

### Successful Song Retrieval

**Request:**

```http
GET /api/songs?limit=10&offset=0
```

**Response:**

```json
{
  "success": true,
  "message": "Retrieved 10 songs",
  "data": [
    {
      "id": "song-123",
      "title": "Example Song",
      "artist": "Example Artist",
      "duration": 180,
      "hasVocals": true,
      "hasInstrumental": true
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 10,
      "total": 45,
      "pages": 5
    }
  }
}
```

### Validation Error Example

**Request:**

```http
POST /api/songs/search
Content-Type: application/json

{
    "q": "",
    "limit": 150
}
```

**Response:**

```json
{
  "success": false,
  "error": {
    "message": "Validation failed",
    "code": "VALIDATION_ERROR",
    "details": {
      "q": ["Field cannot be empty"],
      "limit": ["Must be between 1 and 100"]
    }
  }
}
```

### Service Error Example

**Request:**

```http
GET /api/songs/invalid-id
```

**Response:**

```json
{
  "success": false,
  "error": {
    "message": "Song not found",
    "code": "NOT_FOUND",
    "details": "Song with ID 'invalid-id' does not exist"
  }
}
```

## Validation Schemas

### Song Operations

```python
class SongSearchSchema(Schema):
    q = fields.Str(required=True, validate=lambda x: len(x.strip()) > 0)
    limit = fields.Int(missing=50, validate=lambda x: 0 < x <= 100)
    offset = fields.Int(missing=0, validate=lambda x: x >= 0)

class SongUpdateSchema(Schema):
    title = fields.Str(validate=lambda x: len(x.strip()) > 0)
    artist = fields.Str(validate=lambda x: len(x.strip()) > 0)
    album = fields.Str()
    genre = fields.Str()
```

### YouTube Operations

```python
class YouTubeSearchSchema(Schema):
    query = fields.Str(required=True, validate=lambda x: len(x.strip()) > 0)
    max_results = fields.Int(missing=10, validate=lambda x: 1 <= x <= 50)

class YouTubeDownloadSchema(Schema):
    video_id = fields.Str(required=True)
    title = fields.Str(required=True)
    artist = fields.Str(required=True)
    duration = fields.Int()
```

## Error Code Standards

### HTTP Status Code Mapping

- **200 OK**: Successful operation
- **201 Created**: Resource created successfully
- **400 Bad Request**: Validation errors, malformed requests
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource does not exist
- **409 Conflict**: Resource already exists or conflict
- **422 Unprocessable Entity**: Business logic validation failed
- **500 Internal Server Error**: Unexpected server errors
- **503 Service Unavailable**: External service unavailable

### Application Error Codes

- **VALIDATION_ERROR**: Input validation failed
- **NOT_FOUND**: Requested resource not found
- **CONFLICT**: Resource already exists
- **SERVICE_ERROR**: Business logic error
- **EXTERNAL_API_ERROR**: External service failure
- **PROCESSING_ERROR**: Background job processing error
- **INTERNAL_ERROR**: Unexpected system error

## Integration Points

### Service Layer Integration

Controllers depend on service interfaces for business logic:

```python
# Dependency injection pattern
from app.services import get_song_service, get_youtube_service

def get_songs():
    song_service = get_song_service()
    return song_service.get_songs()
```

### WebSocket Integration

Real-time updates for job progress and queue changes:

```python
# Broadcast job updates via WebSocket
@socketio.on('subscribe_job_updates')
def handle_job_subscription(data):
    job_id = data.get('job_id')
    join_room(f'job_{job_id}')
    emit('subscription_confirmed', {'job_id': job_id})
```

### Background Job Integration

API endpoints trigger background jobs and return immediately:

```python
@youtube_bp.route('/download', methods=['POST'])
def download_youtube_video(validated_data):
    # Create background job
    job_id = jobs_service.create_youtube_job(
        video_id=validated_data['video_id'],
        metadata=validated_data
    )

    return APIResponse.success(
        data={'job_id': job_id},
        message="YouTube download started",
        status_code=202  # Accepted
    )
```

## Security Considerations

### Input Sanitization

All input is validated and sanitized before processing:

```python
def sanitize_filename(filename):
    """Remove dangerous characters from filenames"""
    return re.sub(r'[^\w\s-]', '', filename).strip()

def validate_song_id(song_id):
    """Validate song ID format"""
    if not re.match(r'^[a-f0-9-]{36}$', song_id):
        raise ValidationError("Invalid song ID format")
```

### Rate Limiting

API endpoints implement rate limiting to prevent abuse:

```python
from flask_limiter import Limiter

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@song_bp.route('/search')
@limiter.limit("10 per minute")
def search_songs():
    # Search implementation
    pass
```

### CORS Configuration

Cross-origin requests are properly configured:

```python
from flask_cors import CORS

CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

## Performance Optimization

### Response Caching

Frequently accessed data is cached to improve performance:

```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@song_bp.route('')
@cache.cached(timeout=300)  # Cache for 5 minutes
def get_songs():
    # Implementation
    pass
```

### Pagination

Large datasets are paginated to improve response times:

```python
def get_paginated_songs(page=1, per_page=50):
    offset = (page - 1) * per_page
    songs = song_service.get_songs_paginated(
        limit=per_page,
        offset=offset
    )
    total = song_service.count_songs()

    return APIResponse.paginated(
        data=[song.dict() for song in songs],
        page=page,
        per_page=per_page,
        total=total
    )
```

## Testing Strategy

### Unit Testing

Controllers are tested in isolation with mocked services:

```python
def test_get_songs_success(mock_song_service):
    mock_song_service.get_songs.return_value = [mock_song]

    response = client.get('/api/songs')

    assert response.status_code == 200
    assert response.json['success'] is True
    assert len(response.json['data']) == 1
```

### Integration Testing

End-to-end tests verify the complete request/response cycle:

```python
def test_youtube_download_workflow():
    # Test complete YouTube download workflow
    response = client.post('/api/youtube/download', json={
        'video_id': 'test123',
        'title': 'Test Song',
        'artist': 'Test Artist'
    })

    assert response.status_code == 202
    job_id = response.json['data']['job_id']

    # Verify job was created
    job_response = client.get(f'/api/jobs/{job_id}')
    assert job_response.status_code == 200
```

## Migration from Current Implementation

### Phase 1: Response Standardization
- Implement and use `APIResponse` or `success_response`/`error_response` utilities in all endpoints.
- Update endpoints in `users.py`, `karaoke_queue.py`, and legacy routes to use standardized responses.

### Phase 2: Request Validation
- Apply validation decorators to all endpoints (currently inconsistent).
- Ensure all input is validated and sanitized before processing.

### Phase 3: Error Handling
- Apply centralized error handling decorators (`handle_api_error`) to all endpoints.
- Map exceptions to appropriate HTTP status codes and error codes.

### Phase 4: Thin Controllers and Service Layer
- Refactor endpoints to delegate all business logic to service classes.
- Remove direct model/database access from controllers.
- Add/expand controller-level and integration tests.

> **Current Status:**
> - Some endpoints (notably in `songs.py`, `users.py`, and `karaoke_queue.py`) still use direct model/database access and do not use the thin controller pattern or full validation/error handling. Migration is ongoing.
## Dependencies

### Required Libraries

- **Flask**: Web framework and routing
- **Marshmallow**: Request/response serialization and validation
- **Flask-CORS**: Cross-origin resource sharing
- **Flask-Limiter**: Rate limiting
- **Flask-Caching**: Response caching

### Internal Dependencies

- **Service Layer**: All business logic delegation
- **WebSocket Service**: Real-time communication
- **Configuration Service**: API settings and limits

## Future Enhancements

### Advanced Features

- **API Versioning**: Support multiple API versions
- **GraphQL Integration**: Alternative query interface
- **OpenAPI Documentation**: Auto-generated API docs
- **Webhook Support**: Outbound notifications

### Performance Improvements

- **Response Compression**: Gzip compression for large responses
- **CDN Integration**: Static asset optimization
- **Database Query Optimization**: Eager loading and query tuning
- **Async Endpoints**: Non-blocking request handling

### Security Enhancements

- **JWT Authentication**: Stateless authentication
- **API Key Management**: Service-to-service authentication
- **Request Signing**: Tamper detection
- **Advanced Rate Limiting**: User-based and endpoint-specific limits
