# backend/tests/unit/test_services/test_musicbrainz_service.py
"""
Unit tests for MusicBrainz Service functions
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.services.musicbrainz_service import (
    search_musicbrainz,
    enhance_metadata_with_musicbrainz,
    get_cover_art,
    _extract_genre,
    _extract_language,
    _get_cover_art_url,
    _extract_release_info
)


class TestSearchMusicbrainz:
    
    @patch('app.services.musicbrainz_service.musicbrainzngs.search_recordings')
    def test_search_with_all_parameters(self, mock_search):
        """Test search with artist, title, and album"""
        mock_search.return_value = {
            'recording-list': [
                {
                    'id': 'test-mbid-123',
                    'title': 'Test Song',
                    'artist-credit': [{'artist': {'name': 'Test Artist'}}],
                    'release-list': [
                        {
                            'id': 'release-123',
                            'title': 'Test Album',
                            'date': '2023-01-01'
                        }
                    ]
                }
            ]
        }
        
        results = search_musicbrainz("Test Artist", "Test Song", "Test Album", 5)
        
        assert len(results) == 1
        assert results[0]['mbid'] == 'test-mbid-123'
        assert results[0]['title'] == 'Test Song'
        assert results[0]['artist'] == 'Test Artist'
        
        # Verify query construction
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert 'artist:"Test Artist"' in call_args[1]['query']
        assert 'recording:"Test Song"' in call_args[1]['query']
        assert 'release:"Test Album"' in call_args[1]['query']
        assert call_args[1]['limit'] == 5
    
    @patch('app.services.musicbrainz_service.musicbrainzngs.search_recordings')
    def test_search_without_album(self, mock_search):
        """Test search without album parameter"""
        mock_search.return_value = {'recording-list': []}
        
        search_musicbrainz("Test Artist", "Test Song", "", 5)
        
        call_args = mock_search.call_args
        query = call_args[1]['query']
        assert 'artist:"Test Artist"' in query
        assert 'recording:"Test Song"' in query
        assert 'release:' not in query
    
    @patch('app.services.musicbrainz_service.musicbrainzngs.search_recordings')
    def test_search_empty_results(self, mock_search):
        """Test search returning empty results"""
        mock_search.return_value = {'recording-list': []}
        
        results = search_musicbrainz("Unknown Artist", "Unknown Song")
        
        assert results == []
    
    @patch('app.services.musicbrainz_service.musicbrainzngs.search_recordings')
    def test_search_no_recording_list(self, mock_search):
        """Test search with malformed response"""
        mock_search.return_value = {}
        
        results = search_musicbrainz("Test Artist", "Test Song")
        
        assert results == []
    
    @patch('app.services.musicbrainz_service.musicbrainzngs.search_recordings')
    def test_search_api_exception(self, mock_search):
        """Test search with MusicBrainz API exception"""
        mock_search.side_effect = Exception("MusicBrainz API error")
        
        results = search_musicbrainz("Test Artist", "Test Song")
        
        assert results == []
    
    @patch('app.services.musicbrainz_service.musicbrainzngs.search_recordings')
    def test_search_unicode_characters(self, mock_search):
        """Test search with unicode characters"""
        mock_search.return_value = {'recording-list': []}
        
        search_musicbrainz("Björk", "Café del Mar", "Ñoño")
        
        call_args = mock_search.call_args
        query = call_args[1]['query']
        assert 'artist:"Björk"' in query
        assert 'recording:"Café del Mar"' in query
        assert 'release:"Ñoño"' in query


class TestHelperFunctions:
    
    def test_extract_genre_with_tags(self):
        """Test genre extraction from tags"""
        recording = {
            'tag-list': [
                {'name': 'rock', 'count': 10},
                {'name': 'alternative', 'count': 5}
            ]
        }
        
        genre = _extract_genre(recording)
        assert genre == 'Rock'  # Should return most popular tag, capitalized
    
    def test_extract_genre_no_tags(self):
        """Test genre extraction with no tags"""
        recording = {}
        
        genre = _extract_genre(recording)
        assert genre is None
    
    def test_extract_language_with_attributes(self):
        """Test language extraction from tag list, not attributes"""
        recording = {
            'tag-list': [
                {'name': 'english', 'count': 5}
            ]
        }
        
        language = _extract_language(recording)
        assert language == 'English'
    
    def test_extract_language_no_attributes(self):
        """Test language extraction with no attributes"""
        recording = {}
        
        language = _extract_language(recording)
        assert language is None
    
    @patch('app.services.musicbrainz_service.musicbrainzngs.get_image_list')
    def test_get_cover_art_url_success(self, mock_get_image_list):
        """Test successful cover art URL retrieval"""
        mock_get_image_list.return_value = {
            'images': [
                {
                    'thumbnails': {'large': 'http://example.com/large.jpg'},
                    'image': 'http://example.com/full.jpg'
                }
            ]
        }
        
        url = _get_cover_art_url('test-release-123')
        assert url == 'http://example.com/large.jpg'
    
    @patch('app.services.musicbrainz_service.musicbrainzngs.get_image_list')
    def test_get_cover_art_url_no_large_thumbnail(self, mock_get_image_list):
        """Test cover art URL retrieval with no large thumbnail"""
        mock_get_image_list.return_value = {
            'images': [
                {
                    'front': True,
                    'thumbnails': {},  # No large thumbnail
                    'image': 'http://example.com/full.jpg'
                }
            ]
        }
        
        url = _get_cover_art_url('test-release-123')
        assert url == 'http://example.com/full.jpg'
    
    @patch('app.services.musicbrainz_service.musicbrainzngs.get_image_list')
    def test_get_cover_art_url_no_images(self, mock_get_image_list):
        """Test cover art URL retrieval with no images"""
        mock_get_image_list.return_value = {'images': []}
        
        url = _get_cover_art_url('test-release-123')
        assert url is None
    
    @patch('app.services.musicbrainz_service.musicbrainzngs.get_image_list')
    def test_get_cover_art_url_api_exception(self, mock_get_image_list):
        """Test cover art URL retrieval with API exception"""
        mock_get_image_list.side_effect = Exception("API error")
        
        url = _get_cover_art_url('test-release-123')
        assert url is None
    
    def test_extract_release_info_complete(self):
        """Test release info extraction with complete data"""
        recording = {
            'release-list': [
                {
                    'id': 'release-123',
                    'title': 'Test Album',
                    'date': '2023-01-01'
                }
            ]
        }
        
        release_info = _extract_release_info(recording)
        assert release_info == {
            'id': 'release-123',
            'title': 'Test Album',
            'date': '2023-01-01'
        }
    
    def test_extract_release_info_no_releases(self):
        """Test release info extraction with no releases"""
        recording = {}
        
        release_info = _extract_release_info(recording)
        assert release_info is None


class TestEnhanceMetadata:
    
    @patch('app.services.musicbrainz_service.search_musicbrainz')
    def test_enhance_metadata_success(self, mock_search):
        """Test successful metadata enhancement"""
        mock_search.return_value = [
            {
                'mbid': 'enhanced-mbid-123',
                'title': 'Enhanced Title',
                'artist': 'Enhanced Artist',
                'genre': 'Enhanced Genre'
            }
        ]
        
        original_metadata = {'title': 'Original Title', 'artist': 'Original Artist'}
        song_dir = Path('/test/path')
        
        enhanced = enhance_metadata_with_musicbrainz(original_metadata, song_dir)
        
        assert enhanced['mbid'] == 'enhanced-mbid-123'
        assert enhanced['title'] == 'Enhanced Title'
        assert enhanced['artist'] == 'Enhanced Artist'
        assert enhanced['genre'] == 'Enhanced Genre'
    
    @patch('app.services.musicbrainz_service.search_musicbrainz')
    def test_enhance_metadata_no_results(self, mock_search):
        """Test metadata enhancement with no search results"""
        mock_search.return_value = []
        
        original_metadata = {'title': 'Original Title', 'artist': 'Original Artist'}
        song_dir = Path('/test/path')
        
        enhanced = enhance_metadata_with_musicbrainz(original_metadata, song_dir)
        
        assert enhanced == original_metadata
    
    @patch('app.services.musicbrainz_service.search_musicbrainz')
    def test_enhance_metadata_exception(self, mock_search):
        """Test metadata enhancement with search exception"""
        mock_search.side_effect = Exception("Search failed")
        
        original_metadata = {'title': 'Original Title', 'artist': 'Original Artist'}
        song_dir = Path('/test/path')
        
        enhanced = enhance_metadata_with_musicbrainz(original_metadata, song_dir)
        
        assert enhanced == original_metadata


class TestGetCoverArt:
    
    @patch('app.services.musicbrainz_service.musicbrainzngs.get_image_list')
    @patch('app.services.musicbrainz_service.get_cover_art_path')
    @patch('app.services.musicbrainz_service.download_image')
    @patch('app.config.get_config')
    def test_get_cover_art_success(self, mock_get_config, mock_download, mock_get_path, mock_get_image_list):
        """Test successful cover art download"""
        mock_get_image_list.return_value = {
            'images': [
                {
                    'front': True,
                    'image': 'http://example.com/cover.jpg'
                }
            ]
        }
        mock_get_path.return_value = Path('/test/library/path/cover.jpg')
        mock_download.return_value = True
        
        # Mock the config
        mock_config = Mock()
        mock_config.LIBRARY_DIR = Path('/test/library')
        mock_get_config.return_value = mock_config
        
        result = get_cover_art('test-release-123', Path('/test/library/path'))
        
        assert result == 'path/cover.jpg'  # Relative path
        mock_get_path.assert_called_once_with(Path('/test/library/path'))
        mock_download.assert_called_once_with('http://example.com/cover.jpg', Path('/test/library/path/cover.jpg'))
    
    @patch('app.services.musicbrainz_service._get_cover_art_url')
    def test_get_cover_art_no_url(self, mock_get_url):
        """Test cover art download with no URL available"""
        mock_get_url.return_value = None
        
        result = get_cover_art('test-release-123', Path('/test/path'))
        
        assert result is None
    
    @patch('app.services.musicbrainz_service._get_cover_art_url')
    @patch('app.services.musicbrainz_service.get_cover_art_path')
    @patch('app.services.musicbrainz_service.download_image')
    def test_get_cover_art_download_fails(self, mock_download, mock_get_path, mock_get_url):
        """Test cover art download failure"""
        mock_get_url.return_value = 'http://example.com/cover.jpg'
        mock_get_path.return_value = '/test/path/cover.jpg'
        mock_download.return_value = False
        
        result = get_cover_art('test-release-123', Path('/test/path'))
        
        assert result is None
    
    @patch('app.services.musicbrainz_service._get_cover_art_url')
    @patch('app.services.musicbrainz_service.get_cover_art_path')
    @patch('app.services.musicbrainz_service.download_image')
    def test_get_cover_art_exception(self, mock_download, mock_get_path, mock_get_url):
        """Test cover art download with exception"""
        mock_get_url.return_value = 'http://example.com/cover.jpg'
        mock_get_path.return_value = '/test/path/cover.jpg'
        mock_download.side_effect = Exception("Download failed")
        
        result = get_cover_art('test-release-123', Path('/test/path'))
        
        assert result is None
