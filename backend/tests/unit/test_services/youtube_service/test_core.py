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
        # mock_song_service removed - YouTubeService no longer uses SongService

        # Act
        service = YouTubeService(
            file_service=mock_file_service  # song_service removed
        )

        # Assert
        assert service.file_service is mock_file_service
        # assert service.song_service removed - no longer used