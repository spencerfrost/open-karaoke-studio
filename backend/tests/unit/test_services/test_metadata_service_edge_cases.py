# backend/tests/unit/test_services/test_metadata_service_edge_cases.py
"""
Edge case tests for Metadata Service
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from app.services.metadata_service import MusicBrainzMetadataService


class TestMetadataServiceEdgeCases:
    
    def setup_method(self):
        self.service = MusicBrainzMetadataService()
    
    @patch('app.services.metadata_service.search_musicbrainz')
    def test_search_with_limit_parameter(self, mock_search):
        """Test that limit parameter is passed correctly"""
        mock_search.return_value = []
        
        self.service.search_metadata(
            artist="Test Artist", 
            title="Test Song",
            limit=10
        )
        
        mock_search.assert_called_once_with("Test Artist", "Test Song", "", 10)
    
    @patch('app.services.metadata_service.search_musicbrainz')
    def test_search_with_empty_strings(self, mock_search):
        """Test search with empty strings for parameters"""
        mock_search.return_value = []
        
        # Should raise ValueError due to validation
        with pytest.raises(ValueError, match="At least one search term"):
            self.service.search_metadata(artist="", title="", album="")
    
    @patch('app.services.metadata_service.search_musicbrainz')
    def test_search_with_whitespace_strings(self, mock_search):
        """Test search with whitespace-only strings"""
        mock_search.return_value = []
        
        # Whitespace should be treated as empty
        with pytest.raises(ValueError, match="At least one search term"):
            self.service.search_metadata(artist="   ", title="   ")
    
    @patch('app.services.metadata_service.search_musicbrainz')
    def test_search_strips_whitespace(self, mock_search):
        """Test that input parameters are stripped of whitespace"""
        mock_search.return_value = []
        
        self.service.search_metadata(
            artist="  Test Artist  ",
            title="  Test Song  ",
            album="  Test Album  "
        )
        
        mock_search.assert_called_once_with("Test Artist", "Test Song", "Test Album", 5)
    
    @patch('app.services.metadata_service.search_musicbrainz')
    def test_search_handles_search_exception(self, mock_search):
        """Test that search exceptions are properly propagated"""
        mock_search.side_effect = Exception("MusicBrainz API error")
        
        with pytest.raises(Exception, match="MusicBrainz API error"):
            self.service.search_metadata(artist="Test Artist", title="Test Song")
    
    @patch('app.services.metadata_service.search_musicbrainz')
    def test_search_handles_malformed_results(self, mock_search):
        """Test handling of malformed search results"""
        # Test with various malformed results
        malformed_results = [
            None,  # None result
            {"incomplete": "data"},  # Missing required fields
            {"mbid": None, "title": None},  # Null values
            {},  # Empty dict
        ]
        
        mock_search.return_value = malformed_results
        
        results = self.service.search_metadata(artist="Test Artist", title="Test Song")
        
        assert len(results) == 4
        # All results should be properly formatted even with missing data
        for result in results:
            assert "musicbrainzId" in result
            assert "title" in result
            assert "artist" in result
            assert "album" in result
            assert "year" in result
            assert "genre" in result
            assert "language" in result
            assert "coverArt" in result
    
    def test_format_search_result_nested_missing_data(self):
        """Test formatting with deeply nested missing data"""
        # Test with missing nested release data
        raw_result = {
            "mbid": "test-123",
            "title": "Test Song",
            "release": {}  # Empty release object
        }
        
        formatted = self.service._format_search_result(raw_result)
        
        assert formatted["album"] is None
        assert formatted["year"] is None
    
    def test_format_search_result_with_none_values(self):
        """Test formatting with explicit None values"""
        raw_result = {
            "mbid": None,
            "title": None,
            "artist": None,
            "release": None,
            "genre": None,
            "language": None,
            "coverArtUrl": None
        }
        
        formatted = self.service._format_search_result(raw_result)
        
        # All values should be None (not cause exceptions)
        for key, value in formatted.items():
            assert value is None
    
    @patch('app.services.metadata_service.enhance_metadata_with_musicbrainz')
    def test_enhance_metadata_preserves_original_on_exception(self, mock_enhance):
        """Test that enhance_metadata preserves original data on exception"""
        mock_enhance.side_effect = Exception("Enhancement failed")
        
        original_metadata = {"title": "Test", "artist": "Test Artist"}
        result = self.service.enhance_metadata(original_metadata, Path("/test"))
        
        # Should return original metadata on error
        assert result == original_metadata
    
    @patch('app.services.metadata_service.get_cover_art')
    def test_get_cover_art_returns_none_on_exception(self, mock_get_cover_art):
        """Test that get_cover_art returns None on exception"""
        mock_get_cover_art.side_effect = Exception("Cover art failed")
        
        result = self.service.get_cover_art("test-release", Path("/test"))
        
        assert result is None
    
    def test_format_search_result_unicode_handling(self):
        """Test formatting with unicode characters"""
        raw_result = {
            "mbid": "test-123",
            "title": "Café del Mar",
            "artist": "Björk",
            "release": {
                "title": "Ñoño Album",
                "date": "2023-01-01"
            },
            "genre": "Música Popular",
            "language": "Español"
        }
        
        formatted = self.service._format_search_result(raw_result)
        
        assert formatted["title"] == "Café del Mar"
        assert formatted["artist"] == "Björk"
        assert formatted["album"] == "Ñoño Album"
        assert formatted["genre"] == "Música Popular"
        assert formatted["language"] == "Español"
    
    @patch('app.services.metadata_service.search_musicbrainz')
    def test_search_large_limit(self, mock_search):
        """Test search with very large limit"""
        mock_search.return_value = []
        
        self.service.search_metadata(
            artist="Test Artist",
            title="Test Song",
            limit=100
        )
        
        mock_search.assert_called_once_with("Test Artist", "Test Song", "", 100)
    
    @patch('app.services.metadata_service.search_musicbrainz')
    def test_search_zero_limit(self, mock_search):
        """Test search with zero limit"""
        mock_search.return_value = []
        
        self.service.search_metadata(
            artist="Test Artist",
            title="Test Song",
            limit=0
        )
        
        mock_search.assert_called_once_with("Test Artist", "Test Song", "", 0)
    
    @patch('app.services.metadata_service.search_musicbrainz')
    def test_search_negative_limit(self, mock_search):
        """Test search with negative limit"""
        mock_search.return_value = []
        
        self.service.search_metadata(
            artist="Test Artist",
            title="Test Song",
            limit=-1
        )
        
        mock_search.assert_called_once_with("Test Artist", "Test Song", "", -1)
