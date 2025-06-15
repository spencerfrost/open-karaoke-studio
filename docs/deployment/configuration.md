# Configuration Management

## Overview

The Open Karaoke Studio backend now uses a centralized, environment-based configuration system located in `backend/app/config/`.

## Configuration Structure

```
backend/app/config/
├── __init__.py          # Configuration loader and exports
├── base.py             # Base configuration with common settings
├── development.py      # Development environment settings
├── production.py       # Production environment settings
└── testing.py          # Testing environment settings
```

## Environment Variables

Copy `.env.example` to `.env` and configure the following variables:

### Core Settings
- `FLASK_ENV`: Environment name (`development`, `production`, `testing`)
- `SECRET_KEY`: Flask secret key (required in production)
- `DATABASE_URL`: Database connection string
- `HOST`: Server host (default: `0.0.0.0`)
- `PORT`: Server port (default: `5123`)

### File Storage
- `LIBRARY_DIR`: Directory for processed karaoke files
- `TEMP_DIR`: Directory for temporary file storage

### CORS Configuration
- `CORS_ORIGINS`: Comma-separated list of allowed origins

### Audio Processing
- `DEMUCS_MODEL`: Demucs model to use (default: `htdemucs_ft`)
- `MP3_BITRATE`: MP3 output bitrate (default: `320`)
- `MAX_CONTENT_LENGTH`: Maximum upload size in bytes

### Redis/Celery
- `CELERY_BROKER_URL`: Celery broker URL
- `CELERY_RESULT_BACKEND`: Celery result backend URL
- `REDIS_URL`: Redis connection URL (fallback)

## Usage

```python
from app.config import get_config

# Get environment-appropriate configuration
config = get_config()

# Access configuration values
print(config.DATABASE_URL)
print(config.CORS_ORIGINS)
print(config.DEBUG)
```

## Environment-Specific Behavior

### Development
- DEBUG mode enabled
- Relaxed CORS policy (localhost origins)
- Default SECRET_KEY provided
- No strict validation

### Production
- DEBUG mode disabled
- Strict CORS policy (must set CORS_ORIGINS)
- SECRET_KEY environment variable required
- Full validation of required settings

### Testing
- In-memory SQLite database
- All CORS origins allowed
- Minimal validation
- Directories not created automatically

## Migration Notes

The old `config.py` file has been replaced with a backwards-compatible version that redirects to the new configuration system. All existing imports should continue to work during the transition period.
