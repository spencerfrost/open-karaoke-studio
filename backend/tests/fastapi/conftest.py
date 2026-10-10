"""
Pytest fixtures for FastAPI tests.

Endpoints run against the shared throwaway database set up in tests/conftest.py,
so tests can seed and inspect data with app.db.database.SessionLocal directly.
Only authentication is overridden here.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from tests.conftest import create_test_app

from app.api.dependencies import (
    RequesterContext,
    get_current_user,
    require_host_or_session_member,
)
from app.db.database import SessionLocal


def _get_mock_user():
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "testuser"
    mock_user.is_admin = True
    mock_user.is_host = True
    # Explicit: a MagicMock attribute would otherwise be truthy and trip
    # demo-quota logic on every test that resolves the requester.
    mock_user.is_demo = False
    # Likewise explicit: this reaches the DB as a device's display_name, and SQLite cannot
    # bind a MagicMock.
    mock_user.display_name = "testuser"
    return mock_user


def _get_mock_requester():
    return RequesterContext(user=_get_mock_user())


@pytest.fixture(scope="module")
def fastapi_app():
    """Create FastAPI application for testing with auth bypassed."""
    app = create_test_app()
    app.dependency_overrides[get_current_user] = _get_mock_user
    app.dependency_overrides[require_host_or_session_member] = _get_mock_requester
    return app


@pytest.fixture(scope="module")
def client(fastapi_app):
    """FastAPI test client."""
    with TestClient(fastapi_app) as client:
        yield client


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
                "duration": 214.0,
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
            "albums": [],
        }
        service_instance.get_album_tracks.return_value = {
            "title": "A Night At The Opera",
            "artist": "Queen",
            "tracks": [],
        }

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
                "syncedLyrics": "[00:00.06] Is this the real life?...",
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
def user_db():
    """Provide a test DB session for direct user creation in tests."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
