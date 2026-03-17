"""
Pytest configuration and shared fixtures for Open Karaoke Studio backend tests.

This conftest provides FastAPI test fixtures after the Flask to FastAPI migration.
"""

import random
import sys
import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add the backend path for imports
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


from app.db.models import Base, DbSong
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.fixtures.test_data import create_test_db_song, create_test_song


@pytest.fixture(scope="function")
def test_db_session():
    """
    Provide a transactional scope for database tests.

    This fixture creates an in-memory SQLite database, begins a transaction,
    and rolls it back after each test. This ensures that every test starts
    with a clean database and any changes are discarded, preventing test pollution.
    """
    # Create an in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    # Begin a transaction
    connection = engine.connect()
    transaction = connection.begin()
    session.begin_nested()

    yield session

    # Rollback the transaction and close the connection
    transaction.rollback()
    connection.close()
    session.close()


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
            duration=180.0 + i,  # Duration in seconds
            date_added=None,
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
    # No yield or cleanup needed here, as the transaction will be rolled back.


def create_test_app():
    """
    Create a minimal FastAPI app for testing that includes all routers.
    This is a factory function to allow fresh app instances for tests.
    """
    from app.api import (
        health_router,
        jobs_router,
        lyrics_router,
        metadata_router,
        performance_history_router,
        queue_router,
        sessions_router,
        songs_router,
        users_router,
        youtube_music_router,
        youtube_router,
    )
    from fastapi import WebSocket
    from fastapi.middleware.cors import CORSMiddleware

    from app.ws import (
        SessionConnectionManager,
        websocket_jobs_endpoint,
        websocket_unified_session_endpoint,
    )

    test_app = FastAPI(
        title="Open Karaoke Studio API (Test)",
        version="2.0.0-test",
    )
    manager = SessionConnectionManager()
    test_app.state.session_manager = manager

    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include all API routers
    test_app.include_router(health_router)
    test_app.include_router(songs_router)
    test_app.include_router(jobs_router)
    test_app.include_router(sessions_router)
    test_app.include_router(queue_router)
    test_app.include_router(youtube_router)
    test_app.include_router(youtube_music_router)
    test_app.include_router(metadata_router)
    test_app.include_router(lyrics_router)
    test_app.include_router(users_router)
    test_app.include_router(performance_history_router)

    # WebSocket routes
    @test_app.websocket("/ws/jobs")
    async def jobs_ws(websocket: WebSocket):
        await websocket_jobs_endpoint(websocket, manager)

    @test_app.websocket("/ws/session/{session_id}")
    async def unified_session_ws(
        websocket: WebSocket,
        session_id: str,
        device_id: Optional[str] = None,
    ):
        await websocket_unified_session_endpoint(websocket, session_id, manager, device_id)

    # Root endpoint for testing
    @test_app.get("/")
    async def root():
        return {
            "message": "Open Karaoke Studio FastAPI Backend",
            "version": "2.0.0",
            "api_endpoints": {
                "songs": "/api/songs",
                "jobs": "/api/jobs",
                "sessions": "/api/sessions",
                "queue": "/api/karaoke-queue",
                "youtube": "/api/youtube",
                "youtube_music": "/api/youtube-music",
                "metadata": "/api/metadata",
                "lyrics": "/api/lyrics",
                "users": "/api/users",
            },
            "websockets": {
                "jobs": "/ws/jobs",
                "session": "/ws/session/{session_id}",
            },
        }

    return test_app


@pytest.fixture(scope="session")
def app():
    """Create FastAPI application for testing"""
    return create_test_app()


@pytest.fixture(scope="session")
def client(app):
    """
    Create FastAPI test client.

    FastAPI's TestClient wraps httpx and allows testing async endpoints synchronously.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def db_session():
    """
    Provide a transactional scope for database tests.

    This fixture creates an in-memory SQLite database, begins a transaction,
    and rolls it back after each test. This ensures that every test starts
    with a clean database and any changes are discarded, preventing test pollution.
    """
    # Create an in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    # Begin a transaction
    connection = engine.connect()
    transaction = connection.begin()
    session.begin_nested()

    yield session

    # Rollback the transaction and close the connection
    transaction.rollback()
    connection.close()
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
    service.separate_audio.return_value = {}
    return service


@pytest.fixture(scope="function", autouse=True)
def apply_test_config(monkeypatch):
    """
    Apply test configuration before any application modules are imported.
    """
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")


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
