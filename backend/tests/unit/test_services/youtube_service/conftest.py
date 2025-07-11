"""
Shared fixtures for YouTube Service tests

This file contains common fixtures used across multiple test modules.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock

import pytest
from app.services.interfaces.file_service import FileServiceInterface
from app.services.youtube_service import YouTubeService

# SongMetadata removed in Phase 5 - using dictionaries instead


@pytest.fixture
def mock_file_service():
    """Mock FileServiceInterface for testing"""
    mock = Mock(spec=FileServiceInterface)
    mock.get_song_directory.return_value = Path("/test/song/dir")
    mock.get_original_path.return_value = Path("/test/song/dir/original.mp3")
    return mock


@pytest.fixture
def youtube_service(mock_file_service):
    """YouTubeService instance with mocked dependencies"""
    return YouTubeService(file_service=mock_file_service)


@pytest.fixture
def youtube_service_no_deps():
    """YouTubeService instance without dependencies (for core tests)"""
    mock_file_service = Mock(spec=FileServiceInterface)
    mock_file_service.get_song_directory.return_value = Path("/test/song/dir")
    mock_file_service.get_original_path.return_value = Path(
        "/test/song/dir/original.mp3"
    )
    return YouTubeService(file_service=mock_file_service)


@pytest.fixture
def complete_youtube_info() -> Dict[str, Any]:
    """Complete yt-dlp video info with all fields"""
    return {
        "id": "dQw4w9WgXcQ",
        "title": "Rick Astley - Never Gonna Give You Up (Official Video)",
        "uploader": "Rick Astley",
        "uploader_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
        "channel": "Rick Astley",
        "channel_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
        "duration": 213,
        "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "description": "The official video for Rick Astley's 'Never Gonna Give You Up' released in 1987.",
        "upload_date": "20091025",
        "view_count": 1234567890,
        "like_count": 12345678,
        "thumbnails": [
            {
                "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
                "preference": 10,
                "width": 1280,
                "height": 720,
            }
        ],
        "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    }


@pytest.fixture
def partial_youtube_info() -> Dict[str, Any]:
    """Partial yt-dlp video info with missing fields"""
    return {
        "id": "abc123def45",
        "title": "Sample Video",
        # Missing uploader, channel, duration, etc.
        "webpage_url": "https://www.youtube.com/watch?v=abc123def45",
    }


@pytest.fixture
def sample_search_response():
    """Sample YouTube search response"""
    return {
        "entries": [
            {
                "id": "dQw4w9WgXcQ",
                "title": "Rick Astley - Never Gonna Give You Up",
                "channel": "Rick Astley",
                "channel_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
                "uploader": "Rick Astley",
                "uploader_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
                "duration": 213,
                "thumbnails": [
                    {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"}
                ],
            },
            {
                "id": "y6120QOlsfU",
                "title": "Darude - Sandstorm",
                "channel": "Darude",
                "channel_id": "UCQJEdu6MAbRpISOPa3rBGdQ",
                "uploader": "Darude",
                "uploader_id": "UCQJEdu6MAbRpISOPa3rBGdQ",
                "duration": 234,
                "thumbnails": [
                    {"url": "https://i.ytimg.com/vi/y6120QOlsfU/maxresdefault.jpg"}
                ],
            },
        ]
    }


@pytest.fixture
def sample_thumbnails() -> List[Dict[str, Any]]:
    """Sample thumbnail data with different qualities and formats"""
    return [
        {
            "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg",
            "preference": 1,
            "width": 120,
            "height": 90,
        },
        {
            "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            "preference": 5,
            "width": 480,
            "height": 360,
        },
        {
            "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
            "preference": 10,
            "width": 1280,
            "height": 720,
        },
    ]


@pytest.fixture
def sample_webp_thumbnails() -> List[Dict[str, Any]]:
    """Sample WebP thumbnail data reflecting real YouTube API response"""
    return [
        {
            "url": "https://i.ytimg.com/vi_webp/dQw4w9WgXcQ/maxresdefault.webp",
            "preference": 0,  # Highest preference (WebP)
            "width": 1920,
            "height": 1080,
        },
        {
            "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
            "preference": -1,  # Lower preference (JPEG)
            "width": 1280,
            "height": 720,
        },
        {
            "url": "https://i.ytimg.com/vi_webp/dQw4w9WgXcQ/hq720.webp",
            "preference": -2,  # Lower preference WebP
            "width": 1280,
            "height": 720,
        },
    ]


@pytest.fixture
def mixed_format_thumbnails() -> List[Dict[str, Any]]:
    """Mixed format thumbnails to test format detection"""
    return [
        {
            "url": "https://i.ytimg.com/vi_webp/dQw4w9WgXcQ/maxresdefault.webp",
            "preference": 0,  # WebP highest preference
            "width": 1920,
            "height": 1080,
        },
        {
            "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
            "preference": -1,  # JPEG lower preference
            "width": 1280,
            "height": 720,
        },
        {
            "url": "https://example.com/thumbnail.png",
            "preference": -3,  # PNG lowest preference
            "width": 640,
            "height": 480,
        },
    ]


@pytest.fixture
def sample_metadata():
    """Sample metadata dictionary for testing (SongMetadata class was removed)"""
    return {
        "title": "Test Song",
        "artist": "Test Artist",
        "source": "youtube",
        "videoId": "test123",
        "duration": 213,
    }


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for async testing"""
    mock_job = Mock()
    mock_job.delay.return_value.id = "job-123-456"
    return mock_job


@pytest.fixture
def mock_job_store():
    """Mock job store for task management testing"""
    return Mock()
