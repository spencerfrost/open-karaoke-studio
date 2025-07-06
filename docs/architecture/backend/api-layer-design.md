# API Layer Architecture

## Overview

The API Layer provides a clean HTTP interface to the application's business logic through thin controllers that handle only HTTP concerns. It implements standardized response formats, request validation, error handling, and logging patterns across all endpoints while delegating all business logic to the service layer.

## Current Implementation Status

**Framework**: Flask with Blueprint architecture  
**Endpoints**: 35+ REST endpoints across 8 blueprints  
**Status**: Partially refactored, needs thin controller pattern implementation

## Core Responsibilities

### 1. HTTP Request/Response Handling

- Route requests to appropriate service methods
- Validate incoming request data and parameters
- Transform service responses to standardized HTTP format
- Handle HTTP-specific concerns (headers, status codes, content types)

### 2. Request Validation and Security

- Validate request payloads using schemas
- Sanitize input data before passing to services
- Implement authentication and authorization checks
- Handle CORS and other security headers

### 3. Standardized Response Formatting

- Consistent JSON response structure across all endpoints
- Standardized error response formats
- Pagination support for list endpoints
- Meta information inclusion (timing, pagination, etc.)

### 4. Error Handling and Logging

- Convert service exceptions to appropriate HTTP status codes
- Log all API requests and responses for debugging
- Provide detailed error information in development
- Sanitize error messages for production

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

The `APIResponse` class provides standardized response creation:

```python
class APIResponse:
    """Standardized API response utilities"""

    @staticmethod
    def success(data=None, message="Success", status_code=200, meta=None):
        """Create standardized success response"""
        response_data = {
            "success": True,
            "message": message,
            "data": data
        }
        if meta:
            response_data["meta"] = meta
        return jsonify(response_data), status_code

    @staticmethod
    def error(message, details=None, status_code=500, error_code=None):
        """Create standardized error response"""
        response_data = {
            "success": False,
            "error": {
                "message": message,
                "code": error_code or f"HTTP_{status_code}"
            }
        }
        if details:
            response_data["error"]["details"] = details
        return jsonify(response_data), status_code

    @staticmethod
    def paginated(data, page, per_page, total, message="Success"):
        """Create paginated response with meta information"""
        meta = {
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }
        return APIResponse.success(data=data, message=message, meta=meta)
```

### Request Validation

Input validation is handled through decorators and schemas:

```python
def validate_json(schema: Schema):
    """Decorator to validate JSON request body"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                data = schema.load(request.get_json() or {})
                return f(validated_data=data, *args, **kwargs)
            except MarshmallowValidationError as e:
                return APIResponse.validation_error(e.messages)
        return wrapper
    return decorator

def validate_query_params(schema: Schema):
    """Decorator to validate query parameters"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                data = schema.load(request.args.to_dict())
                return f(query_params=data, *args, **kwargs)
            except MarshmallowValidationError as e:
                return APIResponse.validation_error(e.messages)
        return wrapper
    return decorator
```

### Error Handling

Centralized error handling through decorators:

```python
def handle_api_errors(f):
    """Decorator to handle service layer errors consistently"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except NotFoundError as e:
            return APIResponse.not_found(details=str(e))
        except ValidationError as e:
            return APIResponse.validation_error({"validation": [str(e)]})
        except ServiceError as e:
            return APIResponse.error(
                message="Service error occurred",
                details=str(e),
                status_code=500,
                error_code="SERVICE_ERROR"
            )
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {e}", exc_info=True)
            return APIResponse.error(
                message="Internal server error",
                status_code=500,
                error_code="INTERNAL_ERROR"
            )
    return wrapper
```

## Blueprint Organization

### Songs API Blueprint

Handles all song-related operations:

```python
# /api/songs endpoints
GET    /api/songs              # List all songs with pagination
GET    /api/songs/<id>         # Get specific song details
PUT    /api/songs/<id>         # Update song metadata
DELETE /api/songs/<id>         # Delete song and files
GET    /api/songs/search       # Search songs by query
POST   /api/songs/sync         # Sync filesystem with database
```

### YouTube API Blueprint

Manages YouTube video processing:

```python
# /api/youtube endpoints
POST   /api/youtube/search     # Search YouTube videos
POST   /api/youtube/download   # Download and process video
GET    /api/youtube/info       # Get video information
```

### Jobs API Blueprint

Background job management:

```python
# /api/jobs endpoints
GET    /api/jobs               # List all jobs with status
GET    /api/jobs/<id>          # Get specific job details
POST   /api/jobs/<id>/cancel   # Cancel running job
DELETE /api/jobs/<id>          # Delete completed job
```

### Queue API Blueprint

Real-time karaoke queue management:

```python
# /api/queue endpoints
GET    /api/queue              # Get current queue state
POST   /api/queue              # Add song to queue
PUT    /api/queue/reorder      # Reorder queue items
DELETE /api/queue/<id>         # Remove song from queue
POST   /api/queue/clear        # Clear entire queue
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
      "favorite": false,
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
    favorite = fields.Bool()
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
from ..services import get_song_service, get_youtube_service

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

1. Implement `APIResponse` utility class
2. Update all endpoints to use standardized responses
3. Ensure backward compatibility during transition

### Phase 2: Request Validation

1. Implement validation decorators and schemas
2. Add validation to all endpoints
3. Improve error messages and codes

### Phase 3: Error Handling

1. Implement centralized error handling decorator
2. Map service exceptions to HTTP status codes
3. Add comprehensive logging

### Phase 4: Thin Controllers

1. Move business logic from controllers to services
2. Implement service dependency injection
3. Add controller-level testing

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
