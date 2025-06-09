"""
YouTube Service Channel and Metadata Extraction Tests

Tests for YouTube-specific metadata extraction including channel IDs, 
channel names, and enhanced YouTube fields (Phase 1B features).
"""

import pytest
from unittest.mock import Mock, patch

from app.services.youtube_service import YouTubeService


class TestYouTubeChannelExtraction:
    """Test YouTube channel ID and name extraction"""

    def test_channel_id_extraction_with_channel_id(self, youtube_service):
        """Test channel ID extraction when channel_id is available"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "channel_id": "UC123456789",
            "uploader_id": "UP987654321",
            "uploader": "Test Channel",
            "channel": "Test Channel Name"
        }

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)

        # Assert
        assert metadata.channelId == "UC123456789"
        assert metadata.youtubeChannelId == "UC123456789"
        assert metadata.uploaderId == "UP987654321"

    def test_channel_id_extraction_fallback_to_uploader_id(self, youtube_service):
        """Test channel ID extraction falls back to uploader_id when channel_id missing"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "uploader_id": "UP987654321",
            "uploader": "Test Channel",
            "channel": "Test Channel Name"
            # No channel_id field
        }

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)

        # Assert
        assert metadata.channelId == "UP987654321"  # Fallback to uploader_id
        assert metadata.youtubeChannelId == "UP987654321"
        assert metadata.uploaderId == "UP987654321"

    def test_channel_id_extraction_no_ids_available(self, youtube_service):
        """Test channel ID extraction when no IDs are available"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "uploader": "Test Channel",
            "channel": "Test Channel Name"
            # No channel_id or uploader_id
        }

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)

        # Assert
        assert metadata.channelId is None
        assert metadata.youtubeChannelId is None
        assert metadata.uploaderId is None

    def test_youtube_channel_name_extraction_with_channel(self, youtube_service):
        """Test channel name extraction when 'channel' field is available"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "channel_id": "UC123456789",
            "uploader": "Test Uploader",
            "channel": "Test Channel Official"
        }

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)

        # Assert
        assert metadata.youtubeChannelName == "Test Channel Official"
        assert metadata.channel == "Test Channel Official"  # Legacy field    def test_youtube_channel_name_fallback_to_uploader(self, youtube_service):
        """Test channel name extraction falls back to uploader when channel missing"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "channel_id": "UC123456789",
            "uploader": "Test Uploader"
            # No channel field
        }
        
        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)
        
        # Assert
        assert metadata.youtubeChannelName == "Test Uploader"
        # Note: legacy channel field will be None since no "channel" key in video_info

    def test_channel_extraction_empty_strings(self, youtube_service):
        """Test channel extraction handles empty strings gracefully"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "channel_id": "",
            "uploader_id": "",
            "uploader": "",
            "channel": ""
        }

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)

        # Assert
        # Note: The service currently preserves empty strings, doesn't convert to None
        assert metadata.channelId == ""  # Empty string preserved
        assert metadata.youtubeChannelId == ""
        assert metadata.uploaderId == ""
        assert metadata.youtubeChannelName == ""  # Falls back to empty uploader

    def test_channel_extraction_whitespace_handling(self, youtube_service):
        """Test channel extraction handles whitespace properly"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "channel_id": "  UC123456789  ",
            "uploader": "  Test Channel  ",
            "channel": "  Test Channel Official  "
        }

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)

        # Assert
        # Note: The service currently preserves whitespace, doesn't strip it automatically
        assert metadata.channelId == "  UC123456789  "  # Whitespace preserved
        assert metadata.youtubeChannelName == "  Test Channel Official  "  # channel takes precedence over uploader


class TestYouTubeEnhancedMetadataExtraction:
    """Test enhanced YouTube metadata extraction (Phase 1B features)"""

    @patch('app.services.metadata_service.filter_youtube_metadata_for_storage')
    def test_enhanced_youtube_fields_extraction(self, mock_filter, youtube_service):
        """Test enhanced YouTube-specific fields are extracted correctly"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "uploader": "Test Channel",
            "channel_id": "UC123456789",
            "channel": "Test Channel Official",
            "duration": 200,
            "tags": ["music", "test", "video"],
            "categories": ["Music", "Entertainment"],
            "thumbnails": [
                {"url": "http://example.com/thumb120.jpg", "height": 120},
                {"url": "http://example.com/thumb320.jpg", "height": 320},
                {"url": "http://example.com/thumb640.jpg", "height": 640},
                {"url": "http://example.com/thumb1080.jpg", "height": 1080}
            ]
        }

        mock_filter.return_value = '{"filtered": "metadata"}'

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)

        # Assert enhanced YouTube fields
        assert metadata.youtubeTags == ["music", "test", "video"]
        assert metadata.youtubeCategories == ["Music", "Entertainment"]
        assert metadata.youtubeChannelId == "UC123456789"
        assert metadata.youtubeChannelName == "Test Channel Official"
        
        # Verify thumbnail extraction (should select specific resolutions)
        assert metadata.youtubeThumbnailUrls is not None
        assert len(metadata.youtubeThumbnailUrls) <= 3
        assert "http://example.com/thumb120.jpg" in metadata.youtubeThumbnailUrls
        assert "http://example.com/thumb320.jpg" in metadata.youtubeThumbnailUrls
        assert "http://example.com/thumb640.jpg" in metadata.youtubeThumbnailUrls
        
        # Verify raw metadata storage
        assert metadata.youtubeRawMetadata == '{"filtered": "metadata"}'
        mock_filter.assert_called_once_with(video_info)

    def test_youtube_tags_extraction_empty_list(self, youtube_service):
        """Test YouTube tags extraction with empty list"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "uploader": "Test Channel",
            "tags": []  # Empty tags list
        }

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)

        # Assert
        assert metadata.youtubeTags == []

    def test_youtube_tags_extraction_missing_field(self, youtube_service):
        """Test YouTube tags extraction when tags field is missing"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "uploader": "Test Channel"
            # No tags field
        }

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)

        # Assert
        assert metadata.youtubeTags == []  # Default empty list when field missing

    def test_youtube_categories_extraction_single_category(self, youtube_service):
        """Test YouTube categories extraction with single category"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "uploader": "Test Channel",
            "categories": ["Music"]
        }

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)

        # Assert
        assert metadata.youtubeCategories == ["Music"]

    def test_youtube_categories_extraction_missing_field(self, youtube_service):
        """Test YouTube categories extraction when categories field is missing"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "uploader": "Test Channel"
            # No categories field
        }

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)

        # Assert
        assert metadata.youtubeCategories == []  # Default empty list when field missing


class TestYouTubeThumbnailExtraction:
    """Test YouTube thumbnail URL extraction"""

    def test_thumbnail_extraction_multiple_resolutions(self, youtube_service):
        """Test thumbnail extraction with multiple resolutions"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "uploader": "Test Channel",
            "thumbnails": [
                {"url": "http://example.com/thumb90.jpg", "height": 90},
                {"url": "http://example.com/thumb120.jpg", "height": 120},
                {"url": "http://example.com/thumb320.jpg", "height": 320},
                {"url": "http://example.com/thumb480.jpg", "height": 480},
                {"url": "http://example.com/thumb640.jpg", "height": 640},
                {"url": "http://example.com/thumb1080.jpg", "height": 1080},
                {"url": "http://example.com/thumb1440.jpg", "height": 1440}
            ]
        }

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)

        # Assert
        assert metadata.youtubeThumbnailUrls is not None
        assert len(metadata.youtubeThumbnailUrls) <= 3
        # Should include preferred resolutions: 120, 320, 640
        assert "http://example.com/thumb120.jpg" in metadata.youtubeThumbnailUrls
        assert "http://example.com/thumb320.jpg" in metadata.youtubeThumbnailUrls
        assert "http://example.com/thumb640.jpg" in metadata.youtubeThumbnailUrls
        # Should not include others
        assert "http://example.com/thumb90.jpg" not in metadata.youtubeThumbnailUrls
        assert "http://example.com/thumb1080.jpg" not in metadata.youtubeThumbnailUrls

    def test_thumbnail_extraction_no_thumbnails(self, youtube_service):
        """Test thumbnail extraction when no thumbnails are available"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "uploader": "Test Channel"
            # No thumbnails field
        }

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)

        # Assert
        assert metadata.youtubeThumbnailUrls is None
        
    def test_thumbnail_extraction_no_matching_resolutions(self, youtube_service):
        """Test thumbnail extraction when no matching resolutions are found"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "uploader": "Test Channel",
            "thumbnails": [
                {"url": "http://example.com/thumb90.jpg", "height": 90},
                {"url": "http://example.com/thumb480.jpg", "height": 480}  # Changed from 1200 to 480 which doesn't match
            ]
        }
        
        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)
        
        # Assert
        assert metadata.youtubeThumbnailUrls is None  # No matching resolutions (120, 320, 640)

    def test_thumbnail_extraction_partial_matches(self, youtube_service):
        """Test thumbnail extraction with only some matching resolutions"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "uploader": "Test Channel",
            "thumbnails": [
                {"url": "http://example.com/thumb120.jpg", "height": 120},
                {"url": "http://example.com/thumb480.jpg", "height": 480},  # Not preferred
                {"url": "http://example.com/thumb640.jpg", "height": 640}
                # Missing 320 resolution
            ]
        }

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)

        # Assert
        assert metadata.youtubeThumbnailUrls is not None
        assert len(metadata.youtubeThumbnailUrls) == 2
        assert "http://example.com/thumb120.jpg" in metadata.youtubeThumbnailUrls
        assert "http://example.com/thumb640.jpg" in metadata.youtubeThumbnailUrls
        assert "http://example.com/thumb480.jpg" not in metadata.youtubeThumbnailUrls

    def test_thumbnail_extraction_missing_height(self, youtube_service):
        """Test thumbnail extraction with thumbnails missing height information"""
        # Arrange
        video_info = {
            "id": "test123",
            "title": "Test Video",
            "uploader": "Test Channel",
            "thumbnails": [
                {"url": "http://example.com/thumb1.jpg"},  # No height
                {"url": "http://example.com/thumb320.jpg", "height": 320},
                {"url": "http://example.com/thumb2.jpg"}   # No height
            ]
        }

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(video_info)

        # Assert
        assert metadata.youtubeThumbnailUrls is not None
        assert len(metadata.youtubeThumbnailUrls) == 1
        assert "http://example.com/thumb320.jpg" in metadata.youtubeThumbnailUrls
