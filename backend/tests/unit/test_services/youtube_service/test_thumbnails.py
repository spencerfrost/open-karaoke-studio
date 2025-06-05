"""
YouTube Thumbnail Operations Tests

Tests for thumbnail download and processing functionality.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from app.db.models import SongMetadata


class TestThumbnailOperations:
    """Test thumbnail download and processing"""

    def test_get_best_thumbnail_url_with_multiple_options(self, youtube_service, sample_thumbnails):
        """Test _get_best_thumbnail_url() with multiple options"""
        # Arrange
        video_info = {"thumbnails": sample_thumbnails}
        
        # Act
        best_url = youtube_service._get_best_thumbnail_url(video_info)
        
        # Assert - Should return highest preference thumbnail
        assert best_url == "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"

    def test_get_best_thumbnail_url_preference_based_selection(self, youtube_service):
        """Test preference-based selection in _get_best_thumbnail_url()"""
        # Arrange - Thumbnails with different preferences
        video_info = {
            "thumbnails": [
                {"url": "low.jpg", "preference": 1},
                {"url": "high.jpg", "preference": 100},
                {"url": "medium.jpg", "preference": 50}
            ]
        }
        
        # Act
        best_url = youtube_service._get_best_thumbnail_url(video_info)
        
        # Assert
        assert best_url == "high.jpg"

    def test_get_best_thumbnail_url_missing_preference_handling(self, youtube_service):
        """Test handling of thumbnails with missing preference values"""
        # Arrange - Thumbnails without preference field
        video_info = {
            "thumbnails": [
                {"url": "no_pref1.jpg"},  # No preference field
                {"url": "with_pref.jpg", "preference": 5},
                {"url": "no_pref2.jpg"}   # No preference field
            ]
        }
        
        # Act
        best_url = youtube_service._get_best_thumbnail_url(video_info)
        
        # Assert - Should handle missing preferences (defaults to -9999)
        assert best_url == "with_pref.jpg"

    def test_get_best_thumbnail_url_fallback_to_thumbnail_field(self, youtube_service):
        """Test fallback to thumbnail field when thumbnails array is empty"""
        # Arrange
        video_info = {
            "thumbnails": [],
            "thumbnail": "https://fallback-thumbnail.jpg"
        }
        
        # Act
        best_url = youtube_service._get_best_thumbnail_url(video_info)
        
        # Assert
        assert best_url == "https://fallback-thumbnail.jpg"

    def test_get_best_thumbnail_url_missing_thumbnail_handling(self, youtube_service):
        """Test missing thumbnail handling"""
        # Arrange
        video_info = {}  # No thumbnails at all
        
        # Act
        best_url = youtube_service._get_best_thumbnail_url(video_info)
        
        # Assert
        assert best_url is None

    def test_get_best_thumbnail_url_empty_thumbnails_array(self, youtube_service):
        """Test behavior with empty thumbnails array and no fallback"""
        # Arrange
        video_info = {"thumbnails": []}  # Empty array, no fallback
        
        # Act
        best_url = youtube_service._get_best_thumbnail_url(video_info)
        
        # Assert
        assert best_url is None

    @patch('app.services.file_management.download_image')
    def test_download_thumbnail_success_scenarios(self, mock_download_image, youtube_service):
        """Test _download_thumbnail() success scenarios"""
        # Arrange
        mock_download_image.return_value = True
        youtube_service.file_service.get_song_directory.return_value = Path("/test/song/dir")
        
        metadata = SongMetadata()
        song_id = "test-song-id"
        thumbnail_url = "https://example.com/thumbnail.jpg"
        
        # Act
        youtube_service._download_thumbnail(song_id, thumbnail_url, metadata)
        
        # Assert
        mock_download_image.assert_called_once_with(
            thumbnail_url, 
            Path("/test/song/dir/thumbnail.jpg")
        )
        assert metadata.thumbnail == "test-song-id/thumbnail.jpg"

    @patch('app.services.file_management.download_image')
    def test_download_thumbnail_failure_scenarios(self, mock_download_image, youtube_service):
        """Test _download_thumbnail() failure scenarios"""
        # Arrange
        mock_download_image.return_value = False  # Download fails
        youtube_service.file_service.get_song_directory.return_value = Path("/test/song/dir")
        
        metadata = SongMetadata()
        song_id = "test-song-id"
        thumbnail_url = "https://invalid-url.com/thumbnail.jpg"
        
        # Act - Should not raise exception
        youtube_service._download_thumbnail(song_id, thumbnail_url, metadata)
        
        # Assert - Metadata should not be updated on failure
        assert metadata.thumbnail is None

    @patch('app.services.file_management.download_image')
    def test_download_thumbnail_network_error_handling(self, mock_download_image, youtube_service):
        """Test _download_thumbnail() network error handling"""
        # Arrange
        mock_download_image.side_effect = Exception("Network timeout")
        youtube_service.file_service.get_song_directory.return_value = Path("/test/song/dir")
        
        metadata = SongMetadata()
        song_id = "test-song-id"
        thumbnail_url = "https://example.com/thumbnail.jpg"
        
        # Act - Should not raise exception for thumbnail failures
        youtube_service._download_thumbnail(song_id, thumbnail_url, metadata)
        
        # Assert - Should complete without error
        assert metadata.thumbnail is None

    @patch('app.services.file_management.download_image')
    def test_download_thumbnail_graceful_degradation(self, mock_download_image, youtube_service):
        """Test graceful degradation when thumbnail download fails"""
        # Arrange
        mock_download_image.side_effect = Exception("Disk full")
        youtube_service.file_service.get_song_directory.return_value = Path("/test/song/dir")
        
        metadata = SongMetadata()
        
        # Act - Should not raise exception for thumbnail failures
        youtube_service._download_thumbnail("song-id", "https://example.com/thumb.jpg", metadata)
        
        # Assert - Should complete without error
        assert metadata.thumbnail is None

    @patch('app.services.file_management.download_image')
    def test_download_thumbnail_file_service_integration(self, mock_download_image, youtube_service):
        """Test _download_thumbnail() FileService integration"""
        # Arrange
        mock_download_image.return_value = True
        expected_dir = Path("/custom/song/directory")
        youtube_service.file_service.get_song_directory.return_value = expected_dir
        
        metadata = SongMetadata()
        song_id = "integration-test-id"
        thumbnail_url = "https://example.com/test.jpg"
        
        # Act
        youtube_service._download_thumbnail(song_id, thumbnail_url, metadata)
        
        # Assert - FileService called correctly
        youtube_service.file_service.get_song_directory.assert_called_once_with(song_id)
        mock_download_image.assert_called_once_with(
            thumbnail_url,
            expected_dir / "thumbnail.jpg"
        )

    @patch('app.services.file_management.download_image')
    def test_download_thumbnail_metadata_update_pattern(self, mock_download_image, youtube_service):
        """Test metadata update pattern in _download_thumbnail()"""
        # Arrange
        mock_download_image.return_value = True
        youtube_service.file_service.get_song_directory.return_value = Path("/test/dir")
        
        metadata = SongMetadata(title="Test Song", artist="Test Artist")
        song_id = "metadata-test-id"
        
        # Act
        youtube_service._download_thumbnail(song_id, "https://thumb.jpg", metadata)
        
        # Assert - Only thumbnail field should be modified
        assert metadata.thumbnail == "metadata-test-id/thumbnail.jpg"
        assert metadata.title == "Test Song"  # Other fields unchanged
        assert metadata.artist == "Test Artist"

    @patch('app.services.file_management.download_image')
    def test_download_thumbnail_path_construction(self, mock_download_image, youtube_service):
        """Test thumbnail path construction"""
        # Arrange
        mock_download_image.return_value = True
        song_directory = Path("/custom/path/to/song")
        youtube_service.file_service.get_song_directory.return_value = song_directory
        
        metadata = SongMetadata()
        song_id = "path-test-id"
        
        # Act
        youtube_service._download_thumbnail(song_id, "https://example.jpg", metadata)
        
        # Assert - Check path construction
        expected_path = song_directory / "thumbnail.jpg"
        mock_download_image.assert_called_once_with("https://example.jpg", expected_path)
        
        # Metadata should use relative path format
        assert metadata.thumbnail == "path-test-id/thumbnail.jpg"

    def test_get_best_thumbnail_url_quality_preference_order(self, youtube_service):
        """Test that higher preference thumbnails are selected over lower ones"""
        # Arrange - Deliberately mixed order to test sorting
        video_info = {
            "thumbnails": [
                {"url": "medium.jpg", "preference": 5},
                {"url": "highest.jpg", "preference": 10},
                {"url": "lowest.jpg", "preference": 1},
                {"url": "high.jpg", "preference": 8}
            ]
        }
        
        # Act
        best_url = youtube_service._get_best_thumbnail_url(video_info)
        
        # Assert - Should select highest preference
        assert best_url == "highest.jpg"
