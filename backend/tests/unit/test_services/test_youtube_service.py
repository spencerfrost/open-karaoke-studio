"""
Unit tests for the YouTube service.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from pathlib import Path

from app.services.youtube_service import (
    search_youtube,
    download_from_youtube
)


class TestYouTubeService:
    """Test suite for YouTube service functions."""

    @pytest.fixture
    def sample_youtube_search_result(self):
        """Sample YouTube search result for testing."""
        return [
            {
                'id': 'video123',
                'title': 'Test Song - Test Artist',
                'duration': 180,
                'view_count': 1000000,
                'upload_date': '20230101'
            }
        ]

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_youtube_success(self, mock_ytdl, sample_youtube_search_result, app):
        """Test successful YouTube search."""
        # Arrange
        mock_ytdl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ytdl_instance
        mock_ytdl_instance.extract_info.return_value = {
            'entries': sample_youtube_search_result
        }
        
        # Act
        with app.app_context():
            result = search_youtube("Test Artist Test Song")
        
        # Assert
        assert len(result) == 1
        assert result[0]['title'] == 'Test Song - Test Artist'

    @pytest.fixture
    def sample_search_results(self):
        """Sample YouTube search results for testing."""
        return {
            "items": [
                {
                    "id": {"videoId": "test-video-123"},
                    "snippet": {
                        "title": "Test Song - Test Artist",
                        "description": "Official video for Test Song",
                        "channelTitle": "Test Artist Official",
                        "thumbnails": {
                            "high": {"url": "https://example.com/thumb.jpg"}
                        },
                        "publishedAt": "2023-01-01T00:00:00Z"
                    }
                }
            ]
        }

    @pytest.fixture
    def sample_video_info(self):
        """Sample YouTube video info for testing."""
        return {
            "id": "test-video-123",
            "title": "Test Song - Test Artist",
            "uploader": "Test Artist Official",
            "duration": 180,
            "view_count": 1000000,
            "upload_date": "20230101",
            "formats": [
                {
                    "format_id": "140",
                    "ext": "m4a",
                    "acodec": "mp4a.40.2",
                    "abr": 128,
                    "filesize": 2000000
                }
            ]
        }

    def test_search_videos_success(self, youtube_service, sample_search_results):
        """Test successful video search."""
        # Arrange
        query = "Test Song Test Artist"
        
        with patch('app.services.youtube_service.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_search_results
            mock_get.return_value = mock_response
            
            # Act
            result = youtube_service.search_videos(query)
            
            # Assert
            assert result is not None
            assert len(result) == 1
            assert result[0]["video_id"] == "test-video-123"
            assert result[0]["title"] == "Test Song - Test Artist"

    def test_search_videos_no_results(self, youtube_service):
        """Test video search with no results."""
        # Arrange
        query = "nonexistent song"
        
        with patch('app.services.youtube_service.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"items": []}
            mock_get.return_value = mock_response
            
            # Act
            result = youtube_service.search_videos(query)
            
            # Assert
            assert result == []

    def test_search_videos_api_error(self, youtube_service):
        """Test video search when API returns error."""
        # Arrange
        query = "Test Song"
        
        with patch('app.services.youtube_service.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 403  # Quota exceeded
            mock_response.raise_for_status.side_effect = Exception("API Error")
            mock_get.return_value = mock_response
            
            # Act & Assert
            with pytest.raises(Exception, match="API Error"):
                youtube_service.search_videos(query)

    def test_get_video_info_success(self, youtube_service, sample_video_info):
        """Test successful video info retrieval."""
        # Arrange
        video_id = "test-video-123"
        
        with patch('app.services.youtube_service.yt_dlp.YoutubeDL') as mock_ytdl:
            mock_instance = Mock()
            mock_instance.extract_info.return_value = sample_video_info
            mock_ytdl.return_value.__enter__.return_value = mock_instance
            
            # Act
            result = youtube_service.get_video_info(video_id)
            
            # Assert
            assert result is not None
            assert result["id"] == video_id
            assert result["title"] == "Test Song - Test Artist"
            assert result["duration"] == 180

    def test_get_video_info_not_found(self, youtube_service):
        """Test video info retrieval when video doesn't exist."""
        # Arrange
        video_id = "nonexistent-video"
        
        with patch('app.services.youtube_service.yt_dlp.YoutubeDL') as mock_ytdl:
            mock_instance = Mock()
            mock_instance.extract_info.side_effect = Exception("Video not found")
            mock_ytdl.return_value.__enter__.return_value = mock_instance
            
            # Act & Assert
            with pytest.raises(Exception, match="Video not found"):
                youtube_service.get_video_info(video_id)

    def test_download_audio_success(self, youtube_service, temp_library_dir):
        """Test successful audio download."""
        # Arrange
        video_id = "test-video-123"
        output_path = temp_library_dir / "test_audio.m4a"
        
        with patch('app.services.youtube_service.yt_dlp.YoutubeDL') as mock_ytdl:
            mock_instance = Mock()
            mock_instance.download.return_value = None
            mock_ytdl.return_value.__enter__.return_value = mock_instance
            
            # Mock file creation
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.stat') as mock_stat:
                    mock_stat.return_value.st_size = 2000000  # 2MB file
                    
                    # Act
                    result = youtube_service.download_audio(video_id, str(output_path))
                    
                    # Assert
                    assert result is not None
                    assert result["success"] is True
                    assert result["file_path"] == str(output_path)

    def test_download_audio_failure(self, youtube_service, temp_library_dir):
        """Test audio download failure."""
        # Arrange
        video_id = "test-video-123"
        output_path = temp_library_dir / "test_audio.m4a"
        
        with patch('app.services.youtube_service.yt_dlp.YoutubeDL') as mock_ytdl:
            mock_instance = Mock()
            mock_instance.download.side_effect = Exception("Download failed")
            mock_ytdl.return_value.__enter__.return_value = mock_instance
            
            # Act & Assert
            with pytest.raises(Exception, match="Download failed"):
                youtube_service.download_audio(video_id, str(output_path))

    def test_validate_url_valid(self, youtube_service):
        """Test validation of valid YouTube URLs."""
        # Arrange
        valid_urls = [
            "https://www.youtube.com/watch?v=test123",
            "https://youtu.be/test123",
            "https://m.youtube.com/watch?v=test123",
            "https://youtube.com/watch?v=test123"
        ]
        
        # Act & Assert
        for url in valid_urls:
            assert youtube_service.validate_url(url) is True

    def test_validate_url_invalid(self, youtube_service):
        """Test validation of invalid URLs."""
        # Arrange
        invalid_urls = [
            "https://www.example.com/watch?v=test123",
            "not_a_url",
            "https://vimeo.com/123456",
            ""
        ]
        
        # Act & Assert
        for url in invalid_urls:
            assert youtube_service.validate_url(url) is False

    def test_extract_video_id_from_url(self, youtube_service):
        """Test extracting video ID from various YouTube URL formats."""
        # Arrange
        test_cases = [
            ("https://www.youtube.com/watch?v=test123", "test123"),
            ("https://youtu.be/test456", "test456"),
            ("https://www.youtube.com/watch?v=test789&t=30s", "test789"),
            ("https://m.youtube.com/watch?v=testABC", "testABC")
        ]
        
        # Act & Assert
        for url, expected_id in test_cases:
            result = youtube_service.extract_video_id(url)
            assert result == expected_id

    def test_extract_video_id_invalid_url(self, youtube_service):
        """Test extracting video ID from invalid URLs."""
        # Arrange
        invalid_urls = [
            "https://www.example.com/watch?v=test123",
            "not_a_url",
            "https://youtube.com/invalid"
        ]
        
        # Act & Assert
        for url in invalid_urls:
            result = youtube_service.extract_video_id(url)
            assert result is None

    def test_get_audio_quality_options(self, youtube_service, sample_video_info):
        """Test getting available audio quality options."""
        # Arrange
        video_id = "test-video-123"
        
        with patch('app.services.youtube_service.yt_dlp.YoutubeDL') as mock_ytdl:
            mock_instance = Mock()
            mock_instance.extract_info.return_value = sample_video_info
            mock_ytdl.return_value.__enter__.return_value = mock_instance
            
            # Act
            result = youtube_service.get_audio_quality_options(video_id)
            
            # Assert
            assert result is not None
            assert len(result) == 1
            assert result[0]["format_id"] == "140"
            assert result[0]["ext"] == "m4a"
            assert result[0]["abr"] == 128

    def test_format_search_query(self, youtube_service):
        """Test formatting search queries for YouTube."""
        # Arrange
        title = "Test Song"
        artist = "Test Artist"
        
        # Act
        result = youtube_service.format_search_query(title, artist)
        
        # Assert
        assert "Test Song" in result
        assert "Test Artist" in result
