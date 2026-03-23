"""
Pytest fixtures for FastAPI tests.

FastAPI testing uses httpx TestClient instead of Flask's test_client.
The TestClient allows synchronous testing of async endpoints.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add the backend path for imports
backend_path = str(Path(__file__).parent.parent.parent)

if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_db
from app.db.models import Base  # noqa: F401 — triggers all model imports
from tests.conftest import create_test_app


_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
# Import all models to ensure they're registered with Base.metadata
import app.db.models  # noqa: F401
Base.metadata.create_all(bind=_engine)
_TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _get_test_db():
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_mock_user():
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "testuser"
    mock_user.is_admin = True
    mock_user.is_host = True
    return mock_user


@pytest.fixture(scope="module")
def fastapi_app():
    """Create FastAPI application for testing with isolated DB."""
    app = create_test_app()
    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[get_current_user] = _get_mock_user
    return app


@pytest.fixture(scope="module")
def client(fastapi_app):
    """
    Create FastAPI test client.
    
    Unlike Flask's test_client, FastAPI's TestClient wraps httpx
    and allows testing async endpoints synchronously.
    """
    with TestClient(fastapi_app) as client:
        yield client


@pytest.fixture(autouse=True)
def _clean_tables():
    """Truncate all tables between tests."""
    yield
    with _engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


@pytest.fixture
def mock_youtube_service():
    """Mock YouTube service for testing."""
    with patch("app.api.youtube.YouTubeService") as mock:
        service_instance = Mock()
        mock.return_value = service_instance
        
        # Default mock responses
        service_instance.search_videos.return_value = [
            {
                "id": "dQw4w9WgXcQ",
                "title": "Rick Astley - Never Gonna Give You Up",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "channel": "Rick Astley",
                "channelId": "UCuAXFkgsw1L7xaCfnd5JJOw",
                "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                "duration": 214.0
            }
        ]
        service_instance.download_and_process_async.return_value = "job-123"
        
        yield service_instance


@pytest.fixture
def mock_youtube_music_service():
    """Mock YouTube Music service for testing."""
    with patch("app.api.youtube_music.YoutubeMusicService") as mock:
        service_instance = Mock()
        mock.return_value = service_instance

        # Default mock responses
        service_instance.search_combined.return_value = {
            "songs": [
                {
                    "videoId": "utwMHfDZ6SA",
                    "title": "Bohemian Rhapsody",
                    "artist": "Queen",
                    "artistId": "UCEPMVbUzImPl4p8k4LkGevA",
                    "duration": "5:55",
                    "album": "A Night At The Opera",
                    "thumbnails": [],
                }
            ],
            "artists": [],
        }
        service_instance.get_artist.return_value = {
            "name": "Queen",
            "description": "British rock band",
            "topSongs": [],
            "albums": []
        }
        service_instance.get_album_tracks.return_value = {
            "title": "A Night At The Opera",
            "artist": "Queen",
            "tracks": []
        }
        
        yield service_instance


@pytest.fixture
def mock_metadata_service():
    """Mock metadata service for testing."""
    with patch("app.api.metadata.MetadataService") as mock:
        service_instance = Mock()
        mock.return_value = service_instance
        
        # Default mock response
        service_instance.search_metadata.return_value = [
            {
                "id": 1440806768,
                "title": "Bohemian Rhapsody",
                "artist": "Queen",
                "album": "A Night at the Opera",
                "releaseDate": "1975-11-21T08:00:00Z",
                "primaryGenre": "Rock"
            }
        ]
        
        yield service_instance


@pytest.fixture
def mock_lyrics_service():
    """Mock lyrics service for testing."""
    with patch("app.api.lyrics.LyricsService") as mock:
        service_instance = Mock()
        mock.return_value = service_instance
        
        # Default mock response
        service_instance.search_lyrics.return_value = [
            {
                "id": 139210,
                "trackName": "Bohemian Rhapsody",
                "artistName": "Queen",
                "albumName": "A Night At The Opera",
                "duration": 354.0,
                "instrumental": False,
                "plainLyrics": "Is this the real life?...",
                "syncedLyrics": "[00:00.06] Is this the real life?..."
            }
        ]
        
        yield service_instance


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    with patch("app.api.youtube_music.get_db_session") as mock:
        session = Mock()
        mock.return_value.__enter__ = Mock(return_value=session)
        mock.return_value.__exit__ = Mock(return_value=False)
        
        # Mock query results
        session.query.return_value.filter.return_value.all.return_value = []
        session.query.return_value.filter.return_value.first.return_value = None
        
        yield session


@pytest.fixture
def mock_user_db():
    """Mock user database operations for testing."""
    with patch("app.api.users.SessionLocal") as mock:
        session = Mock()
        mock.return_value = session
        
        # Default: no existing user
        session.query.return_value.filter.return_value.first.return_value = None
        
        yield session
