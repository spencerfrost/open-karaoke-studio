"""
Unit tests for the YouTube service - Phase 1 (Core Functionality)
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any
from pathlib import Path

from app.services.youtube_service import YouTubeService
from app.services.interfaces.youtube_service import YouTubeServiceInterface
from app.services.interfaces.file_service import FileServiceInterface
from app.services.interfaces.song_service import SongServiceInterface
from app.exceptions import ServiceError, ValidationError
from app.db.models import SongMetadata


class TestYouTubeServiceConstruction:
    """Test service initialization and dependency injection"""

    def test_constructor_with_injected_dependencies(self):
        """Test YouTubeService constructor with injected dependencies"""
        # Arrange
        mock_file_service = Mock(spec=FileServiceInterface)
        mock_song_service = Mock(spec=SongServiceInterface)
        
        # Act
        service = YouTubeService(
            file_service=mock_file_service,
            song_service=mock_song_service
        )
        
        # Assert
        assert service.file_service is mock_file_service
        assert service.song_service is mock_song_service

    def test_constructor_with_default_dependencies(self):
        """Test YouTubeService constructor with default dependencies"""
        # Act
        service = YouTubeService()
        
        # Assert
        assert service.file_service is not None
        assert hasattr(service.file_service, 'get_song_directory')  # FileService method
        assert service.song_service is None  # Injected to avoid circular dependency

    def test_interface_compliance(self):
        """Verify interface compliance with YouTubeServiceInterface"""
        # Arrange
        mock_file_service = Mock(spec=FileServiceInterface)
        service = YouTubeService(file_service=mock_file_service)
        
        # Assert - Check all interface methods exist
        assert hasattr(service, 'search_videos')
        assert hasattr(service, 'download_video')
        assert hasattr(service, 'extract_video_info')
        assert hasattr(service, 'validate_video_url')
        assert hasattr(service, 'get_video_id_from_url')
        assert hasattr(service, 'download_and_process_async')
        
        # Verify it's a proper protocol implementation
        assert isinstance(service, YouTubeServiceInterface)

    def test_dependency_injection_patterns(self):
        """Test proper dependency injection patterns"""
        # Arrange
        mock_file_service = Mock(spec=FileServiceInterface)
        mock_song_service = Mock(spec=SongServiceInterface)
        
        # Act
        service = YouTubeService(
            file_service=mock_file_service,
            song_service=mock_song_service
        )
        
        # Assert - Dependencies are properly injected and not recreated
        assert service.file_service is mock_file_service
        assert service.song_service is mock_song_service

    def test_service_initialization_edge_cases(self):
        """Validate service initialization edge cases"""
        # Test with None values explicitly
        service = YouTubeService(file_service=None, song_service=None)
        
        # Should create default file service when None
        assert service.file_service is not None
        assert service.song_service is None


class TestUrlValidation:
    """Test URL processing and validation logic"""

    @pytest.fixture
    def youtube_service(self):
        """YouTubeService instance for URL testing"""
        mock_file_service = Mock(spec=FileServiceInterface)
        return YouTubeService(file_service=mock_file_service)

    def test_validate_video_url_valid_standard_format(self, youtube_service):
        """Test validate_video_url() with standard YouTube URL format"""
        # Arrange
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
        ]
        
        # Act & Assert
        for url in valid_urls:
            assert youtube_service.validate_video_url(url) is True

    def test_validate_video_url_valid_short_format(self, youtube_service):
        """Test validate_video_url() with short YouTube URL format"""
        # Arrange
        valid_urls = [
            "https://youtu.be/dQw4w9WgXcQ",
            "http://youtu.be/dQw4w9WgXcQ",
        ]
        
        # Act & Assert
        for url in valid_urls:
            assert youtube_service.validate_video_url(url) is True

    def test_validate_video_url_valid_mobile_format(self, youtube_service):
        """Test validate_video_url() with mobile YouTube URL format"""
        # Arrange
        valid_urls = [
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://m.youtube.com/watch?v=dQw4w9WgXcQ",
        ]
        
        # Act & Assert
        for url in valid_urls:
            assert youtube_service.validate_video_url(url) is True

    def test_validate_video_url_valid_embedded_format(self, youtube_service):
        """Test validate_video_url() with embedded YouTube URL format"""
        # Arrange
        valid_urls = [
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "http://www.youtube.com/embed/dQw4w9WgXcQ",
        ]
        
        # Act & Assert
        for url in valid_urls:
            assert youtube_service.validate_video_url(url) is True

    def test_validate_video_url_valid_with_parameters(self, youtube_service):
        """Test validate_video_url() with URLs containing parameters"""
        # Arrange
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLx0sYbCqOb8TBPRdmBHs5Iftvv9TPboYG",
            "https://youtu.be/dQw4w9WgXcQ?t=30",
        ]
        
        # Act & Assert
        for url in valid_urls:
            assert youtube_service.validate_video_url(url) is True

    def test_validate_video_url_invalid_non_youtube_domains(self, youtube_service):
        """Test validate_video_url() with non-YouTube domains"""
        # Arrange
        invalid_urls = [
            "https://www.vimeo.com/123456789",
            "https://www.facebook.com/watch?v=123",
            "https://www.dailymotion.com/video/x123456",
            "https://www.example.com/watch?v=dQw4w9WgXcQ",
        ]
        
        # Act & Assert
        for url in invalid_urls:
            assert youtube_service.validate_video_url(url) is False

    def test_validate_video_url_invalid_malformed_urls(self, youtube_service):
        """Test validate_video_url() with malformed URLs"""
        # Arrange
        invalid_urls = [
            "not_a_url",
            "http://",
            "https://youtube.com",  # No video ID
            "https://www.youtube.com/watch",  # No video ID
            "https://youtu.be/",  # No video ID
        ]
        
        # Act & Assert
        for url in invalid_urls:
            assert youtube_service.validate_video_url(url) is False

    def test_validate_video_url_invalid_empty_and_non_string(self, youtube_service):
        """Test validate_video_url() with empty strings and non-string inputs"""
        # Arrange
        invalid_inputs = [
            "",
            None,
            123,
            [],
            {},
        ]
        
        # Act & Assert
        for invalid_input in invalid_inputs:
            # Should handle gracefully and return False
            try:
                result = youtube_service.validate_video_url(invalid_input)
                assert result is False
            except (TypeError, AttributeError):
                # Acceptable to raise type errors for non-string inputs
                pass

    def test_get_video_id_from_url_extraction_accuracy(self, youtube_service):
        """Test get_video_id_from_url() extraction accuracy"""
        # Arrange
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s", "dQw4w9WgXcQ"),
            ("http://youtube.com/watch?v=abc123def45", "abc123def45"),
        ]
        
        # Act & Assert
        for url, expected_id in test_cases:
            result = youtube_service.get_video_id_from_url(url)
            assert result == expected_id

    def test_get_video_id_from_url_invalid_inputs(self, youtube_service):
        """Test get_video_id_from_url() with invalid inputs"""
        # Arrange
        invalid_inputs = [
            "https://www.vimeo.com/123456789",
            "not_a_url",
            "https://youtube.com",
            "",
            None,
        ]
        
        # Act & Assert
        for invalid_input in invalid_inputs:
            result = youtube_service.get_video_id_from_url(invalid_input)
            assert result is None


class TestSearchVideos:
    """Test YouTube search functionality"""

    @pytest.fixture
    def mock_file_service(self):
        """Mock FileServiceInterface for testing"""
        return Mock(spec=FileServiceInterface)

    @pytest.fixture
    def mock_song_service(self):
        """Mock SongServiceInterface for testing"""
        return Mock(spec=SongServiceInterface)

    @pytest.fixture
    def youtube_service(self, mock_file_service, mock_song_service):
        """YouTubeService instance with mocked dependencies"""
        return YouTubeService(
            file_service=mock_file_service,
            song_service=mock_song_service
        )

    @pytest.fixture
    def sample_youtube_info(self):
        """Sample yt-dlp video info response"""
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
                    ]
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
                    ]
                }
            ]
        }

    @pytest.fixture
    def sample_search_response(self):
        """Sample yt-dlp search results"""
        return {
            "entries": [
                {
                    "id": "testVideo1",
                    "title": "Test Song - Test Artist",
                    "channel": "Test Artist",
                    "duration": 180,
                },
                {
                    "id": "testVideo2", 
                    "title": "Another Song - Test Artist",
                    "channel": "Test Artist",
                    "duration": 200,
                }
            ]
        }

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_valid_queries_standard_terms(self, mock_ytdl, youtube_service, sample_youtube_info):
        """Test search_videos() with valid standard search terms"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_youtube_info
        
        # Act
        result = youtube_service.search_videos("Rick Astley Never Gonna Give You Up")
        
        # Assert
        assert len(result) == 2
        assert result[0]["id"] == "dQw4w9WgXcQ"
        assert result[0]["title"] == "Rick Astley - Never Gonna Give You Up"
        assert result[0]["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert result[0]["channel"] == "Rick Astley"
        assert result[0]["duration"] == 213

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_special_characters(self, mock_ytdl, youtube_service, sample_search_response):
        """Test search_videos() with special characters in queries"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_search_response
        
        # Act
        result = youtube_service.search_videos("Artist - Song (Official Video) [HD]")
        
        # Assert
        assert len(result) == 2
        mock_ydl_instance.extract_info.assert_called_once()

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_unicode_characters(self, mock_ytdl, youtube_service, sample_search_response):
        """Test search_videos() with Unicode character support"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_search_response
        
        # Act
        result = youtube_service.search_videos("Björk Jóga 日本")
        
        # Assert
        assert len(result) == 2
        mock_ydl_instance.extract_info.assert_called_once()

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_empty_query_handling(self, mock_ytdl, youtube_service):
        """Test search_videos() with empty query handling"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = {"entries": []}
        
        # Act
        result = youtube_service.search_videos("")
        
        # Assert
        assert result == []

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_max_results_default(self, mock_ytdl, youtube_service, sample_youtube_info):
        """Test search_videos() with default max_results value (10)"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_youtube_info
        
        # Act
        result = youtube_service.search_videos("test query")
        
        # Assert
        search_call = mock_ydl_instance.extract_info.call_args[0][0]
        assert "ytsearch10:" in search_call

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_max_results_custom_values(self, mock_ytdl, youtube_service, sample_search_response):
        """Test search_videos() with different max_results values"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_search_response
        
        test_cases = [1, 5, 20]
        
        for max_results in test_cases:
            # Act
            youtube_service.search_videos("test query", max_results=max_results)
            
            # Assert
            search_call = mock_ydl_instance.extract_info.call_args[0][0]
            assert f"ytsearch{max_results}:" in search_call

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_zero_results(self, mock_ytdl, youtube_service):
        """Test search_videos() with zero results"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = {"entries": []}
        
        # Act
        result = youtube_service.search_videos("nonexistent query")
        
        # Assert
        assert result == []

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_boundary_values(self, mock_ytdl, youtube_service, sample_search_response):
        """Test search_videos() with boundary values for max_results"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_search_response
        
        # Test edge cases
        boundary_cases = [0, 1, 50]
        
        for max_results in boundary_cases:
            # Act
            result = youtube_service.search_videos("test", max_results=max_results)
            
            # Assert
            assert isinstance(result, list)

    def test_search_videos_response_format_validation(self, youtube_service, sample_youtube_info):
        """Test search_videos() response format validation"""
        # Arrange & Act
        with patch('app.services.youtube_service.yt_dlp.YoutubeDL') as mock_ytdl:
            mock_ydl_instance = Mock()
            mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
            mock_ydl_instance.extract_info.return_value = sample_youtube_info
            
            result = youtube_service.search_videos("test query")
        
        # Assert - Validate response format
        assert isinstance(result, list)
        for video in result:
            assert "id" in video
            assert "title" in video
            assert "url" in video
            assert video["url"].startswith("https://www.youtube.com/watch?v=")

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_ytdlp_extraction_failure(self, mock_ytdl, youtube_service):
        """Test search_videos() yt-dlp extraction failures"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.side_effect = Exception("yt-dlp extraction failed")
        
        # Act & Assert
        with pytest.raises(ServiceError, match="Failed to search YouTube"):
            youtube_service.search_videos("test query")

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_network_timeout(self, mock_ytdl, youtube_service):
        """Test search_videos() network timeouts"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.side_effect = Exception("Network timeout")
        
        # Act & Assert
        with pytest.raises(ServiceError, match="Failed to search YouTube"):
            youtube_service.search_videos("test query")

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_malformed_response(self, mock_ytdl, youtube_service):
        """Test search_videos() malformed responses"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = {"invalid": "response"}  # No entries
        
        # Act
        result = youtube_service.search_videos("test query")
        
        # Assert
        assert result == []


class TestDownloadVideo:
    """Test core video download logic"""

    @pytest.fixture
    def mock_file_service(self):
        """Mock FileServiceInterface for testing"""
        mock_service = Mock(spec=FileServiceInterface)
        mock_service.get_song_directory.return_value = Path("/test/songs/test-id")
        mock_service.get_original_path.return_value = Path("/test/songs/test-id/original.mp3")
        return mock_service

    @pytest.fixture
    def mock_song_service(self):
        """Mock SongServiceInterface for testing"""
        return Mock(spec=SongServiceInterface)

    @pytest.fixture
    def youtube_service(self, mock_file_service, mock_song_service):
        """YouTubeService instance with mocked dependencies"""
        return YouTubeService(
            file_service=mock_file_service,
            song_service=mock_song_service
        )

    @pytest.fixture
    def sample_youtube_info(self):
        """Sample yt-dlp video info response"""
        return {
            "id": "dQw4w9WgXcQ",
            "title": "Rick Astley - Never Gonna Give You Up",
            "uploader": "Rick Astley",
            "uploader_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
            "channel": "Rick Astley",
            "channel_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
            "duration": 213,
            "upload_date": "20091025",
            "description": "Official video for Never Gonna Give You Up",
            "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "thumbnails": [
                {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg", "width": 1280, "height": 720}
            ]
        }

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_download_video_with_video_id_input(self, mock_ytdl, youtube_service, mock_file_service, sample_youtube_info):
        """Test download_video() with video ID input"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_youtube_info
        
        # Mock file exists check
        with patch('pathlib.Path.exists', return_value=True):
            # Act
            song_id, metadata = youtube_service.download_video("dQw4w9WgXcQ")
        
        # Assert
        assert isinstance(song_id, str)
        assert len(song_id) == 36  # UUID length
        assert isinstance(metadata, SongMetadata)
        assert metadata.title == "Rick Astley - Never Gonna Give You Up"
        assert metadata.videoId == "dQw4w9WgXcQ"

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_download_video_with_full_url_input(self, mock_ytdl, youtube_service, sample_youtube_info):
        """Test download_video() with full URL input"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_youtube_info
        
        with patch('pathlib.Path.exists', return_value=True):
            # Act
            song_id, metadata = youtube_service.download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        
        # Assert
        assert isinstance(song_id, str)
        assert metadata.videoId == "dQw4w9WgXcQ"

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_download_video_with_custom_song_id(self, mock_ytdl, youtube_service, sample_youtube_info):
        """Test download_video() with custom song_id"""
        # Arrange
        custom_song_id = "custom-test-id-123"
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_youtube_info
        
        with patch('pathlib.Path.exists', return_value=True):
            # Act
            song_id, metadata = youtube_service.download_video("dQw4w9WgXcQ", song_id=custom_song_id)
        
        # Assert
        assert song_id == custom_song_id

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_download_video_with_artist_title_overrides(self, mock_ytdl, youtube_service, sample_youtube_info):
        """Test download_video() with artist/title overrides"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_youtube_info
        
        with patch('pathlib.Path.exists', return_value=True):
            # Act
            song_id, metadata = youtube_service.download_video(
                "dQw4w9WgXcQ", 
                artist="Custom Artist", 
                title="Custom Title"
            )
        
        # Assert
        assert metadata.artist == "Custom Artist"
        assert metadata.title == "Custom Title"
        # Original video title should still be preserved
        assert metadata.videoTitle == "Rick Astley - Never Gonna Give You Up"

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_download_video_file_creation_verification(self, mock_ytdl, youtube_service, mock_file_service, sample_youtube_info):
        """Test download_video() file creation verification"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_youtube_info
        
        with patch('pathlib.Path.exists', return_value=True):
            # Act
            song_id, metadata = youtube_service.download_video("dQw4w9WgXcQ")
        
        # Assert
        assert mock_file_service.get_song_directory.call_count >= 1
        mock_file_service.get_song_directory.assert_called_with(song_id)
        mock_file_service.get_original_path.assert_called_once_with(song_id, ".mp3")

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_download_video_metadata_extraction(self, mock_ytdl, youtube_service, sample_youtube_info):
        """Test download_video() metadata extraction"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_youtube_info
        
        with patch('pathlib.Path.exists', return_value=True):
            # Act
            song_id, metadata = youtube_service.download_video("dQw4w9WgXcQ")
        
        # Assert - Check metadata extraction
        assert metadata.videoId == "dQw4w9WgXcQ"
        assert metadata.videoTitle == "Rick Astley - Never Gonna Give You Up"
        assert metadata.uploader == "Rick Astley"
        assert metadata.channel == "Rick Astley"
        assert metadata.duration == 213
        assert metadata.source == "youtube"
        assert metadata.sourceUrl == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_download_video_invalid_url_error(self, mock_ytdl, youtube_service):
        """Test download_video() with invalid URLs that trigger ServiceError"""
        # Test a valid YouTube URL format but with no video ID extractable
        # This should pass validation but fail video ID extraction
        # Mock the URL validation to return True, but video ID extraction to return None
        with patch.object(youtube_service, 'validate_video_url', return_value=True), \
             patch.object(youtube_service, 'get_video_id_from_url', return_value=None):
        
            with pytest.raises(ServiceError, match="Failed to download YouTube video"):
                youtube_service.download_video("https://www.youtube.com/watch?v=invalid")

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_download_video_ytdlp_download_failure(self, mock_ytdl, youtube_service):
        """Test download_video() yt-dlp download failures"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.side_effect = Exception("Download failed")
        
        # Act & Assert
        with pytest.raises(ServiceError, match="Failed to download YouTube video"):
            youtube_service.download_video("dQw4w9WgXcQ")

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_download_video_file_creation_failure(self, mock_ytdl, youtube_service, sample_youtube_info):
        """Test download_video() file creation failures"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_youtube_info
        
        # Mock file doesn't exist after download
        with patch('pathlib.Path.exists', return_value=False):
            # Act & Assert
            with pytest.raises(ServiceError, match="Download completed but file not found"):
                youtube_service.download_video("dQw4w9WgXcQ")

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')  
    def test_download_video_missing_original_files(self, mock_ytdl, youtube_service, mock_file_service, sample_youtube_info):
        """Test download_video() with missing original files"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_youtube_info
        
        # Mock file service to return non-existent path
        mock_file_service.get_original_path.return_value = Path("/nonexistent/path.mp3")
        
        with patch('pathlib.Path.exists', return_value=False):
            # Act & Assert
            with pytest.raises(ServiceError, match="Download completed but file not found"):
                youtube_service.download_video("dQw4w9WgXcQ")
