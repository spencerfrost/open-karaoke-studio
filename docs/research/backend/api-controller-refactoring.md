# API Controller Refactoring

## Issue Type

🏗️ **Architecture** | **Priority: Medium** | **Effort: Small**

## Summary

Refactor API controllers to be thin and only handle HTTP concerns, removing all business logic and delegating to the service layer. Establish consistent patterns for error handling, request validation, and response formatting across all API endpoints.

## Current Problems

### Fat Controllers with Business Logic

Current API controllers contain business logic that should be in services:

```python
# backend/app/api/songs.py - Business logic in controller
@song_bp.route('', methods=['GET'])
def get_songs():
    # Database logic
    db_songs = database.get_all_songs()

    # Business logic - should be in service
    if not db_songs:
        current_app.logger.info("No songs found in database, syncing from filesystem")
        songs_added = database.sync_songs_with_filesystem()
        db_songs = database.get_all_songs()

    # Transformation logic - should be in service
    songs_list = [Song.model_validate(song.to_dict()) for song in db_songs]
```

### Inconsistent Error Handling

Different endpoints handle errors differently:

- Some return different error formats
- Inconsistent HTTP status codes
- Mixed logging approaches

### No Request Validation

Controllers don't validate incoming requests consistently.

## Proposed Solution

### 1. Create API Response Standards

```python
# backend/app/api/responses.py - Enhanced response utilities
from typing import Any, Optional, Dict, List
from flask import jsonify, Response
import logging

logger = logging.getLogger(__name__)

class APIResponse:
    """Standardized API response format"""

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        status_code: int = 200,
        meta: Optional[Dict[str, Any]] = None
    ) -> Response:
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
    def error(
        message: str = "An error occurred",
        details: Optional[str] = None,
        status_code: int = 500,
        error_code: Optional[str] = None
    ) -> Response:
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
    def not_found(resource: str = "Resource", identifier: str = "") -> Response:
        """Create standardized not found response"""
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"

        return APIResponse.error(
            message=message,
            status_code=404,
            error_code="NOT_FOUND"
        )

    @staticmethod
    def validation_error(errors: Dict[str, List[str]]) -> Response:
        """Create standardized validation error response"""
        return APIResponse.error(
            message="Validation failed",
            details=errors,
            status_code=400,
            error_code="VALIDATION_ERROR"
        )

    @staticmethod
    def paginated(
        data: List[Any],
        page: int,
        per_page: int,
        total: int,
        message: str = "Success"
    ) -> Response:
        """Create paginated response"""
        meta = {
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }

        return APIResponse.success(
            data=data,
            message=message,
            meta=meta
        )
```

### 2. Create Request Validation Decorators

```python
# backend/app/api/validation.py
from functools import wraps
from typing import Dict, Any, Optional, Callable
from flask import request, jsonify
from marshmallow import Schema, ValidationError as MarshmallowValidationError

def validate_json(schema: Schema) -> Callable:
    """Decorator to validate JSON request body"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                # Validate request JSON
                data = schema.load(request.get_json() or {})
                # Pass validated data to the route function
                return f(validated_data=data, *args, **kwargs)
            except MarshmallowValidationError as e:
                from .responses import APIResponse
                return APIResponse.validation_error(e.messages)
        return wrapper
    return decorator

def validate_query_params(schema: Schema) -> Callable:
    """Decorator to validate query parameters"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                # Validate query parameters
                data = schema.load(request.args.to_dict())
                return f(query_params=data, *args, **kwargs)
            except MarshmallowValidationError as e:
                from .responses import APIResponse
                return APIResponse.validation_error(e.messages)
        return wrapper
    return decorator

def require_auth(f):
    """Decorator to require authentication (placeholder)"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Authentication logic would go here
        # For now, just pass through
        return f(*args, **kwargs)
    return wrapper
```

### 3. Create Exception Handling Decorator

```python
# backend/app/api/decorators.py
from functools import wraps
from typing import Callable
import logging
from flask import current_app
from ..exceptions import ServiceError, NotFoundError, ValidationError
from .responses import APIResponse

logger = logging.getLogger(__name__)

def handle_api_errors(f: Callable) -> Callable:
    """Decorator to handle service layer errors consistently"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except NotFoundError as e:
            logger.warning(f"Not found in {f.__name__}: {e}")
            return APIResponse.not_found(details=str(e))
        except ValidationError as e:
            logger.warning(f"Validation error in {f.__name__}: {e}")
            return APIResponse.validation_error({"validation": [str(e)]})
        except ServiceError as e:
            logger.error(f"Service error in {f.__name__}: {e}")
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

def log_api_call(custom_logger: logging.Logger = None) -> Callable:
    """Decorator to log API calls"""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            api_logger = custom_logger or logger
            api_logger.info(f"API call: {f.__name__} - {request.method} {request.path}")

            try:
                result = f(*args, **kwargs)
                api_logger.info(f"API call completed: {f.__name__}")
                return result
            except Exception as e:
                api_logger.error(f"API call failed: {f.__name__} - {e}")
                raise
        return wrapper
    return decorator
```

### 4. Refactored Songs API Controller

```python
# backend/app/api/songs.py - Refactored thin controller
import logging
from flask import Blueprint, request
from marshmallow import Schema, fields

from ..services import get_song_service
from ..services.interfaces.song_service import SongServiceInterface
from .responses import APIResponse
from .decorators import handle_api_errors, log_api_call
from .validation import validate_query_params, validate_json

logger = logging.getLogger(__name__)
song_bp = Blueprint('songs', __name__, url_prefix='/api/songs')

# Request validation schemas
class SongSearchSchema(Schema):
    q = fields.Str(required=True, validate=lambda x: len(x.strip()) > 0)
    limit = fields.Int(missing=50, validate=lambda x: 0 < x <= 100)
    offset = fields.Int(missing=0, validate=lambda x: x >= 0)

class SongListSchema(Schema):
    limit = fields.Int(missing=50, validate=lambda x: 0 < x <= 100)
    offset = fields.Int(missing=0, validate=lambda x: x >= 0)

class SongUpdateSchema(Schema):
    title = fields.Str()
    artist = fields.Str()
    album = fields.Str()
    # Other metadata fields...

@song_bp.route('', methods=['GET'])
@handle_api_errors
@log_api_call(logger)
@validate_query_params(SongListSchema())
def get_songs(query_params):
    """Get all songs - thin controller using service layer"""
    song_service: SongServiceInterface = get_song_service()

    # Get songs through service layer
    songs = song_service.get_all_songs(
        limit=query_params.get('limit'),
        offset=query_params.get('offset')
    )

    # Convert to response format
    response_data = [
        song.model_dump(mode='json') if hasattr(song, 'model_dump') else song.dict()
        for song in songs
    ]

    return APIResponse.success(
        data=response_data,
        message=f"Retrieved {len(response_data)} songs"
    )

@song_bp.route('/<song_id>', methods=['GET'])
@handle_api_errors
@log_api_call(logger)
def get_song(song_id: str):
    """Get single song - thin controller using service layer"""
    song_service: SongServiceInterface = get_song_service()

    song = song_service.get_song_by_id(song_id)
    if not song:
        return APIResponse.not_found("Song", song_id)

    response_data = song.model_dump(mode='json') if hasattr(song, 'model_dump') else song.dict()
    return APIResponse.success(data=response_data)

@song_bp.route('/search', methods=['GET'])
@handle_api_errors
@log_api_call(logger)
@validate_query_params(SongSearchSchema())
def search_songs(query_params):
    """Search songs - thin controller using service layer"""
    song_service: SongServiceInterface = get_song_service()

    songs = song_service.search_songs(
        query=query_params['q'],
        limit=query_params.get('limit')
    )

    response_data = [
        song.model_dump(mode='json') if hasattr(song, 'model_dump') else song.dict()
        for song in songs
    ]

    return APIResponse.success(
        data=response_data,
        message=f"Found {len(response_data)} songs matching '{query_params['q']}'"
    )

@song_bp.route('/<song_id>', methods=['PUT'])
@handle_api_errors
@log_api_call(logger)
@validate_json(SongUpdateSchema())
def update_song(song_id: str, validated_data):
    """Update song metadata - thin controller using service layer"""
    song_service: SongServiceInterface = get_song_service()

    # Check if song exists
    existing_song = song_service.get_song_by_id(song_id)
    if not existing_song:
        return APIResponse.not_found("Song", song_id)

    # Update through service layer
    # This would require implementing update methods in service
    updated_song = song_service.update_song_metadata(song_id, validated_data)

    if not updated_song:
        return APIResponse.error("Failed to update song", status_code=500)

    response_data = updated_song.model_dump(mode='json') if hasattr(updated_song, 'model_dump') else updated_song.dict()
    return APIResponse.success(
        data=response_data,
        message=f"Successfully updated song {song_id}"
    )

@song_bp.route('/<song_id>', methods=['DELETE'])
@handle_api_errors
@log_api_call(logger)
def delete_song(song_id: str):
    """Delete song - thin controller using service layer"""
    song_service: SongServiceInterface = get_song_service()

    # Check if song exists
    existing_song = song_service.get_song_by_id(song_id)
    if not existing_song:
        return APIResponse.not_found("Song", song_id)

    # Delete through service layer
    success = song_service.delete_song(song_id, cleanup_files=True)

    if not success:
        return APIResponse.error("Failed to delete song", status_code=500)

    return APIResponse.success(message=f"Successfully deleted song {song_id}")
```

### 5. Apply Same Pattern to Other Controllers

Apply the same thin controller pattern to other API modules:

- `youtube.py` - Use YouTube service
- `lyrics.py` - Use Lyrics service
- `queue.py` - Use Queue service
- `users.py` - Use User service

## Acceptance Criteria

- [ ] All API controllers are thin and only handle HTTP concerns
- [ ] Business logic removed from all API endpoints
- [ ] Standardized response format across all endpoints
- [ ] Consistent error handling with proper HTTP status codes
- [ ] Request validation using schemas and decorators
- [ ] Proper logging for all API operations
- [ ] API endpoints use service container for dependency injection
- [ ] Clear separation between HTTP layer and business logic
- [ ] Existing API functionality preserved (no breaking changes)

## Implementation Steps

1. Create standardized response utilities
2. Create request validation decorators
3. Create error handling decorators
4. Refactor songs API controller to use services
5. Apply same pattern to other controllers
6. Add request validation schemas
7. Test all endpoints work correctly
8. Update API documentation

## Files to Create

- `backend/app/api/validation.py`
- `backend/app/api/decorators.py`

## Files to Modify

- `backend/app/api/responses.py` (enhance with standards)
- `backend/app/api/songs.py` (refactor to thin controller)
- `backend/app/api/youtube.py` (refactor to thin controller)
- `backend/app/api/lyrics.py` (refactor to thin controller)
- `backend/app/api/queue.py` (refactor to thin controller)
- `backend/app/api/users.py` (refactor to thin controller)

## Dependencies

- Requires all service layers to be implemented
- Requires service container for dependency injection
- Requires proper exception classes
- May require marshmallow for request validation

## Testing Benefits

- Controllers become much easier to test
- Service layer can be mocked for API testing
- Request validation can be tested independently
- Error handling can be tested consistently

## API Documentation

After refactoring, API documentation should be updated to reflect:

- Standardized response formats
- Consistent error responses
- Request validation requirements
- Proper HTTP status code usage

## Related Issues

- Issue #004a (Song Service) - API controllers will use Song Service
- Issue #004e (Service Interfaces) - Controllers will use service container
- Issue #003 (Error Handling) - Controllers will use standardized error handling
