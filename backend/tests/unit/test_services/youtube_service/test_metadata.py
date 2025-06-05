"""
YouTube Metadata Extraction Tests

Tests for YouTube info → SongMetadata conversion and processing.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from app.services.youtube_service import YouTubeService
from app.db.models import SongMetadata


class TestMetadataExtraction:
    """Test YouTube info → SongMetadata conversion"""

    def test_extract_metadata_from_youtube_info_complete_data(self, youtube_service, complete_youtube_info):
        """Test _extract_metadata_from_youtube_info() with complete data"""
        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(complete_youtube_info)
        
        # Assert - Check all field mappings
        assert metadata.title == "Rick Astley - Never Gonna Give You Up (Official Video)"
        assert metadata.artist == "Rick Astley"
        assert metadata.duration == 213
        assert metadata.source == "youtube"
        assert metadata.sourceUrl == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert metadata.videoId == "dQw4w9WgXcQ"
        assert metadata.videoTitle == "Rick Astley - Never Gonna Give You Up (Official Video)"
        assert metadata.uploader == "Rick Astley"
        assert metadata.channel == "Rick Astley"
        assert isinstance(metadata.dateAdded, datetime)
    
    def test_extract_metadata_from_youtube_info_missing_fields(self, youtube_service, partial_youtube_info):
        """Test _extract_metadata_from_youtube_info() with missing fields"""
        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(partial_youtube_info)

        # Assert - Check default values for missing fields
        assert metadata.title == "Sample Video"
        assert metadata.artist == "Unknown Artist"  # Default when uploader missing
        assert metadata.duration is None
        assert metadata.source == "youtube"
        assert metadata.sourceUrl == "https://www.youtube.com/watch?v=abc123def45"
        assert metadata.videoId == "abc123def45"
        assert metadata.uploader is None  # uploader field itself doesn't get default value
        assert metadata.channel is None

    def test_metadata_field_mapping_accuracy(self, youtube_service, complete_youtube_info):
        """Test metadata field mapping accuracy"""
        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(complete_youtube_info)
        
        # Assert - Verify specific mappings
        assert metadata.title == complete_youtube_info["title"]
        assert metadata.artist == complete_youtube_info["uploader"]
        assert metadata.duration == complete_youtube_info["duration"]
        assert metadata.videoId == complete_youtube_info["id"]
        assert metadata.channel == complete_youtube_info["channel"]
        assert metadata.sourceUrl == complete_youtube_info["webpage_url"]

    def test_metadata_datetime_handling(self, youtube_service, complete_youtube_info):
        """Test metadata datetime field handling"""
        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(complete_youtube_info)
        
        # Assert - dateAdded should be current time with UTC timezone
        assert isinstance(metadata.dateAdded, datetime)
        assert metadata.dateAdded.tzinfo == timezone.utc
        # Should be very recent (within last minute)
        time_diff = datetime.now(timezone.utc) - metadata.dateAdded
        assert time_diff.total_seconds() < 60

    def test_metadata_source_fields_consistency(self, youtube_service, complete_youtube_info):
        """Test source-related fields are set consistently"""
        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(complete_youtube_info)
        
        # Assert - Source fields should be consistent
        assert metadata.source == "youtube"
        assert metadata.sourceUrl is not None
        assert metadata.videoId is not None
        assert "youtube.com" in metadata.sourceUrl

    def test_metadata_youtube_specific_fields(self, youtube_service, complete_youtube_info):
        """Test YouTube-specific field extraction"""
        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(complete_youtube_info)
        
        # Assert - YouTube-specific fields
        assert metadata.videoId == complete_youtube_info["id"]
        assert metadata.videoTitle == complete_youtube_info["title"]
        assert metadata.uploader == complete_youtube_info["uploader"]
        assert metadata.channel == complete_youtube_info["channel"]

    def test_metadata_empty_youtube_info(self, youtube_service):
        """Test _extract_metadata_from_youtube_info() with empty info"""
        # Arrange
        empty_info = {}
        
        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(empty_info)
        
        # Assert - Should handle missing fields gracefully
        assert metadata.title == "Unknown Title"
        assert metadata.artist == "Unknown Artist"
        assert metadata.source == "youtube"
        assert metadata.duration is None
        assert metadata.videoId is None
    
    def test_metadata_partial_youtube_info_fallbacks(self, youtube_service):
        """Test fallback behavior with partial YouTube info"""
        # Arrange
        minimal_info = {
            "id": "test123",
            "title": "Test Video"
            # Missing uploader, channel, etc.
        }

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(minimal_info)

        # Assert - Check fallback values
        assert metadata.title == "Test Video"
        assert metadata.artist == "Unknown Artist"  # Fallback for missing uploader
        assert metadata.videoId == "test123"
        assert metadata.uploader is None  # uploader field itself doesn't get default value
        assert metadata.channel is None
    
    def test_metadata_none_values_handling(self, youtube_service):
        """Test handling of None values in YouTube info"""
        # Arrange
        info_with_nones = {
            "id": "test123",
            "title": None,
            "uploader": None,
            "duration": None,
            "webpage_url": None
        }

        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(info_with_nones)

        # Assert - Should handle None values gracefully
        # Note: .get(key, default) returns None when key exists but has None value
        assert metadata.title is None  # .get('title', 'Unknown Title') returns None when title=None
        assert metadata.artist is None  # .get('uploader', 'Unknown Artist') returns None when uploader=None
        assert metadata.duration is None  # No default provided for duration
        assert metadata.sourceUrl is None  # No default provided for webpage_url
        assert metadata.uploader is None  # uploader field itself gets None value
        assert metadata.videoId == "test123"

    def test_metadata_type_conversion(self, youtube_service):
        """Test proper type conversion in metadata extraction"""
        # Arrange
        info_with_types = {
            "id": "test123",
            "title": "Test Video",
            "uploader": "Test Uploader",
            "duration": 300.5,  # Float duration
            "webpage_url": "https://youtube.com/watch?v=test123"
        }
        
        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(info_with_types)
        
        # Assert - Check types are preserved/converted correctly
        assert isinstance(metadata.title, str)
        assert isinstance(metadata.artist, str)
        assert isinstance(metadata.duration, float)
        assert metadata.duration == 300.5
        assert isinstance(metadata.sourceUrl, str)

    def test_metadata_model_validation(self, youtube_service, complete_youtube_info):
        """Test that extracted metadata passes Pydantic validation"""
        # Act
        metadata = youtube_service._extract_metadata_from_youtube_info(complete_youtube_info)
        
        # Assert - Should be valid SongMetadata instance
        assert isinstance(metadata, SongMetadata)
        
        # Test serialization/deserialization to ensure model is valid
        metadata_dict = metadata.model_dump()
        reconstructed = SongMetadata(**metadata_dict)
        
        assert reconstructed.title == metadata.title
        assert reconstructed.artist == metadata.artist
        assert reconstructed.source == metadata.source
