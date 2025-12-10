"""
Pytest fixtures for FastAPI tests.

FastAPI testing uses httpx TestClient instead of Flask's test_client.
The TestClient allows synchronous testing of async endpoints.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add the backend path for imports
backend_path = str(Path(__file__).parent.parent.parent)

if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from fastapi import FastAPI
from fastapi.testclient import TestClient





@pytest.fixture(scope="module")
def fastapi_app():
    """Create FastAPI application for testing."""
    return create_test_app()


@pytest.fixture(scope="module")
def client(fastapi_app):
    """
    Create FastAPI test client.
    
    Unlike Flask's test_client, FastAPI's TestClient wraps httpx
    and allows testing async endpoints synchronously.
    """
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
        service_instance.search_songs.return_value = [
            {
                "videoId": "utwMHfDZ6SA",
                "title": "Bohemian Rhapsody",
                "artist": "Queen",
                "artistId": "UCEPMVbUzImPl4p8k4LkGevA",
                "duration": "5:55",
                "album": "A Night At The Opera",
                "thumbnails": []
            }
        ]
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
                "genre": "Rock"
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
