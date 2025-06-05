"""
Base configuration class for Open Karaoke Studio backend.
"""

import os
from pathlib import Path
from typing import List


class BaseConfig:
    """Base configuration class containing common settings for all environments."""
    
    # Flask Core Settings
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        # For development, provide a default; for production, this will raise an error
        SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-please-change-in-production")
    
    # Directory Structure
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # Points to project root
    
    # Database Configuration
    DATABASE_URL = os.environ.get(
        "DATABASE_URL", 
        f"sqlite:///{BASE_DIR / 'karaoke.db'}"
    )
    SQLALCHEMY_DATABASE_URI = DATABASE_URL  # For SQLAlchemy compatibility
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File Management
    LIBRARY_DIR = Path(os.environ.get(
        "LIBRARY_DIR", 
        str(BASE_DIR / "karaoke_library")
    ))
    TEMP_DIR = Path(os.environ.get(
        "TEMP_DIR",
        str(BASE_DIR / "temp_downloads")
    ))
    
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
    def CORS_ORIGINS(self) -> List[str]:
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
    def DEFAULT_CORS_ORIGINS(self) -> List[str]:
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
        if os.getenv('FLASK_ENV') == 'production':
            if not os.environ.get("SECRET_KEY"):
                required_vars.append("SECRET_KEY")
        
        if required_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(required_vars)}")
    
    def __init__(self):
        """Initialize and validate configuration."""
        self.validate_config()
        
        # Ensure directories exist
        self.LIBRARY_DIR.mkdir(exist_ok=True)
        self.TEMP_DIR.mkdir(exist_ok=True)
