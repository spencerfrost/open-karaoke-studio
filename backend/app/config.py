"""
Configuration settings for the Open Karaoke Studio backend.
"""
import os
from pathlib import Path


class Config:
    """Base configuration class for the application."""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(BASE_DIR, "..", "karaoke.db")}'
    
    # File management
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    BASE_LIBRARY_DIR = PROJECT_ROOT / "karaoke_library"  # Root directory for processed songs
    
    # Audio processing
    DEFAULT_MODEL = "htdemucs_ft"  # Default Demucs model 
    DEFAULT_MP3_BITRATE = "320"  # Default bitrate if saving as MP3
    
    # File upload configuration
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200 MB max upload size
    ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
    
    # Celery configuration
    CELERY_BROKER_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # API configuration
    CORS_ORIGINS = ['http://localhost:5173']  # Frontend development server


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # In production, SECRET_KEY should be set as an environment variable
    
    
class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    # Use in-memory database for testing
    

# Map environment names to config classes
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': Config
}

# Get the appropriate config based on environment or use default
def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    return config_by_name.get(env, config_by_name['default'])