✅ **COMPLETED** Centralized logging standardization is complete. All backend modules now use the standardized `logger = logging.getLogger(__name__)` pattern. Remaining tasks focus on error response standardization and centralized error handlers.

# Error Handling & Logging Standardization

## Issue Type

🐛 **Bug Fix** / 🏗️ **Architecture** | **Priority: High** | **Effort: Medium**

## Summary

**PHASE 1 COMPLETE**: ✅ Logging standardization implemented across all backend modules
**PHASE 2 PENDING**: Centralized error handler registration and standardized API responses

## ✅ COMPLETED - Phase 1: Logging Standardization

### **✅ Fixed Mixed Logging Approaches**

All modules now use consistent pattern:

```python
import logging
logger = logging.getLogger(__name__)

# Usage:
logger.info("Information message")
logger.error("Error message", exc_info=True)
```

### **✅ Eliminated Print Statements**

- Replaced all print statements in production code with logger calls
- Retained print statements only in test functions, server startup, and migration scripts
- Added logger imports to all backend modules

### **✅ Centralized Configuration**

- All modules use centralized logging config from `backend/app/config/logging.py`
- Dual output: console + file (`backend/logs/errors.log`)
- Automatic log rotation to prevent disk space issues

## ⏳ PENDING - Phase 2: Error Response Standardization

### **Inconsistent Error Handling in API Endpoints**

Current state varies across endpoints:

```python
# songs.py - Basic try/catch without proper error responses
try:
    db_songs = database.get_songs()
    # ... processing
except Exception as e:
    # No proper error response format
    logger.error(f"Error: {e}", exc_info=True)  # ✅ Logging now correct
    return jsonify({"error": "Something went wrong"}), 500  # ❌ Response format inconsistent
```

### No Centralized Error Response Format

Different endpoints return errors in different formats:

```python
# Various error response formats across endpoints
return jsonify({"error": "Song not found"}), 404
return {"status": "error", "message": "Job not found"}
return jsonify({"success": False, "error": str(e)}), 500
```

### **Exception Handling Without Context**

```python
# In database.py - Generic exception handling
except Exception as e:
    logger.error(f"Error getting songs from database: {e}", exc_info=True)  # ✅ Logging now correct
    return []  # ❌ Silent failure still needs addressing
```

## ✅ COMPLETED WORK

### **1. Logging Standardization - DONE**

- ✅ Added `logger = logging.getLogger(__name__)` to all backend modules
- ✅ Replaced all `print()` statements with appropriate logger calls
- ✅ Replaced all `logging.error/info/warning` with `logger.error/info/warning`
- ✅ Replaced all `current_app.logger` calls with module loggers
- ✅ Added `exc_info=True` to error logging for proper stack traces
- ✅ Configured dual logging (console + file) through centralized config

### **Files Updated:**

- ✅ `backend/app/services/audio.py` - Fixed 12 print statements + logger setup
- ✅ `backend/app/services/file_management.py` - Fixed 4 logging calls
- ✅ `backend/app/services/itunes_service.py` - Fixed 16 logging calls
- ✅ `backend/app/db/database.py` - Fixed 8 logging calls
- ✅ `backend/app/db/song_operations.py` - Fixed 8 logging calls
- ✅ `backend/app/api/*.py` - All API endpoints updated
- ✅ `backend/app/db/models/job.py` - All print statements replaced

## Proposed Solution

### 1. Structured Logging Configuration

```python
# logging/config.py
import logging
import sys
from pathlib import Path
from typing import Dict, Any

def setup_logging(
    log_level: str = "INFO",
    log_file: str = None,
    structured: bool = False
) -> None:
    """Configure application logging"""

    # Configure root logger
    logging.root.handlers = []

    # Create formatter
    if structured:
        import structlog
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.add_logger_name,
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        formatter = None
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if formatter:
        console_handler.setFormatter(formatter)

    # File handler (optional)
    handlers = [console_handler]
    if log_file:
        file_handler = logging.FileHandler(log_file)
        if formatter:
            file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=handlers
    )

    # Set specific logger levels
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
```

### 2. Custom Exception Classes

```python
# exceptions.py
class OpenKaraokeError(Exception):
    """Base exception for Open Karaoke Studio"""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class ServiceError(OpenKaraokeError):
    """Service layer errors"""
    pass

class DatabaseError(OpenKaraokeError):
    """Database operation errors"""
    pass

class AudioProcessingError(OpenKaraokeError):
    """Audio processing errors"""
    pass

class ValidationError(OpenKaraokeError):
    """Input validation errors"""
    pass

class NotFoundError(OpenKaraokeError):
    """Resource not found errors"""
    pass

class AuthenticationError(OpenKaraokeError):
    """Authentication/authorization errors"""
    pass
```

### 3. Centralized Error Response Handler

```python
# api/error_handlers.py
from flask import jsonify, current_app
from typing import Tuple, Dict, Any
import traceback

def register_error_handlers(app):
    """Register centralized error handlers with Flask app"""

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError) -> Tuple[Dict[str, Any], int]:
        return create_error_response(
            message=error.message,
            error_code=error.error_code or "VALIDATION_ERROR",
            status_code=400
        )

    @app.errorhandler(NotFoundError)
    def handle_not_found_error(error: NotFoundError) -> Tuple[Dict[str, Any], int]:
        return create_error_response(
            message=error.message,
            error_code=error.error_code or "NOT_FOUND",
            status_code=404
        )

    @app.errorhandler(ServiceError)
    def handle_service_error(error: ServiceError) -> Tuple[Dict[str, Any], int]:
        current_app.logger.error(f"Service error: {error.message}")
        return create_error_response(
            message="Internal service error",
            error_code=error.error_code or "SERVICE_ERROR",
            status_code=500
        )

    @app.errorhandler(500)
    def handle_internal_error(error) -> Tuple[Dict[str, Any], int]:
        current_app.logger.error(f"Internal server error: {error}")
        if current_app.debug:
            current_app.logger.error(traceback.format_exc())

        return create_error_response(
            message="Internal server error",
            error_code="INTERNAL_ERROR",
            status_code=500
        )

def create_error_response(
    message: str,
    error_code: str,
    status_code: int,
    details: Dict[str, Any] = None
) -> Tuple[Dict[str, Any], int]:
    """Create standardized error response"""
    response = {
        "success": False,
        "error": {
            "message": message,
            "code": error_code,
            "status": status_code
        }
    }

    if details:
        response["error"]["details"] = details

    return jsonify(response), status_code
```

### 4. API Response Helpers

```python
# api/responses.py
from flask import jsonify
from typing import Any, Dict, Optional

def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200
) -> tuple:
    """Create standardized success response"""
    response = {
        "success": True,
        "message": message
    }

    if data is not None:
        response["data"] = data

    return jsonify(response), status_code

def paginated_response(
    data: list,
    total: int,
    page: int = 1,
    per_page: int = 10,
    message: str = "Success"
) -> tuple:
    """Create paginated response"""
    response = {
        "success": True,
        "message": message,
        "data": data,
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        }
    }

    return jsonify(response), 200
```

### 5. Logging Decorators for Consistent Logging

```python
# utils/decorators.py
import functools
import logging
import time
from typing import Callable, Any

def log_function_call(logger: logging.Logger = None):
    """Decorator to log function calls with execution time"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            func_logger = logger or logging.getLogger(func.__module__)

            start_time = time.time()
            func_logger.info(f"Starting {func.__name__}")

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                func_logger.info(
                    f"Completed {func.__name__} in {execution_time:.2f}s"
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                func_logger.error(
                    f"Error in {func.__name__} after {execution_time:.2f}s: {e}"
                )
                raise

        return wrapper
    return decorator

def log_api_call(logger: logging.Logger = None):
    """Decorator for API endpoint logging"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            from flask import request

            func_logger = logger or logging.getLogger(func.__module__)

            func_logger.info(
                f"API call: {request.method} {request.path}",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "remote_addr": request.remote_addr,
                    "user_agent": request.headers.get("User-Agent")
                }
            )

            try:
                return func(*args, **kwargs)
            except Exception as e:
                func_logger.error(f"API error in {func.__name__}: {e}")
                raise

        return wrapper
    return decorator
```

### 6. Updated API Endpoint Example

```python
# api/songs.py - Updated with proper error handling
import logging
from flask import Blueprint, request
from app.exceptions import NotFoundError, ServiceError
from app.api.responses import success_response, paginated_response
from app.api.decorators import log_api_call
from app.services.song_service import SongService

logger = logging.getLogger(__name__)
song_bp = Blueprint('songs', __name__, url_prefix='/api/songs')

@song_bp.route('', methods=['GET'])
@log_api_call(logger)
def get_songs():
    """Get all songs with proper error handling and logging"""
    try:
        song_service = SongService()
        songs = song_service.get_songs()

        logger.info(f"Retrieved {len(songs)} songs successfully")
        return success_response(
            data=songs,
            message=f"Retrieved {len(songs)} songs"
        )

    except ServiceError as e:
        logger.error(f"Service error retrieving songs: {e}")
        raise  # Will be handled by error handler
    except Exception as e:
        logger.error(f"Unexpected error retrieving songs: {e}")
        raise ServiceError("Failed to retrieve songs")

@song_bp.route('/<song_id>', methods=['GET'])
@log_api_call(logger)
def get_song(song_id: str):
    """Get single song with proper error handling"""
    try:
        song_service = SongService()
        song = song_service.get_song_by_id(song_id)

        if not song:
            raise NotFoundError(f"Song with ID {song_id} not found")

        return success_response(data=song)

    except NotFoundError:
        raise  # Will be handled by error handler
    except Exception as e:
        logger.error(f"Error retrieving song {song_id}: {e}")
        raise ServiceError(f"Failed to retrieve song {song_id}")
```

## Acceptance Criteria

### ✅ COMPLETED - Phase 1: Logging

- [x] ~~Structured logging configured across all modules~~
- [x] ~~All print statements replaced with proper logging calls~~
- [x] ~~Centralized logging configuration implemented~~
- [x] ~~All API endpoints updated to use module loggers~~
- [x] ~~Service layer methods use proper logging~~
- [x] ~~Database operations include proper error logging~~

### ⏳ PENDING - Phase 2: Error Response Standardization

- [ ] Custom exception classes implemented for different error types
- [ ] Centralized error handlers registered with Flask app
- [ ] Standardized error response format across all endpoints
- [ ] API response helpers for consistent success responses
- [ ] Logging decorators implemented for function and API call tracking
- [ ] All API endpoints updated to use new error handling patterns
- [ ] Service layer methods raise appropriate custom exceptions

## Files to Modify (Phase 2)

- `backend/app/__init__.py` - Register error handlers
- `backend/app/api/*.py` - Update error response formats
- `backend/app/services/*.py` - Add custom exception raising

## Files to Create (Phase 2)

- `backend/app/exceptions.py`
- `backend/app/api/error_handlers.py`
- `backend/app/api/responses.py`
- `backend/app/utils/decorators.py`

## Testing

- [ ] Error responses follow standardized format
- [ ] Custom exceptions are properly caught and handled
- [ ] Logging outputs to configured destinations
- [ ] API endpoints return consistent response structures
- [ ] Error logging includes sufficient context for debugging

## Related Issues

- Issue #002 (Database Layer) - Database error handling
- Issue #004 (Service Layer) - Service error handling patterns
- Issue #006 (Testing Infrastructure) - Error handling testing
