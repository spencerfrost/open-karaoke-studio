"""
Test iTunes integration within YouTube service
Tests the iTunes metadata enhancement logic integrated into the YouTube download process.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from pathlib import Path

from app.services.youtube_service import YouTubeService
from app.db.models import SongMetadata


class TestYouTubeServiceiTunesIntegration:
    """Test iTunes metadata enhancement in YouTube service download_video method"""
    
    @pytest.fixture
    def youtube_service(self):
        """Create a YouTube service instance for testing"""
        with patch('app.services.youtube_service.FileService'):
            return YouTubeService()
    
    @pytest.fixture
    def mock_song_metadata(self):
        """Create a mock SongMetadata object"""
        metadata = SongMetadata(
            song_id="test-song-id",
            title="Test Song",
            artist="Test Artist", 
            duration=180,
            source="youtube",
            file_path="/path/to/song",
            added_date=datetime.now(timezone.utc)
        )
        return metadata
    
    @pytest.fixture  
    def mock_youtube_info(self):
        """Mock YouTube video info dict"""
        return {
            'id': 'test123',
            'title': 'Test Song by Test Artist',
            'duration': 180,
            'uploader': 'Test Artist',  # This becomes the extracted artist
            'channel': 'TestChannel',
            'description': 'A test song',
            'upload_date': '20230101',
            'webpage_url': 'https://youtube.com/watch?v=test123',
            'thumbnails': [
                {'url': 'https://example.com/thumb.jpg', 'width': 480, 'height': 360}
            ]
        }
    
    @pytest.fixture
    def enhanced_metadata_dict(self):
        """Enhanced metadata returned by iTunes service"""
        return {
            'artist': 'Test Artist',
            'title': 'Test Song',
            'album': 'Test Album',  # New from iTunes
            'genre': 'Pop',  # New from iTunes
            'duration': 180,
            'coverArt': 'path/to/cover.jpg',  # New from iTunes
            'releaseDate': '2023-01-01'  # New from iTunes
        }
    
    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    @patch('app.services.itunes_service.enhance_metadata_with_itunes')
    def test_download_video_with_itunes_enhancement_success(self, mock_enhance, mock_yt_dlp, youtube_service, mock_youtube_info, enhanced_metadata_dict):
        """Test successful iTunes enhancement during video download"""
        # Setup mocks
        mock_ydl_instance = Mock()
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = mock_youtube_info
        mock_ydl_instance.download.return_value = None
        
        # Mock iTunes enhancement to return enhanced data (different from input)
        mock_enhance.return_value = enhanced_metadata_dict
        
        # Mock file service operations and thumbnail downloading
        with patch.object(youtube_service, 'file_service') as mock_file_service, \
             patch.object(youtube_service, '_download_thumbnail') as mock_download_thumb:
            mock_file_service.create_song_directory.return_value = Path("/test/song/dir")
            
            # Call download_video
            song_id, metadata = youtube_service.download_video("https://youtube.com/watch?v=test123")
            
            # Verify iTunes enhancement was called with correct metadata dict
            mock_enhance.assert_called_once()
            call_args = mock_enhance.call_args[0]
            metadata_dict_arg = call_args[0]
            
            assert metadata_dict_arg['artist'] == 'Test Artist'
            assert metadata_dict_arg['title'] == 'Test Song by Test Artist'  # Updated expected title
            assert 'duration' in metadata_dict_arg
            
            # Verify metadata was enhanced with iTunes data
            assert metadata.genre == 'Pop'  # From iTunes
            assert metadata.coverArt == 'path/to/cover.jpg'  # From iTunes
            assert metadata.releaseDate == '2023-01-01'  # From iTunes
    
    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    @patch('app.services.itunes_service.enhance_metadata_with_itunes')
    def test_download_video_itunes_enhancement_no_change(self, mock_enhance, mock_yt_dlp, youtube_service, mock_youtube_info):
        """Test iTunes enhancement when no enhancement is available (returns same data)"""
        # Setup mocks
        mock_ydl_instance = Mock()
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = mock_youtube_info
        mock_ydl_instance.download.return_value = None
        
        # Mock iTunes enhancement to return same data (no enhancement)
        original_dict = {
            'artist': 'Test Artist',
            'title': 'Test Song by Test Artist',
            'album': None,
            'genre': None,
            'duration': 180
        }
        mock_enhance.return_value = original_dict
        
        # Mock file service operations and thumbnail downloading
        with patch.object(youtube_service, 'file_service') as mock_file_service, \
             patch.object(youtube_service, '_download_thumbnail') as mock_download_thumb:
            mock_file_service.create_song_directory.return_value = Path("/test/song/dir")
            
            # Call download_video
            song_id, metadata = youtube_service.download_video("https://youtube.com/watch?v=test123")
            
            # Verify iTunes enhancement was called
            mock_enhance.assert_called_once()
            
            # Verify metadata was not enhanced (no new fields added)
            assert metadata.genre is None  # Should remain None since no enhancement
            assert metadata.coverArt is None  # Should remain None
            assert metadata.releaseDate is None  # Should remain None
    
    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    @patch('app.services.itunes_service.enhance_metadata_with_itunes')
    def test_download_video_itunes_enhancement_exception(self, mock_enhance, mock_yt_dlp, youtube_service, mock_youtube_info):
        """Test iTunes enhancement exception handling during video download"""
        # Setup mocks
        mock_ydl_instance = Mock()
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = mock_youtube_info
        mock_ydl_instance.download.return_value = None
        
        # Mock iTunes enhancement to raise exception
        mock_enhance.side_effect = Exception("iTunes API error")
        
        # Mock file service operations and thumbnail downloading
        with patch.object(youtube_service, 'file_service') as mock_file_service, \
             patch.object(youtube_service, '_download_thumbnail') as mock_download_thumb:
            mock_file_service.create_song_directory.return_value = Path("/test/song/dir")
            
            # Call download_video - should not raise exception
            song_id, metadata = youtube_service.download_video("https://youtube.com/watch?v=test123")
            
            # Verify iTunes enhancement was attempted
            mock_enhance.assert_called_once()
            
            # Verify download completed successfully despite iTunes failure
            assert song_id is not None
            assert metadata is not None
            assert metadata.artist == 'Test Artist'  # Original metadata preserved
            assert metadata.title == 'Test Song by Test Artist'
    
    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    @patch('app.services.itunes_service.enhance_metadata_with_itunes')
    def test_download_video_with_manual_artist_title(self, mock_enhance, mock_yt_dlp, youtube_service, mock_youtube_info, enhanced_metadata_dict):
        """Test iTunes enhancement with manually provided artist and title"""
        # Setup mocks
        mock_ydl_instance = Mock()
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = mock_youtube_info
        mock_ydl_instance.download.return_value = None
        
        # Mock iTunes enhancement
        mock_enhance.return_value = enhanced_metadata_dict
        
        # Mock file service operations and thumbnail downloading
        with patch.object(youtube_service, 'file_service') as mock_file_service, \
             patch.object(youtube_service, '_download_thumbnail') as mock_download_thumb:
            mock_file_service.create_song_directory.return_value = Path("/test/song/dir")
            
            # Call download_video with manual artist and title
            song_id, metadata = youtube_service.download_video(
                "https://youtube.com/watch?v=test123",
                artist="Manual Artist",
                title="Manual Title"
            )
            
            # Verify iTunes enhancement was called with manual artist/title
            mock_enhance.assert_called_once()
            call_args = mock_enhance.call_args[0]
            metadata_dict_arg = call_args[0]
            
            assert metadata_dict_arg['artist'] == 'Manual Artist'
            assert metadata_dict_arg['title'] == 'Manual Title'
            
            # Verify final metadata uses manual values and iTunes enhancements
            assert metadata.artist == 'Manual Artist'
            assert metadata.title == 'Manual Title'
            assert metadata.genre == 'Pop'  # From iTunes enhancement
    
    @patch('app.services.youtube_service.yt_dlp.YoutubeDL')
    @patch('app.services.itunes_service.enhance_metadata_with_itunes')
    def test_itunes_enhancement_preserves_duration(self, mock_enhance, mock_yt_dlp, youtube_service, mock_youtube_info):
        """Test that YouTube video duration is preserved over iTunes track duration"""
        # Setup mocks
        mock_ydl_instance = Mock()
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = mock_youtube_info
        mock_ydl_instance.download.return_value = None
        
        # Mock iTunes enhancement with different duration
        enhanced_dict = {
            'artist': 'Test Artist',
            'title': 'Test Song',
            'album': 'Test Album',
            'genre': 'Pop',
            'duration': 200,  # Different from YouTube duration (180)
            'coverArt': 'path/to/cover.jpg',
            'releaseDate': '2023-01-01'
        }
        mock_enhance.return_value = enhanced_dict
        
        # Mock file service operations and thumbnail downloading
        with patch.object(youtube_service, 'file_service') as mock_file_service, \
             patch.object(youtube_service, '_download_thumbnail') as mock_download_thumb:
            mock_file_service.create_song_directory.return_value = Path("/test/song/dir")
            
            # Call download_video
            song_id, metadata = youtube_service.download_video("https://youtube.com/watch?v=test123")
            
            # Verify YouTube duration is preserved (not iTunes duration)
            assert metadata.duration == 180  # Original YouTube duration
            
            # But other iTunes fields are applied
            assert metadata.genre == 'Pop'
            assert metadata.coverArt == 'path/to/cover.jpg'
