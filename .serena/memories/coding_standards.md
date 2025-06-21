# Coding Standards and Conventions

## Critical Backend Standards

### Logging (MANDATORY)
Every Python module must follow this pattern:
```python
import logging

# At the top of every .py file, after imports
logger = logging.getLogger(__name__)
```

**Required Usage**:
- `logger.info("message", param)` - Use logger, not print()
- `logger.error("message", param, exc_info=True)` - Always include exc_info for exceptions
- NO direct `logging.info()` calls
- NO `print()` statements in production code
- NO `current_app.logger` usage

### Error Handling Pattern
All API endpoints must use:
```python
from ..utils.error_handlers import handle_api_error
from ..exceptions import DatabaseError, ValidationError

@bp.route("/endpoint")
@handle_api_error  # REQUIRED decorator
def endpoint_function():
    try:
        # logic here
        return jsonify(result)
    except ValidationError:
        raise  # Let error handlers deal with it
    except ConnectionError as e:
        raise DatabaseError("message", "ERROR_CODE", {"context": "value"})
```

### Type Hints (REQUIRED)
All functions must have proper type annotations:
```python
def get_song_by_id(song_id: str) -> Optional[DbSong]:
    """Get song by ID from database."""
```

### Documentation
Functions require docstrings with Args, Returns, and Raises sections.

## Frontend Standards
- TypeScript strict mode
- ESLint with React hooks rules
- Prettier for formatting
- Consistent component structure with proper prop typing