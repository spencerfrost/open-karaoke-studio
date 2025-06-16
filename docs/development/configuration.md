# Configuration Management

## Overview

Open Karaoke Studio uses a sophisticated environment-based configuration system that provides centralized settings management with proper environment variable handling and inheritance hierarchy.

## Configuration Structure

```
backend/app/config/
├── __init__.py          # Environment-based config loading
├── base.py              # Base configuration class
├── development.py       # Development environment settings
├── production.py        # Production environment settings
├── testing.py           # Testing environment settings
└── logging.py           # Centralized logging configuration
```

## Environment-Based Loading

The system automatically loads the appropriate configuration based on the `FLASK_ENV` environment variable:

```python
from app.config import get_config

config = get_config()  # Automatically selects environment
```

Available environments:
- `development` (default)
- `production` 
- `testing`

## Configuration Classes

### Base Configuration

All environments inherit from `BaseConfig` which provides:

- **Flask Core Settings**: Secret key management, debug settings
- **Database Configuration**: SQLite path resolution, SQLAlchemy settings
- **File Management**: Library directory, temp directory, upload limits
- **Audio Processing**: Demucs model, MP3 bitrate settings
- **Celery Configuration**: Redis broker and result backend
- **Server Configuration**: Host, port, CORS origins

### Environment-Specific Configurations

#### Development Configuration
- Debug mode enabled
- Permissive CORS origins for local development
- Console logging with INFO level
- SQLite database in backend directory

#### Production Configuration
- Debug mode disabled
- Restricted CORS origins
- File-based logging with rotation
- Environment-specific database URL
- Security-focused settings

#### Testing Configuration
- Minimal logging (WARNING level only)
- In-memory or temporary database
- Fast configuration for test execution

## Environment Variables

### Required Variables

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
```

### Optional Variables with Defaults

```bash
# Environment
FLASK_ENV=development

# Database
DATABASE_URL=sqlite:///karaoke.db

# File Storage
LIBRARY_DIR=/path/to/karaoke_library
TEMP_DIR=/path/to/temp_downloads

# Redis/Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# CORS Origins (comma-separated)
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Audio Processing
DEMUCS_MODEL=htdemucs_ft
MP3_BITRATE=320
MAX_CONTENT_LENGTH=209715200

# Logging
LOG_LEVEL=INFO
LOG_DIR=/path/to/logs
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5
```

## Usage Examples

### Basic Configuration Access

```python
from app.config import get_config

config = get_config()

# Access configuration values
database_url = config.DATABASE_URL
library_dir = config.LIBRARY_DIR
cors_origins = config.CORS_ORIGINS  # Returns list
```

### Service Configuration

```python
# In service classes
class FileService:
    def __init__(self):
        self.config = get_config()
        self.library_dir = self.config.LIBRARY_DIR
        self.temp_dir = self.config.TEMP_DIR
```

### Database Configuration

```python
# Automatic configuration in database.py
from ..config import get_config

config = get_config()
DATABASE_URL = config.DATABASE_URL

engine = create_engine(DATABASE_URL)
```

## Configuration Validation

The system validates critical configuration on startup:

- **SECRET_KEY**: Must be provided in production
- **DATABASE_URL**: Validates SQLite path resolution
- **CORS_ORIGINS**: Validates comma-separated origin list
- **Directory Paths**: Ensures required directories exist

## Path Resolution

The configuration system intelligently resolves paths:

- **Absolute paths**: Used as-is
- **Relative paths**: Resolved relative to project root
- **SQLite URLs**: Automatically resolved to backend directory
- **Environment variables**: Override defaults when provided

## CORS Configuration

CORS origins are managed per environment:

```python
# Development: Permissive for local development
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173", 
    "http://192.168.50.112:5173"
]

# Production: Restricted to specific domains
DEFAULT_CORS_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com"
]

# Environment variable override
CORS_ORIGINS=https://prod.com,https://staging.com
```

## Logging Integration

Configuration seamlessly integrates with the logging system:

```python
from app.config.logging import setup_logging

config = get_config()
logging_config = setup_logging(config)
```

## Migration Notes

### From Old Configuration

The new system replaces scattered hardcoded values:

**Before:**
```python
# Mixed patterns throughout codebase
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'karaoke.db')}"
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CORS(app, origins="*")  # Hardcoded
```

**After:**
```python
# Centralized, environment-aware
config = get_config()
DATABASE_URL = config.DATABASE_URL
CELERY_BROKER_URL = config.CELERY_BROKER_URL
CORS(app, origins=config.CORS_ORIGINS)
```

## Benefits

1. **Centralized Management**: All configuration in one place
2. **Environment Awareness**: Automatic environment-specific settings
3. **Validation**: Configuration validation on startup
4. **Flexibility**: Environment variable overrides
5. **Security**: Proper secret management
6. **Maintainability**: Clear inheritance hierarchy
7. **Documentation**: Self-documenting configuration classes

## Best Practices

1. **Use environment variables** for sensitive values
2. **Provide sensible defaults** for development
3. **Validate required configuration** on startup
4. **Document environment variables** in `.env.example`
5. **Use type hints** for configuration properties
6. **Test configuration** in different environments

## Related Documentation

- [Environment Setup](../setup/README.md)
- [Logging Configuration](../../deployment/logging.md)
- [Database Configuration](../../architecture/backend/database-design.md)
