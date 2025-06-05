"""
Integration tests for the songs API endpoints in Open Karaoke Studio.
"""

import pytest
import json
from unittest.mock import Mock, patch
from pathlib import Path

# Mock the imports that might not be available during testing
try:
    from app.api.songs import song_bp
    from app.db.models import DbSong
except ImportError:
    song_bp = Mock()
    DbSong = Mock()


class TestSongsAPI:
    """Test the songs API endpoints"""
    
    def test_get_songs_success(self, client):
        """Test GET /api/songs endpoint success"""
        # Mock database response
        mock_songs = [
            Mock(
                id="song-1",
                title="Test Song 1", 
                artist="Test Artist 1",
                duration=180,
                to_pydantic=Mock(return_value=Mock(
                    model_dump=Mock(return_value={
                        "id": "song-1",
                        "title": "Test Song 1",
                        "artist": "Test Artist 1",
                        "duration": 180,
                        "status": "processed"
                    })
                ))
            ),
            Mock(
                id="song-2",
                title="Test Song 2",
                artist="Test Artist 2", 
                duration=200,
                to_pydantic=Mock(return_value=Mock(
                    model_dump=Mock(return_value={
                        "id": "song-2",
                        "title": "Test Song 2",
                        "artist": "Test Artist 2",
                        "duration": 200,
                        "status": "processed"
                    })
                ))
            )
        ]
        
        with patch('app.db.database.get_all_songs', return_value=mock_songs):
            # Make request
            response = client.get('/api/songs')
            
            # Assertions
            assert response.status_code == 200
            
            # Parse response data
            if hasattr(response, 'get_json'):
                data = response.get_json()
            else:
                data = json.loads(response.data.decode())
            
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]['title'] == "Test Song 1"
            assert data[1]['title'] == "Test Song 2"
    
    def test_get_songs_empty_database_triggers_sync(self, client):
        """Test GET /api/songs when database is empty triggers filesystem sync"""
        with patch('app.db.database.get_all_songs') as mock_get_all:
            # First call returns empty, second call returns songs after sync
            mock_get_all.side_effect = [[], [Mock(
                to_pydantic=Mock(return_value=Mock(
                    model_dump=Mock(return_value={
                        "id": "synced-song",
                        "title": "Synced Song",
                        "artist": "Synced Artist",
                        "duration": 180
                    })
                ))
            )]]
            
            with patch('app.db.database.sync_songs_with_filesystem', return_value=1) as mock_sync:
                response = client.get('/api/songs')
                
                # Should call sync when database is empty
                mock_sync.assert_called_once()
                assert mock_get_all.call_count == 2
                
                # Should return synced songs
                if hasattr(response, 'get_json'):
                    data = response.get_json()
                else:
                    data = json.loads(response.data.decode())
                
                assert len(data) == 1
                assert data[0]['title'] == "Synced Song"
    
    def test_get_songs_database_error(self, client):
        """Test GET /api/songs when database error occurs"""
        with patch('app.db.database.get_all_songs', side_effect=Exception("Database error")):
            response = client.get('/api/songs')
            
            assert response.status_code == 500
            
            if hasattr(response, 'get_json'):
                data = response.get_json()
            else:
                data = json.loads(response.data.decode())
            
            assert 'error' in data
            assert 'Failed to fetch songs' in data['error']
    
    def test_get_song_details_success(self, client):
        """Test GET /api/songs/<id> endpoint success"""
        mock_song = Mock(
            id="test-song-123",
            title="Test Song",
            artist="Test Artist",
            duration=180,
            to_pydantic=Mock(return_value=Mock(
                model_dump=Mock(return_value={
                    "id": "test-song-123",
                    "title": "Test Song",
                    "artist": "Test Artist",
                    "duration": 180,
                    "status": "processed"
                })
            ))
        )
        
        with patch('app.db.database.get_song', return_value=mock_song):
            response = client.get('/api/songs/test-song-123')
            
            assert response.status_code == 200
            
            if hasattr(response, 'get_json'):
                data = response.get_json()
            else:
                data = json.loads(response.data.decode())
            
            assert data['id'] == "test-song-123"
            assert data['title'] == "Test Song"
    
    def test_get_song_details_not_found(self, client):
        """Test GET /api/songs/<id> when song not found"""
        with patch('app.db.database.get_song', return_value=None):
            response = client.get('/api/songs/nonexistent-song')
            
            assert response.status_code == 404
            
            if hasattr(response, 'get_json'):
                data = response.get_json()
            else:
                data = json.loads(response.data.decode())
            
            assert 'error' in data
    
    @patch('app.services.file_management.get_song_dir')
    @patch('app.config.get_config')
    def test_download_song_track_success(self, mock_get_config, mock_get_song_dir, client):
        """Test GET /api/songs/<id>/download/<track_type> success"""
        # Setup mocks
        mock_config = Mock()
        mock_config.LIBRARY_DIR = Path("/test/library")
        mock_get_config.return_value = mock_config
        
        mock_song_dir = Path("/test/library/test-song")
        mock_get_song_dir.return_value = mock_song_dir
        
        with patch('pathlib.Path.is_dir', return_value=True):
            with patch('pathlib.Path.is_file', return_value=True):
                with patch('pathlib.Path.resolve') as mock_resolve:
                    # Mock path resolution for security check
                    mock_resolve.side_effect = lambda: Path("/test/library/test-song/vocals.mp3")
                    
                    with patch('flask.send_from_directory') as mock_send:
                        mock_send.return_value = Mock(status_code=200)
                        
                        response = client.get('/api/songs/test-song/download/vocals')
                        
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
    
    @patch('app.services.file_management.get_song_dir')
    def test_download_song_track_song_not_found(self, mock_get_song_dir, client):
        """Test download when song directory doesn't exist"""
        mock_song_dir = Mock()
        mock_song_dir.is_dir.return_value = False
        mock_get_song_dir.return_value = mock_song_dir
        
        response = client.get('/api/songs/nonexistent/download/vocals')
        
        assert response.status_code == 404
        
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert 'error' in data
        assert 'Song not found' in data['error']
    
    @patch('app.services.file_management.get_song_dir') 
    def test_download_song_track_file_not_found(self, mock_get_song_dir, client):
        """Test download when track file doesn't exist"""
        mock_song_dir = Mock()
        mock_song_dir.is_dir.return_value = True
        mock_song_dir.__truediv__ = Mock(return_value=Mock(is_file=Mock(return_value=False)))
        mock_get_song_dir.return_value = mock_song_dir
        
        response = client.get('/api/songs/test-song/download/vocals')
        
        assert response.status_code == 404
        
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = json.loads(response.data.decode())
        
        assert 'error' in data
        assert 'track not found' in data['error'].lower()
    
    @patch('app.services.file_management.get_song_dir')
    @patch('app.config.get_config')
    def test_download_song_track_security_violation(self, mock_get_config, mock_get_song_dir, client):
        """Test download security check prevents path traversal"""
        # Setup mocks
        mock_config = Mock()
        mock_config.LIBRARY_DIR = Path("/test/library")
        mock_get_config.return_value = mock_config
        
        mock_song_dir = Path("/test/library/test-song")
        mock_get_song_dir.return_value = mock_song_dir
        
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
    
    def test_search_songs_success(self, client):
        """Test GET /api/songs/search endpoint success"""
        mock_songs = [
            Mock(
                to_pydantic=Mock(return_value=Mock(
                    model_dump=Mock(return_value={
                        "id": "song-1",
                        "title": "Test Song",
                        "artist": "Test Artist",
                        "duration": 180
                    })
                ))
            )
        ]
        
        with patch('app.db.database.search_songs', return_value=mock_songs):
            response = client.get('/api/songs/search?q=test')
            
            assert response.status_code == 200
            
            if hasattr(response, 'get_json'):
                data = response.get_json()
            else:
                data = json.loads(response.data.decode())
            
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]['title'] == "Test Song"
    
    def test_search_songs_no_query(self, client):
        """Test search without query parameter"""
        response = client.get('/api/songs/search')
        
        # Should handle missing query gracefully
        assert response.status_code in [400, 200]  # Depends on implementation
    
    def test_search_songs_empty_results(self, client):
        """Test search with no matching results"""
        with patch('app.db.database.search_songs', return_value=[]):
            response = client.get('/api/songs/search?q=nonexistent')
            
            assert response.status_code == 200
            
            if hasattr(response, 'get_json'):
                data = response.get_json()
            else:
                data = json.loads(response.data.decode())
            
            assert isinstance(data, list)
            assert len(data) == 0


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
