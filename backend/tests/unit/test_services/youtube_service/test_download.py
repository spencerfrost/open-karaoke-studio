"""
YouTube Download Functionality Tests

Tests for YouTube video download operations.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from app.exceptions import ServiceError, ValidationError


class TestDownloadVideo:
    """Test YouTube download functionality"""

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    @patch('pathlib.Path.exists')
    def test_download_video_successful_download(self, mock_exists, mock_ytdl, youtube_service, complete_youtube_info):
        """Test download_video() successful download"""
        # Arrange
        mock_exists.return_value = True
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = complete_youtube_info
        
        with patch.object(youtube_service, '_get_best_thumbnail_url', return_value=None):
            # Act
            song_id, metadata = youtube_service.download_video("dQw4w9WgXcQ")
            
            # Assert
            assert song_id is not None
            assert len(song_id) == 36  # UUID length
            assert metadata.title == "Rick Astley - Never Gonna Give You Up (Official Video)"
            assert metadata.artist == "Rick Astley"
            assert metadata.source == "youtube"

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    @patch('pathlib.Path.exists')
    def test_download_video_with_custom_song_id(self, mock_exists, mock_ytdl, youtube_service, complete_youtube_info):
        """Test download_video() with custom song ID"""
        # Arrange
        custom_song_id = "custom-song-123"
        mock_exists.return_value = True
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = complete_youtube_info
        
        with patch.object(youtube_service, '_get_best_thumbnail_url', return_value=None):
            # Act
            song_id, metadata = youtube_service.download_video("dQw4w9WgXcQ", song_id=custom_song_id)
            
            # Assert
            assert song_id == custom_song_id

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    @patch('pathlib.Path.exists')
    def test_download_video_with_url_input(self, mock_exists, mock_ytdl, youtube_service, complete_youtube_info):
        """Test download_video() with full URL input"""
        # Arrange
        mock_exists.return_value = True
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = complete_youtube_info
        
        with patch.object(youtube_service, '_get_best_thumbnail_url', return_value=None):
            # Act
            song_id, metadata = youtube_service.download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            
            # Assert
            assert metadata.sourceUrl == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    @patch('pathlib.Path.exists')
    def test_download_video_with_metadata_override(self, mock_exists, mock_ytdl, youtube_service, complete_youtube_info):
        """Test download_video() with manual metadata override"""
        # Arrange
        mock_exists.return_value = True
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = complete_youtube_info
        
        with patch.object(youtube_service, '_get_best_thumbnail_url', return_value=None):
            # Act
            song_id, metadata = youtube_service.download_video(
                "dQw4w9WgXcQ",
                artist="Custom Artist",
                title="Custom Title"
            )
            
            # Assert
            assert metadata.artist == "Custom Artist"
            assert metadata.title == "Custom Title"
            # YouTube-specific fields should remain unchanged
            assert metadata.uploader == "Rick Astley"
            assert metadata.videoTitle == complete_youtube_info["title"]

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    @patch('pathlib.Path.exists')
    def test_download_video_with_thumbnail_download(self, mock_exists, mock_ytdl, youtube_service, complete_youtube_info):
        """Test download_video() with thumbnail download"""
        # Arrange
        mock_exists.return_value = True
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = complete_youtube_info
        
        with patch.object(youtube_service, '_get_best_thumbnail_url', return_value="https://thumb.jpg") as mock_get_thumb, \
             patch.object(youtube_service, '_download_thumbnail') as mock_download_thumb:
            
            # Act
            song_id, metadata = youtube_service.download_video("dQw4w9WgXcQ")
            
            # Assert
            mock_get_thumb.assert_called_once_with(complete_youtube_info)
            mock_download_thumb.assert_called_once_with(song_id, "https://thumb.jpg", metadata)
    
    def test_download_video_invalid_url_error(self, youtube_service):
        """Test download_video() with invalid URLs that trigger ServiceError"""
        # Arrange - Mock validation to return True but video ID extraction to return None
        with patch.object(youtube_service, 'validate_video_url', return_value=True), \
             patch.object(youtube_service, 'get_video_id_from_url', return_value=None):

            # Act & Assert - Service wraps ValidationError in ServiceError
            with pytest.raises(ServiceError, match="Failed to download YouTube video: Could not extract video ID from URL"):
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
    def test_download_video_file_creation_failure(self, mock_ytdl, youtube_service, complete_youtube_info):
        """Test download_video() file creation failures"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = complete_youtube_info
        
        # Mock file doesn't exist after download
        with patch('pathlib.Path.exists', return_value=False):
            # Act & Assert
            with pytest.raises(ServiceError, match="Download completed but file not found"):
                youtube_service.download_video("dQw4w9WgXcQ")

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_download_video_missing_original_files(self, mock_ytdl, youtube_service, complete_youtube_info):
        """Test download_video() with missing original files"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = complete_youtube_info
        
        # Mock file service to return non-existent path
        youtube_service.file_service.get_original_path.return_value = Path("/nonexistent/path.mp3")
        
        with patch('pathlib.Path.exists', return_value=False):
            # Act & Assert
            with pytest.raises(ServiceError, match="Download completed but file not found"):
                youtube_service.download_video("dQw4w9WgXcQ")

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    @patch('pathlib.Path.exists')
    def test_download_video_ydl_options_configuration(self, mock_exists, mock_ytdl, youtube_service, complete_youtube_info):
        """Test download_video() configures yt-dlp options correctly"""
        # Arrange
        mock_exists.return_value = True
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = complete_youtube_info
        
        youtube_service.file_service.get_song_directory.return_value = Path("/test/dir")
        
        with patch.object(youtube_service, '_get_best_thumbnail_url', return_value=None):
            # Act
            youtube_service.download_video("dQw4w9WgXcQ")
            
            # Assert - Check yt-dlp was called with correct options
            mock_ytdl.assert_called_once()
            call_args = mock_ytdl.call_args[0][0]  # First positional argument (options dict)
            
            assert call_args["format"] == "bestaudio/best"
            assert call_args["outtmpl"] == "/test/dir/original.%(ext)s"
            assert call_args["writeinfojson"] is True
            assert call_args["noplaylist"] is True
            assert len(call_args["postprocessors"]) == 1
            assert call_args["postprocessors"][0]["key"] == "FFmpegExtractAudio"
            assert call_args["postprocessors"][0]["preferredcodec"] == "mp3"
            assert call_args["postprocessors"][0]["preferredquality"] == "320"

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    @patch('pathlib.Path.exists')
    def test_download_video_file_service_integration(self, mock_exists, mock_ytdl, youtube_service, complete_youtube_info):
        """Test download_video() FileService integration"""
        # Arrange
        mock_exists.return_value = True
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = complete_youtube_info
        
        with patch.object(youtube_service, '_get_best_thumbnail_url', return_value=None):
            # Act
            song_id, metadata = youtube_service.download_video("dQw4w9WgXcQ")
            
            # Assert - FileService methods called correctly
            youtube_service.file_service.get_song_directory.assert_called_with(song_id)
            youtube_service.file_service.get_original_path.assert_called_with(song_id, ".mp3")

    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    def test_download_video_null_video_info_error(self, mock_ytdl, youtube_service):
        """Test download_video() when yt-dlp returns None video info"""
        # Arrange
        mock_ydl_instance = Mock()
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = None  # No video info returned
        
        # Act & Assert
        with pytest.raises(ServiceError, match="Could not download video info"):
            youtube_service.download_video("dQw4w9WgXcQ")
