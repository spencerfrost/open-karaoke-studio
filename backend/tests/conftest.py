"""
Pytest configuration and shared fixtures for Open Karaoke Studio backend tests.
"""

import random
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from app import create_app
from app.config.testing import TestingConfig
from app.db.models import Base, DbSong
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.fixtures.test_data import create_test_db_song, create_test_song


@pytest.fixture(scope="function")
def populate_test_songs(test_db_session):
    """
    Populate the test database with 25 representative songs for integration tests.
    Songs will have a mix of artists, albums, and special characters.
    """
    artists = ["Artist A", "Artist B", "Artist C", "Björk", "李荣浩"]
    albums = ["Hits 1", "Hits 2", "Classics", "Specials"]
    for i in range(25):
        song = DbSong(
            id=f"song-{i+1}",
            title=f"Test Song {i+1} {'★' if i % 5 == 0 else ''}",
            artist=random.choice(artists),
            album=random.choice(albums),
            duration_ms=180000 + i * 1000,
            i % 7 == 0),
            date_added=None,
            vocals_path=f"/tmp/test_songs/vocals_{i+1}.wav",
            instrumental_path=f"/tmp/test_songs/instrumental_{i+1}.wav",
            original_path=f"/tmp/test_songs/original_{i+1}.wav",
            thumbnail_path=f"/tmp/test_songs/thumb_{i+1}.jpg",
            cover_art_path=f"/tmp/test_songs/cover_{i+1}.jpg",
            source="test",
            source_url=f"http://example.com/song/{i+1}",
            video_id=f"vid{i+1}",
            uploader="TestUploader",
            uploader_id="uploader123",
            channel="TestChannel",
            channel_id="channel123",
            description=f"Description for song {i+1}",
            upload_date=None,
            mbid=None,
            release_id=None,
            release_date=None,
            year=2020 + (i % 5),
            genre=random.choice(["Pop", "Rock", "Jazz", "Classical"]),
            language=random.choice(["English", "Spanish", "Chinese"]),
            lyrics="La la la...",
            synced_lyrics=None,
        )
        test_db_session.add(song)
    test_db_session.commit()
    yield
    test_db_session.query(DbSong).delete()
    test_db_session.commit()


@pytest.fixture(scope="session")
def app():
    """Create application for testing"""
    flask_app = create_app(TestingConfig())  # Create instance instead of passing class

    with flask_app.app_context():
        yield flask_app


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

    session_local = sessionmaker(bind=engine)
    session = session_local()

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
    }


@pytest.fixture
def sample_job_data():
    """Sample job data for testing"""
    return {
        "id": "test-job-123",
        "filename": "test_file.mp3",
        "status": "pending",
        "progress": 0,
    }


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for testing"""

    class MockTask:
        def __init__(self):
            self.id = "test-job-123"
            self.state = "PENDING"
            self.result = None

        def delay(self):
            return self

        def get(self):
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
        "duration": 180,
    }
    return service


@pytest.fixture
def mock_audio_service():
    """Mock audio processing service"""
    service = Mock()
    service.separate_audio.return_value = {
        "vocals_path": "/tmp/vocals.wav",
        "instrumental_path": "/tmp/instrumental.wav",
    }
    return service


@pytest.fixture(autouse=True)
def patch_config():
    """Automatically patch configuration for all tests"""
    with patch("app.config.get_config") as mock:
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
