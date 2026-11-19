"""
Base configuration class for Open Karaoke Studio backend.
"""

import os
from pathlib import Path


class BaseConfig:
    """Base configuration class containing common settings for all environments."""

    # Application Settings
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        # For development, provide a default; for production, this will raise an error
        SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-please-change-in-production")

    # Directory Structure
    BASE_DIR = (
        Path(__file__).resolve().parent.parent.parent.parent
    )  # Points to project root

    # Timestamps in the log files
    TIMEZONE = "America/Toronto"

    # How much the console shows (tmux panes, `docker logs`). The log files
    # always keep INFO. Unset: INFO in development, WARNING in production.
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "").strip().upper() or None

    # Database Configuration
    # DATABASE_URL is required - no fallback to SQLite
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError(
            "DATABASE_URL environment variable is required. "
            "Please set it in your .env file, e.g.: "
            "DATABASE_URL=postgresql://karaoke_user:karaoke_pass@localhost/karaoke"
        )
    SQLALCHEMY_DATABASE_URI = DATABASE_URL  # For SQLAlchemy compatibility
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File Management
    LIBRARY_DIR = Path(os.environ.get("LIBRARY_DIR", str(BASE_DIR / "karaoke_library")))

    # Audio processing. Fixed, not per machine: dev and prod share one library,
    # and every song's stems should come from the same model and bitrate.
    DEMUCS_MODEL = "htdemucs_ft"
    MP3_BITRATE = "320"
    # Mixed precision on the Roformer passes (1.5-1.9x faster) and the three-track
    # Demucs pass (~15% faster); inaudible change
    SEPARATION_USE_AUTOCAST = True
    # torch.compile on the Roformer blocks: ~1/3 faster again, ~6 s warm-up once
    # per worker process; falls back to eager if the build can't compile
    SEPARATION_TORCH_COMPILE = True
    # De-noise pass on three-track backing vocals (one extra Roformer pass)
    THREE_TRACK_DENOISE = True

    # Third-party API Keys
    DISCOGS_TOKEN = os.environ.get("DISCOGS_TOKEN", "")
    ACOUSTID_API_KEY = os.environ.get("ACOUSTID_API_KEY", "")

    # Netscape-format cookie file for yt-dlp (age-restricted / login-gated
    # videos). Disabled when unset.
    # NOTE: app.services.youtube_service reads this from os.environ at call
    # time so tests can monkeypatch it; this attr exists for documentation
    # parity.
    YTDLP_COOKIES_FILE = os.environ.get("YTDLP_COOKIES_FILE", "")

    ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}

    # Celery Configuration
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    # Same Redis as the broker; CI overrides it with an in-memory backend
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)

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

    # Compatibility settings
    TESTING = False
    DEBUG = False

    # Backwards compatibility properties
    @property
    def BASE_LIBRARY_DIR(self):
        """Backwards compatibility for BASE_LIBRARY_DIR -> LIBRARY_DIR"""
        return self.LIBRARY_DIR

    @property
    def library_path(self):
        """Backwards compatibility alias for LIBRARY_DIR"""
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
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env == "production":
            if not os.environ.get("SECRET_KEY"):
                required_vars.append("SECRET_KEY")

        if required_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(required_vars)}"
            )

    def __init__(self):
        """Initialize and validate configuration."""
        self.validate_config()

        # Ensure directories exist
        self.LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
