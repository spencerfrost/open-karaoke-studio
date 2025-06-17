"""
Integration tests for the songs API endpoints in Open Karaoke Studio.
Updated to work with Song Service Layer.
"""

import pytest
import json
from unittest.mock import Mock, patch
from pathlib import Path

# Mock the imports that might not be available during testing
try:
    from app.api.songs import song_bp
    from app.db.models import DbSong, Song
    from app.services.song_service import SongService
    from app.exceptions import ServiceError, NotFoundError
except ImportError:
    song_bp = Mock()
    DbSong = Mock()
    Song = Mock()
    SongService = Mock()
    ServiceError = Exception
    NotFoundError = Exception


class TestSongsAPI:
    """Test the songs API endpoints with service layer integration"""
    
    @patch('app.api.songs.SongService')
    def test_get_songs_success(self, mock_song_service_class, client):
        """Test GET /api/songs endpoint success with service layer"""
        # Setup mock service
        mock_service = Mock()
        mock_song_service_class.return_value = mock_service
        
        # Mock service response
        mock_songs = [
            Mock(
                model_dump=Mock(return_value={
                    "id": "song-1",
                    "title": "Test Song 1",
                    "artist": "Test Artist 1",
                    "duration": 180,
                    "status": "processed"
                })
            ),
            Mock(
                model_dump=Mock(return_value={
                    "id": "song-2",
                    "title": "Test Song 2",
                    "artist": "Test Artist 2",
                    "duration": 200,
                    "status": "processed"
                })
            )
        ]
        mock_service.get_all_songs.return_value = mock_songs
        
        # Make request
        response = client.get('/api/songs')
        
        # Assertions
        assert response.status_code == 200
        mock_song_service_class.assert_called_once()
        mock_service.get_all_songs.assert_called_once()
        
        # Parse response data
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]['title'] == "Test Song 1"
        assert data[1]['title'] == "Test Song 2"
    
    @patch('app.api.songs.SongService')
    def test_get_songs_service_error(self, mock_song_service_class, client):
        """Test GET /api/songs when service raises ServiceError"""
        # Setup mock service to raise ServiceError
        mock_service = Mock()
        mock_song_service_class.return_value = mock_service
        mock_service.get_all_songs.side_effect = ServiceError("Service failed")
        
        # Make request
        response = client.get('/api/songs')
        
        # Assertions
        assert response.status_code == 500
        
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert 'error' in data
        assert 'Failed to fetch songs' in data['error']
        assert 'Service failed' in data['details']
    
    @patch('app.api.songs.SongService')
    def test_get_songs_unexpected_error(self, mock_song_service_class, client):
        """Test GET /api/songs when unexpected error occurs"""
        # Setup mock service to raise unexpected exception
        mock_service = Mock()
        mock_song_service_class.return_value = mock_service
        mock_service.get_all_songs.side_effect = Exception("Unexpected error")
        
        # Make request
        response = client.get('/api/songs')
        
        # Assertions
        assert response.status_code == 500
        
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert 'error' in data
        assert 'Internal server error' in data['error']
    
    @patch('app.api.songs.SongService')
    @patch('app.api.songs.get_song')  # Updated to mock the direct import
    def test_get_song_details_success(self, mock_get_song, mock_song_service_class, client):
        """Test GET /api/songs/<id> endpoint success with service layer"""
        # Setup mock service
        mock_service = Mock()
        mock_song_service_class.return_value = mock_service
        
        mock_song = Mock(
            model_dump=Mock(return_value={
                "id": "test-song-123",
                "title": "Test Song",
                "artist": "Test Artist",
                "duration": 180,
                "status": "processed"
            })
        )
        mock_service.get_song_by_id.return_value = mock_song
        
        # Mock database for legacy compatibility
        mock_db_song = Mock(
            album="Test Album",
            release_date="2023",
            genre="Test Genre",
            language="English",
            mbid="test-mbid",
            channel="Test Channel",
            source="test",
            source_url="http://test.com",
            lyrics="Test lyrics",
            synced_lyrics="Test synced lyrics",
            # iTunes metadata
            itunes_track_id=None,
            itunes_artist_id=None,
            itunes_collection_id=None,
            track_time_millis=None,
            itunes_explicit=False,
            itunes_preview_url=None,
            itunes_artwork_urls=None,
            # YouTube metadata
            youtube_duration=None,
            youtube_thumbnail_urls=None,
            youtube_tags=None,
            youtube_categories=None,
            youtube_channel_id=None,
            youtube_channel_name=None,
        )
        mock_get_song.return_value = mock_db_song
        
        # Make request
        response = client.get('/api/songs/test-song-123')
        
        # Assertions
        assert response.status_code == 200
        mock_service.get_song_by_id.assert_called_once_with("test-song-123")
        
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert data['id'] == "test-song-123"
        assert data['title'] == "Test Song"
        assert data['album'] == "Test Album"  # Added by legacy compatibility
    
    @patch('app.api.songs.SongService')
    def test_get_song_details_not_found(self, mock_song_service_class, client):
        """Test GET /api/songs/<id> when song not found with service layer"""
        # Setup mock service to return None
        mock_service = Mock()
        mock_song_service_class.return_value = mock_service
        mock_service.get_song_by_id.return_value = None
        
        # Make request
        response = client.get('/api/songs/nonexistent-song')
        
        # Assertions
        assert response.status_code == 404
        mock_service.get_song_by_id.assert_called_once_with("nonexistent-song")
        
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert 'error' in data
        assert 'not found' in data['error']
    
    @patch('app.api.songs.SongService')
    def test_get_song_details_service_error(self, mock_song_service_class, client):
        """Test GET /api/songs/<id> when service raises ServiceError"""
        # Setup mock service to raise ServiceError
        mock_service = Mock()
        mock_song_service_class.return_value = mock_service
        mock_service.get_song_by_id.side_effect = ServiceError("Service failed")
        
        # Make request
        response = client.get('/api/songs/test-song-123')
        
        # Assertions
        assert response.status_code == 500
        
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert 'error' in data
        assert 'Failed to fetch song' in data['error']
    
    @patch('app.api.songs.FileService')
    def test_download_song_track_success(self, mock_file_service_class, client):
        """Test GET /api/songs/<id>/download/<track_type> success"""
        # Setup FileService mock
        mock_file_service = Mock()
        mock_file_service_class.return_value = mock_file_service
        
        mock_song_dir = Path("/test/library/test-song")
        mock_file_service.get_song_directory.return_value = mock_song_dir
        
        with patch('pathlib.Path.is_dir', return_value=True):
            with patch('pathlib.Path.is_file', return_value=True):
                with patch('pathlib.Path.resolve') as mock_resolve:
                    # Mock path resolution for security check
                    mock_resolve.side_effect = lambda: Path("/test/library/test-song/vocals.mp3")
                    
                    with patch('flask.send_from_directory') as mock_send:
                        mock_send.return_value = Mock(status_code=200)
                        
                        response = client.get('/api/songs/test-song/download/vocals')
                        
                        # Should call FileService.get_song_directory
                        mock_file_service.get_song_directory.assert_called_once_with("test-song")
                        # Should call send_from_directory
                        mock_send.assert_called_once()
    
    def test_download_song_track_invalid_type(self, client):
        """Test download with invalid track type"""
        response = client.get('/api/songs/test-song/download/invalid')
        
        assert response.status_code == 400
        
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert 'error' in data
        assert 'Invalid track type' in data['error']
    
    @patch('app.api.songs.FileService')
    def test_download_song_track_song_not_found(self, mock_file_service_class, client):
        """Test download when song directory doesn't exist"""
        # Setup FileService mock
        mock_file_service = Mock()
        mock_file_service_class.return_value = mock_file_service
        
        mock_song_dir = Mock()
        mock_song_dir.is_dir.return_value = False
        mock_file_service.get_song_directory.return_value = mock_song_dir
        
        response = client.get('/api/songs/nonexistent/download/vocals')
        
        assert response.status_code == 404
        
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert 'error' in data
        assert 'Song not found' in data['error']
    
    @patch('app.api.songs.FileService')
    def test_download_song_track_file_not_found(self, mock_file_service_class, client):
        """Test download when track file doesn't exist"""
        # Setup FileService mock
        mock_file_service = Mock()
        mock_file_service_class.return_value = mock_file_service
        
        mock_song_dir = Mock()
        mock_song_dir.is_dir.return_value = True
        mock_song_dir.__truediv__ = Mock(return_value=Mock(is_file=Mock(return_value=False)))
        mock_file_service.get_song_directory.return_value = mock_song_dir
        
        response = client.get('/api/songs/test-song/download/vocals')
        
        assert response.status_code == 404
        
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert 'error' in data
        assert 'track not found' in data['error'].lower()
    
    @patch('app.api.songs.FileService')
    @patch('app.config.get_config')
    def test_download_song_track_security_violation(self, mock_get_config, mock_file_service_class, client):
        """Test download security check prevents path traversal"""
        # Setup mocks
        mock_config = Mock()
        mock_config.LIBRARY_DIR = Path("/test/library")
        mock_get_config.return_value = mock_config
        
        # Setup FileService mock
        mock_file_service = Mock()
        mock_file_service_class.return_value = mock_file_service
        
        mock_song_dir = Path("/test/library/test-song")
        mock_file_service.get_song_directory.return_value = mock_song_dir
        
        with patch('pathlib.Path.is_dir', return_value=True):
            with patch('pathlib.Path.is_file', return_value=True):
                with patch('pathlib.Path.resolve') as mock_resolve:
                    # Mock path resolution to simulate path traversal attempt
                    mock_resolve.side_effect = lambda: Path("/outside/library/malicious.mp3")
                    
                    response = client.get('/api/songs/test-song/download/vocals')
                    
                    assert response.status_code == 403
                    
                    if hasattr(response, 'get_json'):
                        data = response.get_json()
                    else:
                        data = json.loads(response.data.decode())
                    
                    assert 'error' in data
                    assert 'Access denied' in data['error']


class TestSongsAPISearch:
    """Test the songs search functionality"""
    
    @patch('app.api.songs.SongService')
    def test_search_songs_success(self, mock_song_service_class, client):
        """Test GET /api/songs/search endpoint success with service layer"""
        # Setup mock service
        mock_service = Mock()
        mock_song_service_class.return_value = mock_service
        
        mock_songs = [
            Mock(
                model_dump=Mock(return_value={
                    "id": "song-1",
                    "title": "Test Song",
                    "artist": "Test Artist",
                    "duration": 180,
                    "status": "processed"
                })
            )
        ]
        mock_service.search_songs.return_value = mock_songs
        
        # Make request with query parameter
        response = client.get('/api/songs/search?q=test')
        
        # Assertions
        assert response.status_code == 200
        mock_service.search_songs.assert_called_once_with('test')
        
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]['title'] == "Test Song"
    
    @patch('app.api.songs.SongService')
    def test_search_songs_empty_query(self, mock_song_service_class, client):
        """Test search endpoint with empty query returns empty list"""
        # Make request with empty query
        response = client.get('/api/songs/search?q=')
        
        # Assertions
        assert response.status_code == 200
        
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert data == []
        # Service should not be called for empty query
        mock_song_service_class.assert_not_called()
    
    @patch('app.api.songs.SongService')
    def test_search_songs_service_error(self, mock_song_service_class, client):
        """Test search endpoint when service raises ServiceError"""
        # Setup mock service to raise ServiceError
        mock_service = Mock()
        mock_song_service_class.return_value = mock_service
        mock_service.search_songs.side_effect = ServiceError("Search failed")
        
        # Make request
        response = client.get('/api/songs/search?q=test')
        
        # Assertions
        assert response.status_code == 500
        
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert 'error' in data
        assert 'Failed to search songs' in data['error']


class TestSongsAPIErrorHandling:
    """Test error handling in songs API"""
    
    def test_internal_server_error_handling(self, client):
        """Test that internal server errors are handled gracefully"""
        with patch('app.db.database.get_all_songs', side_effect=Exception("Unexpected error")):
            response = client.get('/api/songs')
            
            assert response.status_code == 500
            
            if hasattr(response, 'get_json'):
                data = response.get_json()
            else:
                data = json.loads(response.data.decode())
            
            assert 'error' in data
            # Should not expose internal error details
            assert 'Failed to fetch songs' in data['error']
    
    def test_malformed_request_handling(self, client):
        """Test handling of malformed requests"""
        # Test with invalid song ID characters
        response = client.get('/api/songs/../malicious')
        
        # Should handle invalid paths gracefully
        # Actual behavior depends on Flask routing and implementation
        assert response.status_code in [400, 404, 500]


    @patch('app.api.songs.SongService')
    @patch('app.api.songs.SongService')
    @patch('app.api.songs.FileService')
    def test_delete_song_success(self, mock_file_service_class, mock_song_service_class, client):
        """Test DELETE /api/songs/<id> endpoint success with service layer"""
        # Setup mock services
        mock_service = Mock()
        mock_song_service_class.return_value = mock_service
        mock_service.delete_song.return_value = True
        
        mock_file_service = Mock()
        mock_file_service_class.return_value = mock_file_service
        
        # Make request
        response = client.delete('/api/songs/test-song-123')
        
        # Assertions
        assert response.status_code == 200
        mock_service.delete_song.assert_called_once_with("test-song-123")
        mock_file_service.delete_song_files.assert_called_once_with("test-song-123")
        
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert 'message' in data
        assert 'deleted successfully' in data['message']
    
    @patch('app.api.songs.SongService')
    def test_delete_song_not_found(self, mock_song_service_class, client):
        """Test DELETE /api/songs/<id> when song not found with service layer"""
        # Setup mock service to return False (not found)
        mock_service = Mock()
        mock_song_service_class.return_value = mock_service
        mock_service.delete_song.return_value = False
        
        # Make request
        response = client.delete('/api/songs/nonexistent-song')
        
        # Assertions
        assert response.status_code == 404
        mock_service.delete_song.assert_called_once_with("nonexistent-song")
        
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert 'error' in data
        assert 'not found' in data['error']
    
    @patch('app.api.songs.SongService')
    def test_delete_song_service_error(self, mock_song_service_class, client):
        """Test DELETE /api/songs/<id> when service raises ServiceError"""
        # Setup mock service to raise ServiceError
        mock_service = Mock()
        mock_song_service_class.return_value = mock_service
        mock_service.delete_song.side_effect = ServiceError("Delete failed")
        
        # Make request
        response = client.delete('/api/songs/test-song-123')
        
        # Assertions
        assert response.status_code == 500
        
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert 'error' in data
        assert 'Failed to delete song' in data['error']
