# Open Karaoke Studio - Backend Coding Standards

## Overview

This document defines the coding standards for the Open Karaoke Studio backend to ensure consistency, maintainability, and reliability across the codebase.

## 🚨 CRITICAL: Logging Standards

### **REQUIRED Pattern - Every Python Module:**

```python
import logging

# At the top of every .py file, after imports
logger = logging.getLogger(__name__)
```

### **✅ CORRECT Usage:**

```python
# Information logging
logger.info("Starting audio processing for song: %s", song_id)

# Warning logging
logger.warning("File not found, using default: %s", default_path)

# Error logging (ALWAYS include exc_info=True for exceptions)
try:
    process_audio(file_path)
except Exception as e:
    logger.error("Audio processing failed for %s: %s", file_path, e, exc_info=True)
    raise
```

### **❌ FORBIDDEN Patterns:**

```python
# DON'T - Direct logging module usage
logging.info("message")
logging.error("error")

# DON'T - Print statements in production code
print("Debug info")
print(f"Error: {error}")

# DON'T - Flask current_app.logger (inconsistent)
current_app.logger.info("message")

# DON'T - Silent failures
except Exception as e:
    pass  # Never do this!
```

## Code Review Requirements

### **Pre-Merge Checklist:**

Every backend file must have:

- [ ] `import logging` statement
- [ ] `logger = logging.getLogger(__name__)` declaration
- [ ] No `print()` statements in production code
- [ ] No direct `logging.info/error/warning()` calls
- [ ] No `current_app.logger` usage
- [ ] Proper error handling with `logger.error(..., exc_info=True)`
- [ ] **NEW:** Consistent error handling decorators and patterns
- [ ] **NEW:** Specific exception types instead of generic `Exception` catches
- [ ] **NEW:** Structured error responses with error codes

### **API Error Handling Standards (UPDATED June 2025):**

All API endpoints must follow the standardized error handling pattern:

```python
from ..utils.error_handlers import handle_api_error
from ..utils.validation import validate_json_request
from ..exceptions import DatabaseError, ValidationError, ServiceError

@bp.route("/endpoint", methods=["POST"])
@handle_api_error  # REQUIRED - Provides consistent error responses
@validate_json_request(RequestSchema)  # For POST/PUT endpoints
def endpoint_function(validated_data: RequestSchema):
    try:
        # Endpoint logic here
        logger.info("Processing request for %s", resource_id)
        return jsonify({"success": True})

    except ValidationError:
        raise  # Let error handlers deal with it
    except ConnectionError as e:
        # Specific database connection errors
        raise DatabaseError(
            "Database connection failed during operation",
            "DATABASE_CONNECTION_ERROR",
            {"resource_id": resource_id, "error": str(e)}
        )
    except OSError as e:
        # File system errors
        raise FileOperationError(
            "operation", "file_path", f"File system error: {str(e)}"
        )
    except Exception as e:
        # Final fallback with context
        raise ServiceError(
            "Unexpected error in endpoint",
            "ENDPOINT_ERROR",
            {"resource_id": resource_id, "error": str(e)}
        )
```

### **Exception Handling Standards:**

```python
# ✅ CORRECT - Specific error handling with context
def process_song(song_id: str) -> bool:
    try:
        logger.info("Processing song: %s", song_id)
        # ... processing logic
        logger.info("Successfully processed song: %s", song_id)
        return True
    except ValidationError as e:
        logger.warning("Validation failed for song %s: %s", song_id, e)
        raise  # Re-raise specific exceptions
    except ConnectionError as e:
        # Handle specific error types with context
        logger.error("Database connection failed for song %s: %s", song_id, e, exc_info=True)
        raise DatabaseError(
            "Database connection failed during song processing",
            "DATABASE_CONNECTION_ERROR",
            {"song_id": song_id, "error": str(e)}
        )
    except Exception as e:
        logger.error("Unexpected error processing song %s: %s", song_id, e, exc_info=True)
        raise ServiceError(
            "Unexpected error during song processing",
            "SONG_PROCESSING_ERROR",
            {"song_id": song_id, "error": str(e)}
        )

# ❌ FORBIDDEN - Generic exception handling without context
def bad_process_song(song_id: str):
    try:
        # ... logic
        pass
    except Exception as e:
        logger.error("Error: %s", e)  # No context, generic handling
        return False  # Silent failure
```

### **Error Response Standards:**

All API errors must return structured JSON responses:

```python
# ✅ CORRECT - Structured error response (handled automatically by decorators)
{
    "error": "Human-readable error message",
    "code": "MACHINE_READABLE_ERROR_CODE",
    "details": {
        "contextual_field": "value",
        "resource_id": "affected_resource"
    }
}

# ❌ FORBIDDEN - Inconsistent error responses
return {"error": "Something went wrong"}  # No error code
return "Error message", 500  # Not JSON
```

    except ValidationError as e:
        logger.warning("Validation failed for song %s: %s", song_id, e)
        raise
    except Exception as e:
        logger.error("Unexpected error processing song %s: %s", song_id, e, exc_info=True)
        raise

````

## Function Documentation Standards

### **Docstring Requirements:**

```python
def separate_audio(input_path: Path, song_dir: Path, status_callback=None) -> bool:
    """
    Separates audio file into vocals and instrumental tracks.

    Args:
        input_path: Path to the input audio file
        song_dir: Directory where processed files will be saved
        status_callback: Optional callback function for progress updates

    Returns:
        True if separation successful, False otherwise

    Raises:
        AudioProcessingError: If audio processing fails
        FileNotFoundError: If input file doesn't exist
    """
````

## Type Hints Requirements

### **Function Signatures:**

```python
# ✅ REQUIRED - Type hints for all parameters and return values
def get_song_by_id(song_id: str) -> Optional[DbSong]:
    """Get song by ID from database."""

def update_song_metadata(song_id: str, metadata: Dict[str, Any]) -> bool:
    """Update song metadata in database."""
```

## Error Response Standards (API)

### **Consistent Error Responses:**

```python
# ✅ CORRECT - API error handling
@song_bp.route('/<song_id>', methods=['GET'])
def get_song(song_id: str):
    try:
        song = song_service.get_song_by_id(song_id)
        if not song:
            logger.warning("Song not found: %s", song_id)
            return jsonify({"error": "Song not found"}), 404

        return jsonify({"data": song.to_dict()}), 200

    except Exception as e:
        logger.error("Error retrieving song %s: %s", song_id, e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
```

## File Organization Standards

### **Import Order:**

```python
# 1. Standard library imports
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

# 2. Third-party imports
from flask import Blueprint, jsonify, request
from sqlalchemy import create_engine

# 3. Local application imports
from ..config import get_config
from ..db.models import DbSong
from ..services.song_service import SongService

# 4. Logger setup (ALWAYS after imports)
logger = logging.getLogger(__name__)
```

## Testing Standards

### **Test Function Logging:**

```python
# ✅ OK - Print statements allowed in test functions
def test_song_creation():
    print("Testing song creation...")  # OK in tests

    # But still use logger for actual application logic being tested
    song_service = SongService()
    # song_service methods should use logger, not print
```

## Environment-Specific Guidelines

### **Development:**

- Console logging enabled for immediate feedback
- DEBUG level logging available
- Print statements acceptable in `__main__` blocks and test functions

### **Production:**

- File logging prioritized for persistence
- INFO level minimum
- NO print statements in production code paths
- All errors logged with full context

## Enforcement

### **Automated Checks:**

```bash
# Check for print statements in production code
grep -r "print(" backend/app/ --exclude-dir=__pycache__ --exclude="*test*" --exclude="*debug*"

# Check for direct logging usage
grep -r "logging\." backend/app/ --exclude-dir=__pycache__ | grep -v "getLogger"

# Check for missing logger declarations
grep -L "logger = logging.getLogger" backend/app/**/*.py
```

### **Code Review Focus:**

1. **Logging consistency** - Every file follows the pattern
2. **Error handling** - No silent failures, proper exception logging
3. **Type hints** - All functions properly typed
4. **Documentation** - Clear docstrings for public functions

## Migration from Legacy Patterns

### **Common Migrations:**

```python
# OLD - Direct logging
logging.info("Processing started")
# NEW - Module logger
logger.info("Processing started")

# OLD - Print debugging
print(f"Debug: {variable}")
# NEW - Logger debugging
logger.debug("Debug value: %s", variable)

# OLD - Flask logger
current_app.logger.error("Error occurred")
# NEW - Module logger
logger.error("Error occurred", exc_info=True)
```

This document should be referenced during all code reviews and new development to maintain consistency across the Open Karaoke Studio backend.
