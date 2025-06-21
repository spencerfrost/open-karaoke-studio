"""
Base configuration class for Open Karaoke Studio backend.
"""

import os
from pathlib import Path


class BaseConfig:
    """Base configuration class containing common settings for all environments."""

    # Flask Core Settings
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        # For development, provide a default; for production, this will raise an error
        SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-please-change-in-production")

    # Directory Structure
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # Points to project root

    # Timezone Configuration
    TIMEZONE = os.environ.get("TIMEZONE", "America/Toronto")
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_DIR = Path(os.environ.get("LOG_DIR", str(BASE_DIR / "backend" / "logs")))
    LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", 10485760))
    LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 5))
    LOG_FORMAT = os.environ.get("LOG_FORMAT", "detailed")

    # Database Configuration
    # Always use the backend directory database to avoid working directory issues
    BACKEND_DB_PATH = BASE_DIR / "backend" / "karaoke.db"
    _env_database_url = os.environ.get("DATABASE_URL")

    if (
        _env_database_url
        and _env_database_url.startswith("sqlite:///")
        and not _env_database_url.startswith("sqlite:////")
    ):
        # If relative sqlite path, convert to absolute backend directory path
        relative_path = _env_database_url.replace("sqlite:///", "")
        if relative_path == "karaoke.db":
            # Use the backend directory database for consistency
            DATABASE_URL = f"sqlite:///{BACKEND_DB_PATH}"
        elif not Path(relative_path).is_absolute():
            DATABASE_URL = f"sqlite:///{BASE_DIR / 'backend' / relative_path}"
        else:
            DATABASE_URL = _env_database_url
    else:
        DATABASE_URL = _env_database_url or f"sqlite:///{BACKEND_DB_PATH}"
    SQLALCHEMY_DATABASE_URI = DATABASE_URL  # For SQLAlchemy compatibility
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File Management
    LIBRARY_DIR = Path(os.environ.get("LIBRARY_DIR", str(BASE_DIR / "karaoke_library")))
    TEMP_DIR = Path(os.environ.get("TEMP_DIR", str(BASE_DIR / "temp_downloads")))

    # Audio Processing Settings
    DEMUCS_MODEL = os.environ.get("DEMUCS_MODEL", "htdemucs_ft")
    MP3_BITRATE = os.environ.get("MP3_BITRATE", "320")
    DEFAULT_MODEL = DEMUCS_MODEL  # For backwards compatibility
    DEFAULT_MP3_BITRATE = MP3_BITRATE  # For backwards compatibility

    # Upload Configuration
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 200 * 1024 * 1024))  # 200MB
    ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}

    # Celery Configuration
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # Redis Configuration (fallback support)
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # Server Configuration
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", 5123))

    @property
    def CORS_ORIGINS(self) -> list[str]:
        """
        Get CORS origins from environment variable as a list.

        Returns:
            List of allowed CORS origins
        """
        origins = os.environ.get("CORS_ORIGINS", "")
        if not origins:
            return self.DEFAULT_CORS_ORIGINS
        return [origin.strip() for origin in origins.split(",") if origin.strip()]

    @property
    def DEFAULT_CORS_ORIGINS(self) -> list[str]:
        """Default CORS origins for this environment. Override in subclasses."""
        return ["*"]  # Will be overridden in specific environments

    # Flask-specific settings
    TESTING = False
    DEBUG = False

    # Backwards compatibility properties
    @property
    def BASE_LIBRARY_DIR(self):
        """Backwards compatibility for BASE_LIBRARY_DIR -> LIBRARY_DIR"""
        return self.LIBRARY_DIR

    @property
    def PROJECT_ROOT(self):
        """Backwards compatibility for PROJECT_ROOT -> BASE_DIR"""
        return self.BASE_DIR

    ORIGINAL_FILENAME_SUFFIX = "_original"  # Add missing constant

    @classmethod
    def validate_config(cls):
        """Validate that all required configuration is present."""
        required_vars = []

        # Check for production-critical environment variables
        if os.getenv("FLASK_ENV") == "production":
            if not os.environ.get("SECRET_KEY"):
                required_vars.append("SECRET_KEY")

        if required_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(required_vars)}")

    def __init__(self):
        """Initialize and validate configuration."""
        self.validate_config()

        # Ensure directories exist
        self.LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)  # Ensure log directory exists
