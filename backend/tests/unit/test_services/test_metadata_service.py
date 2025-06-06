# backend/tests/unit/test_services/test_metadata_service.py
"""
Unit tests for Metadata Service
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from app.services.metadata_service import MusicBrainzMetadataService


class TestMusicBrainzMetadataService:
    
    def setup_method(self):
        self.service = MusicBrainzMetadataService()
    
    def test_search_metadata_validates_input(self):
        """Test that search_metadata validates input parameters"""
        with pytest.raises(ValueError, match="At least one search term"):
            self.service.search_metadata(artist='', title='')
    
    @patch('app.services.metadata_service.search_musicbrainz')
    def test_search_metadata_formats_results(self, mock_search):
        """Test that search_metadata properly formats MusicBrainz results"""
        # Mock the raw MusicBrainz response
        mock_search.return_value = [
            {
                "mbid": "test-mbid-123",
                "title": "Test Song",
                "artist": "Test Artist",
                "release": {
                    "title": "Test Album",
                    "date": "2023-01-01"
                },
                "genre": "Rock",
                "language": "English",
                "coverArtUrl": None
            }
        ]
        
        results = self.service.search_metadata(
            artist="Test Artist", 
            title="Test Song"
        )
        
        assert len(results) == 1
        result = results[0]
        assert result["musicbrainzId"] == "test-mbid-123"
        assert result["title"] == "Test Song"
        assert result["artist"] == "Test Artist"
        assert result["album"] == "Test Album"
        assert result["year"] == "2023-01-01"
        assert result["genre"] == "Rock"
        assert result["language"] == "English"
        assert result["coverArt"] is None
        
        # Verify the underlying service was called correctly
        mock_search.assert_called_once_with("Test Artist", "Test Song", "", 5)
    
    @patch('app.services.metadata_service.search_musicbrainz')
    def test_search_metadata_handles_empty_results(self, mock_search):
        """Test that search_metadata handles empty results gracefully"""
        mock_search.return_value = []
        
        results = self.service.search_metadata(
            artist="Unknown Artist", 
            title="Unknown Song"
        )
        
        assert results == []
    
    @patch('app.services.metadata_service.enhance_metadata_with_musicbrainz')
    def test_enhance_metadata_delegates_correctly(self, mock_enhance):
        """Test that enhance_metadata delegates to the underlying service"""
        mock_metadata = {"title": "Test Song", "artist": "Test Artist"}
        mock_song_dir = Path("/test/path")
        mock_enhanced = {"title": "Test Song", "artist": "Test Artist", "mbid": "123"}
        
        mock_enhance.return_value = mock_enhanced
        
        result = self.service.enhance_metadata(mock_metadata, mock_song_dir)
        
        assert result == mock_enhanced
        mock_enhance.assert_called_once_with(mock_metadata, mock_song_dir)
    
    @patch('app.services.metadata_service.get_cover_art')
    def test_get_cover_art_delegates_correctly(self, mock_get_cover_art):
        """Test that get_cover_art delegates to the underlying service"""
        mock_release_id = "test-release-123"
        mock_song_dir = Path("/test/path")
        mock_cover_path = "/test/path/cover.jpg"
        
        mock_get_cover_art.return_value = mock_cover_path
        
        result = self.service.get_cover_art(mock_release_id, mock_song_dir)
        
        assert result == mock_cover_path
        mock_get_cover_art.assert_called_once_with(mock_release_id, mock_song_dir)
    
    def test_format_search_result(self):
        """Test the internal _format_search_result method"""
        raw_result = {
            "mbid": "test-mbid-123",
            "title": "Test Song",
            "artist": "Test Artist",
            "release": {
                "title": "Test Album",
                "date": "2023-01-01"
            },
            "genre": "Rock",
            "language": "English",
            "coverArtUrl": "http://example.com/cover.jpg"
        }
        
        formatted = self.service._format_search_result(raw_result)
        
        expected = {
            "musicbrainzId": "test-mbid-123",
            "title": "Test Song", 
            "artist": "Test Artist",
            "album": "Test Album",
            "year": "2023-01-01",
            "genre": "Rock",
            "language": "English",
            "coverArt": "http://example.com/cover.jpg"
        }
        
        assert formatted == expected
    
    def test_format_search_result_handles_missing_fields(self):
        """Test that _format_search_result handles missing fields gracefully"""
        raw_result = {
            "mbid": "test-mbid-123",
            "title": "Test Song"
            # Missing other fields
        }
        
        formatted = self.service._format_search_result(raw_result)
        
        assert formatted["musicbrainzId"] == "test-mbid-123"
        assert formatted["title"] == "Test Song"
        assert formatted["artist"] is None
        assert formatted["album"] is None
        assert formatted["year"] is None
        assert formatted["genre"] is None
        assert formatted["language"] is None
        assert formatted["coverArt"] is None
