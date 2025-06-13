"""
Pytest configuration and shared fixtures for Open Karaoke Studio backend tests.
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path so we can import from it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app import create_app
from app.config.testing import TestingConfig
from app.db.models import Base, DbSong, DbJob
from app.db.database import get_db_session
from tests.fixtures.test_data import create_test_db_song, create_test_song


@pytest.fixture(scope="session")
def app():
    """Create application for testing"""
    app = create_app(TestingConfig())  # Create instance instead of passing class
    
    with app.app_context():
        yield app


@pytest.fixture(scope="session")
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture(scope="function")
def db_session():
    """Create isolated database session for each test"""
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def temp_library_dir():
    """Create temporary directory for file operations"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_song_data():
    """Sample song data for testing"""
    return {
        "id": "test-song-123",
        "title": "Test Song",
        "artist": "Test Artist",
        "duration": 180,
        "source": "upload",
        "favorite": False
    }


@pytest.fixture
def sample_job_data():
    """Sample job data for testing"""
    return {
        "id": "test-job-123",
        "filename": "test_file.mp3",
        "status": "pending",
        "progress": 0
    }


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for testing"""
    class MockTask:
        def __init__(self):
            self.id = "test-job-123"
            self.state = "PENDING"
            self.result = None
        
        def delay(self, *args, **kwargs):
            return self
        
        def get(self, timeout=None):
            return self.result
        
        def ready(self):
            return self.state in ["SUCCESS", "FAILURE"]
        
        def successful(self):
            return self.state == "SUCCESS"
        
        def failed(self):
            return self.state == "FAILURE"
    
    return MockTask()


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    config = Mock()
    config.LIBRARY_DIR = Path("/tmp/test_library")
    config.UPLOADS_DIR = Path("/tmp/test_uploads")
    config.TEMP_DIR = Path("/tmp/test_temp")
    config.DATABASE_URL = "sqlite:///:memory:"
    return config


@pytest.fixture
def mock_file_service():
    """Mock file management service"""
    service = Mock()
    service.get_song_directory.return_value = Path("/tmp/test_song")
    service.ensure_song_directory.return_value = Path("/tmp/test_song")
    service.get_metadata.return_value = {
        "title": "Test Song",
        "artist": "Test Artist",
        "duration": 180
    }
    return service


@pytest.fixture
def mock_audio_service():
    """Mock audio processing service"""
    service = Mock()
    service.separate_audio.return_value = {
        "vocals_path": "/tmp/vocals.wav",
        "instrumental_path": "/tmp/instrumental.wav"
    }
    return service


@pytest.fixture(autouse=True)
def patch_config():
    """Automatically patch configuration for all tests"""
    with patch('app.config.get_config') as mock:
        config = Mock()
        config.LIBRARY_DIR = Path("/tmp/test_library")
        config.UPLOADS_DIR = Path("/tmp/test_uploads") 
        config.TEMP_DIR = Path("/tmp/test_temp")
        config.DATABASE_URL = "sqlite:///:memory:"
        mock.return_value = config
        yield config


@pytest.fixture
def db_song_factory():
    """Factory for creating test database songs"""
    def _create_db_song(**kwargs):
        return create_test_db_song(kwargs)
    return _create_db_song


@pytest.fixture
def song_factory():
    """Factory for creating test songs"""
    def _create_song(**kwargs):
        return create_test_song(kwargs)
    return _create_song
