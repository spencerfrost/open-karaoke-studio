"""
Core YouTube Service Tests

Tests for service construction, dependency injection, and URL validation.
"""

import pytest
from unittest.mock import Mock

from app.services.youtube_service import YouTubeService
from app.services.interfaces.youtube_service import YouTubeServiceInterface
from app.services.interfaces.file_service import FileServiceInterface


class TestYouTubeServiceConstruction:
    """Test service initialization and dependency injection"""

    def test_constructor_with_injected_dependencies(self):
        """Test YouTubeService constructor with injected dependencies"""
        # Arrange
        mock_file_service = Mock(spec=FileServiceInterface)
        mock_song_service = Mock(spec=SongServiceInterface)

        # Act
        service = YouTubeService(
            file_service=mock_file_service, song_service=mock_song_service
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
        assert hasattr(service.file_service, "get_song_directory")  # FileService method
        assert service.song_service is None  # Injected to avoid circular dependency

    def test_interface_compliance(self):
        """Verify interface compliance with YouTubeServiceInterface"""
        # Arrange
        mock_file_service = Mock(spec=FileServiceInterface)
        service = YouTubeService(file_service=mock_file_service)

        # Assert - Check all interface methods exist
        assert hasattr(service, "search_videos")
        assert hasattr(service, "download_video")
        assert hasattr(service, "extract_video_info")
        assert hasattr(service, "validate_video_url")
        assert hasattr(service, "get_video_id_from_url")
        assert hasattr(service, "download_and_process_async")

        # Verify it's a proper protocol implementation
        assert isinstance(service, YouTubeServiceInterface)

    def test_dependency_injection_patterns(self):
        """Test proper dependency injection patterns"""
        # Arrange
        mock_file_service = Mock(spec=FileServiceInterface)
        mock_song_service = Mock(spec=SongServiceInterface)

        # Act
        service = YouTubeService(
            file_service=mock_file_service, song_service=mock_song_service
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

    def test_validate_video_url_valid_standard_format(
        self, youtube_service_no_song_service
    ):
        """Test validate_video_url() with standard YouTube URL format"""
        # Arrange
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
        ]

        # Act & Assert
        for url in valid_urls:
            assert youtube_service_no_song_service.validate_video_url(url) is True

    def test_validate_video_url_valid_short_format(
        self, youtube_service_no_song_service
    ):
        """Test validate_video_url() with short YouTube URL format"""
        # Arrange
        valid_urls = [
            "https://youtu.be/dQw4w9WgXcQ",
            "http://youtu.be/dQw4w9WgXcQ",
        ]

        # Act & Assert
        for url in valid_urls:
            assert youtube_service_no_song_service.validate_video_url(url) is True

    def test_validate_video_url_valid_mobile_format(
        self, youtube_service_no_song_service
    ):
        """Test validate_video_url() with mobile YouTube URL format"""
        # Arrange
        valid_urls = [
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://m.youtube.com/watch?v=dQw4w9WgXcQ",
        ]

        # Act & Assert
        for url in valid_urls:
            assert youtube_service_no_song_service.validate_video_url(url) is True

    def test_validate_video_url_valid_embedded_format(
        self, youtube_service_no_song_service
    ):
        """Test validate_video_url() with embedded YouTube URL format"""
        # Arrange
        valid_urls = [
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "http://www.youtube.com/embed/dQw4w9WgXcQ",
        ]

        # Act & Assert
        for url in valid_urls:
            assert youtube_service_no_song_service.validate_video_url(url) is True

    def test_validate_video_url_valid_with_parameters(
        self, youtube_service_no_song_service
    ):
        """Test validate_video_url() with URLs containing parameters"""
        # Arrange
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLx0sYbCqOb8TBPRdmBHs5Iftvv9TPboYG",
            "https://youtu.be/dQw4w9WgXcQ?t=30",
        ]

        # Act & Assert
        for url in valid_urls:
            assert youtube_service_no_song_service.validate_video_url(url) is True

    def test_validate_video_url_invalid_non_youtube_domains(
        self, youtube_service_no_song_service
    ):
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
            assert youtube_service_no_song_service.validate_video_url(url) is False

    def test_validate_video_url_invalid_malformed_urls(
        self, youtube_service_no_song_service
    ):
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
            assert youtube_service_no_song_service.validate_video_url(url) is False

    def test_validate_video_url_invalid_empty_and_non_string(
        self, youtube_service_no_song_service
    ):
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
                result = youtube_service_no_song_service.validate_video_url(
                    invalid_input
                )
                assert result is False
            except (TypeError, AttributeError):
                # Acceptable to raise type errors for non-string inputs
                pass

    def test_get_video_id_from_url_extraction_accuracy(
        self, youtube_service_no_song_service
    ):
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
            result = youtube_service_no_song_service.get_video_id_from_url(url)
            assert result == expected_id

    def test_get_video_id_from_url_invalid_inputs(
        self, youtube_service_no_song_service
    ):
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
            result = youtube_service_no_song_service.get_video_id_from_url(
                invalid_input
            )
            assert result is None
