# backend/tests/unit/test_api/test_musicbrainz_endpoints.py
"""
Unit tests for MusicBrainz API endpoints
"""

import pytest
from unittest.mock import Mock, patch
from flask import Flask

from app.api.musicbrainz import mb_bp


@pytest.fixture
def app():
    """Create a test Flask app"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(mb_bp)
    return app


@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()


class TestMusicBrainzEndpoints:
    
    @patch('app.api.musicbrainz.metadata_service')
    def test_search_endpoint_success(self, mock_metadata_service, client):
        """Test successful metadata search"""
        mock_metadata_service.search_metadata.return_value = [
            {
                "musicbrainzId": "test-mbid-123",
                "title": "Test Song",
                "artist": "Test Artist",
                "album": "Test Album",
                "year": "2023-01-01",
                "genre": "Rock",
                "language": "English",
                "coverArt": None
            }
        ]
        
        response = client.get('/api/musicbrainz/search?artist=Test Artist&title=Test Song')
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Song"
        assert data[0]["artist"] == "Test Artist"
        
        # Verify service was called correctly
        mock_metadata_service.search_metadata.assert_called_once_with(
            artist="Test Artist",
            title="Test Song",
            album=""
        )
    
    @patch('app.api.musicbrainz.metadata_service')
    def test_search_endpoint_with_album(self, mock_metadata_service, client):
        """Test metadata search with album parameter"""
        mock_metadata_service.search_metadata.return_value = []
        
        response = client.get('/api/musicbrainz/search?artist=Test Artist&title=Test Song&album=Test Album')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data == []
        
        # Verify service was called with album parameter
        mock_metadata_service.search_metadata.assert_called_once_with(
            artist="Test Artist",
            title="Test Song",
            album="Test Album"
        )
    
    @patch('app.api.musicbrainz.metadata_service')
    def test_search_endpoint_empty_results(self, mock_metadata_service, client):
        """Test metadata search returning empty results"""
        mock_metadata_service.search_metadata.return_value = []
        
        response = client.get('/api/musicbrainz/search?artist=Unknown Artist&title=Unknown Song')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data == []
    
    @patch('app.api.musicbrainz.metadata_service')
    def test_search_endpoint_validation_error(self, mock_metadata_service, client):
        """Test metadata search with validation error"""
        mock_metadata_service.search_metadata.side_effect = ValueError("At least one search term (title or artist) is required")
        
        response = client.get('/api/musicbrainz/search')
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "At least one search term" in data["error"]
    
    @patch('app.api.musicbrainz.metadata_service')
    def test_search_endpoint_server_error(self, mock_metadata_service, client):
        """Test metadata search with internal server error"""
        mock_metadata_service.search_metadata.side_effect = Exception("Database connection failed")
        
        response = client.get('/api/musicbrainz/search?artist=Test Artist')
        
        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data
        assert "internal error occurred" in data["error"]
    
    def test_search_endpoint_only_artist(self, client):
        """Test metadata search with only artist parameter"""
        with patch('app.api.musicbrainz.metadata_service') as mock_service:
            mock_service.search_metadata.return_value = []
            
            response = client.get('/api/musicbrainz/search?artist=Test Artist')
            
            assert response.status_code == 200
            mock_service.search_metadata.assert_called_once_with(
                artist="Test Artist",
                title="",
                album=""
            )
    
    def test_search_endpoint_only_title(self, client):
        """Test metadata search with only title parameter"""
        with patch('app.api.musicbrainz.metadata_service') as mock_service:
            mock_service.search_metadata.return_value = []
            
            response = client.get('/api/musicbrainz/search?title=Test Song')
            
            assert response.status_code == 200
            mock_service.search_metadata.assert_called_once_with(
                artist="",
                title="Test Song",
                album=""
            )
