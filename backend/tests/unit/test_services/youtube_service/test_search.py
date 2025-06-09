"""
YouTube Search Functionality Tests

Tests for YouTube video search operations.
"""

import pytest
from unittest.mock import Mock, patch

from app.exceptions import ServiceError


class TestSearchVideos:
    """Test YouTube search functionality"""

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_successful_query(self, mock_ytdl, youtube_service, sample_search_response):
        """Test search_videos() with successful query"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_search_response
        
        # Act
        results = youtube_service.search_videos("Rick Astley Never Gonna Give You Up", max_results=2)
        
        # Assert
        assert len(results) == 2
        assert results[0]["id"] == "dQw4w9WgXcQ"
        assert results[0]["title"] == "Rick Astley - Never Gonna Give You Up"
        assert results[0]["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert results[0]["channel"] == "Rick Astley"
        assert results[0]["duration"] == 213

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_empty_results(self, mock_ytdl, youtube_service):
        """Test search_videos() with no search results"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = {"entries": []}
        
        # Act
        results = youtube_service.search_videos("nonexistent video query")
        
        # Assert
        assert results == []

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_max_results_parameter(self, mock_ytdl, youtube_service, sample_search_response):
        """Test search_videos() respects max_results parameter"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_search_response
        
        # Act
        results = youtube_service.search_videos("test query", max_results=1)
        
        # Assert
        mock_ydl_instance.extract_info.assert_called_once()
        call_args = mock_ydl_instance.extract_info.call_args[0]
        assert "ytsearch1:" in call_args[0]  # Should include max_results in search term

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_default_max_results(self, mock_ytdl, youtube_service, sample_search_response):
        """Test search_videos() uses default max_results when not specified"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_search_response
        
        # Act
        results = youtube_service.search_videos("test query")
        
        # Assert
        call_args = mock_ydl_instance.extract_info.call_args[0]
        assert "ytsearch10:" in call_args[0]  # Should use default max_results=10

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_field_mapping(self, mock_ytdl, youtube_service, sample_search_response):
        """Test search_videos() correctly maps response fields"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = sample_search_response
        
        # Act
        results = youtube_service.search_videos("test query")
        
        # Assert - Check field mapping
        result = results[0]
        entry = sample_search_response["entries"][0]
        
        assert result["id"] == entry["id"]
        assert result["title"] == entry["title"]
        assert result["channel"] == entry["channel"]
        assert result["channelId"] == entry["channel_id"]
        assert result["duration"] == entry["duration"]
        assert result["thumbnail"] == entry["thumbnails"][0]["url"]

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_missing_thumbnail_handling(self, mock_ytdl, youtube_service):
        """Test search_videos() handles missing thumbnails gracefully"""
        # Arrange
        response_no_thumbnails = {
            "entries": [{
                "id": "test123",
                "title": "Test Video",
                "channel": "Test Channel",
                "duration": 120,
                # No thumbnails field
            }]
        }
        
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = response_no_thumbnails
        
        # Act
        results = youtube_service.search_videos("test query")
        
        # Assert
        assert results[0]["thumbnail"] is None

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_channel_fallback_to_uploader(self, mock_ytdl, youtube_service):
        """Test search_videos() falls back to uploader when channel is missing"""
        # Arrange
        response_no_channel = {
            "entries": [{
                "id": "test123",
                "title": "Test Video",
                "uploader": "Test Uploader",
                "uploader_id": "uploader123",
                "duration": 120,
                # No channel field
            }]
        }
        
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = response_no_channel
        
        # Act
        results = youtube_service.search_videos("test query")
        
        # Assert
        assert results[0]["channel"] == "Test Uploader"
        assert results[0]["channelId"] == "uploader123"

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_error_handling(self, mock_ytdl, youtube_service):
        """Test search_videos() error handling"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.side_effect = Exception("Network error")
        
        # Act & Assert
        with pytest.raises(ServiceError, match="Failed to search YouTube"):
            youtube_service.search_videos("test query")

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_no_entries_field(self, mock_ytdl, youtube_service):
        """Test search_videos() when response has no entries field"""
        # Arrange
        response_no_entries = {}  # Missing entries field
        
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = response_no_entries
        
        # Act
        results = youtube_service.search_videos("test query")
        
        # Assert
        assert results == []

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_search_videos_ydl_options_configuration(self, mock_ytdl, youtube_service):
        """Test search_videos() configures yt-dlp options correctly"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = {"entries": []}
        
        # Act
        youtube_service.search_videos("test query")
        
        # Assert - Check yt-dlp was called with correct options
        mock_ytdl.assert_called_once()
        call_args = mock_ytdl.call_args[0][0]  # First positional argument (options dict)
        
        assert call_args["format"] == "bestaudio/best"
        assert call_args["quiet"] is True
        assert call_args["no_warnings"] is True
        assert call_args["extract_flat"] is True
        assert call_args["default_search"] == "ytsearch"
        assert call_args["noplaylist"] is True
