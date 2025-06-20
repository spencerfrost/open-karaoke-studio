"""
YouTube Service Dictionary-Based Tests

Tests for the new dict-based YouTube service that replaces SongMetadata patterns.
This test file covers the current YouTube service architecture where:
- download_video() returns (song_id, metadata_dict)
- _extract_metadata_from_youtube_info() returns dict, not SongMetadata
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from typing import Dict, Any
import uuid

from app.services.youtube_service import YouTubeService
from app.exceptions import ServiceError, ValidationError


class TestYouTubeServiceDictPatterns:
    """Test the new dictionary-based YouTube service patterns"""

    @pytest.fixture
    def youtube_service(self):
        """Create YouTube service with mocked dependencies"""
        mock_file_service = Mock()
        # Mock all methods to return Mock objects with proper behavior
        mock_song_dir = Mock()
        mock_song_dir.__truediv__ = Mock(return_value=Mock())
        mock_file_service.get_song_directory.return_value = mock_song_dir
        mock_file_service.get_original_path.return_value = Mock()
        return YouTubeService(file_service=mock_file_service)

    @pytest.fixture
    def complete_youtube_info(self) -> Dict[str, Any]:
        """Complete YouTube video info dict for testing"""
        return {
            "id": "dQw4w9WgXcQ",
            "title": "Rick Astley - Never Gonna Give You Up (Official Video)",
            "uploader": "Rick Astley",
            "uploader_id": "RickAstleyVEVO",
            "channel": "Rick Astley",
            "channel_id": "UC-lHJZR3Gqxm24_Vd_AJ5Yw",
            "duration": 213,
            "description": "The official video for Rick Astley's Never Gonna Give You Up",
            "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "upload_date": "20091024",
            "thumbnails": [
                {
                    "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
                    "preference": 1,
                }
            ],
        }

    @pytest.fixture
    def minimal_youtube_info(self) -> Dict[str, Any]:
        """Minimal YouTube video info dict for testing fallback values"""
        return {"id": "abc123", "webpage_url": "https://www.youtube.com/watch?v=abc123"}

    def test_extract_metadata_from_youtube_info_complete_data(
        self, youtube_service, complete_youtube_info
    ):
        """Test _extract_metadata_from_youtube_info() returns proper dictionary structure"""
        # Act
        metadata_dict = youtube_service._extract_metadata_from_youtube_info(
            complete_youtube_info
        )

        # Assert - Check it returns a dictionary
        assert isinstance(metadata_dict, dict)

        # Assert - Check expected keys exist
        expected_keys = [
            "title",
            "artist",
            "duration",
            "source",
            "source_url",
            "video_id",
            "uploader",
            "uploader_id",
            "channel",
            "channel_id",
            "description",
            "upload_date",
        ]
        for key in expected_keys:
            assert key in metadata_dict

        # Assert - Check values are correctly mapped
        assert (
            metadata_dict["title"]
            == "Rick Astley - Never Gonna Give You Up (Official Video)"
        )
        assert metadata_dict["artist"] == "Rick Astley"
        assert metadata_dict["duration"] == 213
        assert metadata_dict["source"] == "youtube"
        assert (
            metadata_dict["source_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        assert metadata_dict["video_id"] == "dQw4w9WgXcQ"
        assert metadata_dict["uploader"] == "Rick Astley"
        assert metadata_dict["channel"] == "Rick Astley"
        assert metadata_dict["channel_id"] == "UC-lHJZR3Gqxm24_Vd_AJ5Yw"

    def test_extract_metadata_from_youtube_info_minimal_data(
        self, youtube_service, minimal_youtube_info
    ):
        """Test _extract_metadata_from_youtube_info() handles minimal data with fallbacks"""
        # Act
        metadata_dict = youtube_service._extract_metadata_from_youtube_info(
            minimal_youtube_info
        )

        # Assert - Check fallback values are used
        assert metadata_dict["title"] == "Unknown Title"
        assert metadata_dict["artist"] == "Unknown Artist"
        assert metadata_dict["duration"] is None
        assert metadata_dict["source"] == "youtube"
        assert metadata_dict["source_url"] == "https://www.youtube.com/watch?v=abc123"
        assert metadata_dict["video_id"] == "abc123"

    def test_extract_metadata_from_youtube_info_type_validation(
        self, youtube_service, complete_youtube_info
    ):
        """Test _extract_metadata_from_youtube_info() returns proper data types"""
        # Act
        metadata_dict = youtube_service._extract_metadata_from_youtube_info(
            complete_youtube_info
        )

        # Assert - Check data types
        assert isinstance(metadata_dict["title"], str)
        assert isinstance(metadata_dict["artist"], str)
        assert isinstance(metadata_dict["duration"], int)
        assert isinstance(metadata_dict["source"], str)
        assert isinstance(metadata_dict["source_url"], str)
        assert isinstance(metadata_dict["video_id"], str)
        assert (
            isinstance(metadata_dict["upload_date"], datetime)
            or metadata_dict["upload_date"] is None
        )

    def test_extract_metadata_handles_missing_optional_fields(self, youtube_service):
        """Test _extract_metadata_from_youtube_info() handles missing optional fields gracefully"""
        # Arrange - Info with only required fields
        minimal_info = {"id": "test123"}

        # Act
        metadata_dict = youtube_service._extract_metadata_from_youtube_info(
            minimal_info
        )

        # Assert - Optional fields should be None or have default values
        assert metadata_dict["description"] is None
        assert metadata_dict["upload_date"] is None
        assert metadata_dict["channel_id"] is None
        assert metadata_dict["duration"] is None

    def test_extract_metadata_channel_id_fallback(self, youtube_service):
        """Test channel_id fallback to uploader_id when channel_id is missing"""
        # Arrange
        info_with_uploader_id = {"id": "test123", "uploader_id": "TestUploaderID"}

        # Act
        metadata_dict = youtube_service._extract_metadata_from_youtube_info(
            info_with_uploader_id
        )

        # Assert - Should use uploader_id as channel_id fallback
        assert (
            metadata_dict["channel_id"] == "TestUploaderID"
        )  # TODO: Complex download tests require better file service mocking

    # These tests should be added when we improve the test infrastructure

    # @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    # @patch.object(YouTubeService, '_extract_audio_duration')
    # def test_download_video_returns_correct_tuple_format(self, mock_extract_duration, mock_yt_dlp, youtube_service, complete_youtube_info):
    #     """Test download_video() returns (song_id, metadata_dict) tuple"""
    #     # Complex file mocking needed - postponed for now
    #     pass

    # @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    # def test_download_video_generates_song_id_when_not_provided(self, mock_yt_dlp, youtube_service, complete_youtube_info):
    #     """Test download_video() generates UUID when song_id is not provided"""
    #     # Complex file mocking needed - postponed for now
    #     pass

    # @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    # def test_download_video_overrides_metadata_with_provided_params(self, mock_yt_dlp, youtube_service, complete_youtube_info):
    #     """Test download_video() overrides metadata dict with provided title/artist"""
    #     # Complex file mocking needed - postponed for now
    #     pass

    def test_parse_upload_date_valid_format(self, youtube_service):
        """Test _parse_upload_date() handles valid YYYYMMDD format"""
        # Act
        result = youtube_service._parse_upload_date("20231225")

        # Assert
        assert isinstance(result, datetime)
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 25
        assert result.tzinfo == timezone.utc

    def test_parse_upload_date_invalid_format(self, youtube_service):
        """Test _parse_upload_date() handles invalid format gracefully"""
        # Act
        result = youtube_service._parse_upload_date("invalid-date")

        # Assert
        assert result is None

    def test_parse_upload_date_none_input(self, youtube_service):
        """Test _parse_upload_date() handles None input"""
        # Act
        result = youtube_service._parse_upload_date(None)

        # Assert
        assert result is None

    @patch("app.services.youtube_service.yt_dlp.YoutubeDL")
    def test_download_video_error_handling(self, mock_yt_dlp, youtube_service):
        """Test download_video() error handling raises ServiceError"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.side_effect = Exception(
            "YouTube download failed"
        )

        # Act & Assert
        with pytest.raises(ServiceError, match="Failed to download YouTube video"):
            youtube_service.download_video("https://www.youtube.com/watch?v=invalid")

    def test_metadata_dict_compatibility_with_create_or_update_song(
        self, youtube_service, complete_youtube_info
    ):
        """Test that metadata dict contains fields compatible with create_or_update_song()"""
        # Act
        metadata_dict = youtube_service._extract_metadata_from_youtube_info(
            complete_youtube_info
        )

        # Assert - Check that dict contains fields that create_or_update_song() expects
        # Based on the new direct parameter approach
        expected_fields = {
            "title": str,
            "artist": str,
            "duration": (int, type(None)),
            "source": str,
            "source_url": str,
            "video_id": str,
        }

        for field, expected_type in expected_fields.items():
            assert field in metadata_dict
            if isinstance(expected_type, tuple):
                assert (
                    isinstance(metadata_dict[field], expected_type)
                    or metadata_dict[field] is None
                )
            else:
                assert isinstance(metadata_dict[field], expected_type)
