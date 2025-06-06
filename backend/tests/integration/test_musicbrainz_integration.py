# backend/tests/integration/test_musicbrainz_integration.py
"""
Integration tests for MusicBrainz service with real API calls
These tests make actual calls to the MusicBrainz API and should be run sparingly
to avoid rate limiting. They serve as end-to-end validation of the integration.
"""

import pytest
from pathlib import Path
import tempfile
import os

from app.services.musicbrainz_service import search_musicbrainz, get_cover_art
from app.services.metadata_service import MusicBrainzMetadataService


class TestMusicBrainzIntegration:
    """Integration tests with real MusicBrainz API calls"""
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_search_well_known_song(self):
        """Test search for a well-known song with real API"""
        results = search_musicbrainz("The Beatles", "Yesterday", "", 1)
        
        assert len(results) > 0
        result = results[0]
        assert result['title'].lower() == 'yesterday'
        assert 'beatles' in result['artist'].lower()
        assert result['mbid'] is not None
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_search_with_album_filter(self):
        """Test search with album filter using real API"""
        # Test album filtering actually works
        results_with_album = search_musicbrainz("The Beatles", "Yesterday", "Help!", 5)
        results_without_album = search_musicbrainz("The Beatles", "Yesterday", "", 5)
        
        # Both should return results but potentially different ones
        assert len(results_with_album) > 0
        assert len(results_without_album) > 0
        
        # The album-specific search should prioritize the Help! album
        help_results = [r for r in results_with_album if r.get('release', {}).get('title') == 'Help!']
        assert len(help_results) > 0
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_search_unicode_artist(self):
        """Test search with unicode characters using real API"""
        results = search_musicbrainz("Björk", "Hyperballad", "", 1)
        
        assert len(results) > 0
        result = results[0]
        assert 'björk' in result['artist'].lower()
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_search_no_results(self):
        """Test search that should return no results"""
        results = search_musicbrainz("NonexistentArtist12345", "NonexistentSong12345", "", 5)
        
        assert results == []
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_metadata_service_integration(self):
        """Test the full metadata service with real API"""
        service = MusicBrainzMetadataService()
        
        results = service.search_metadata(
            artist="The Beatles",
            title="Yesterday",
            limit=1
        )
        
        assert len(results) > 0
        result = results[0]
        assert result['title'].lower() == 'yesterday'
        assert 'beatles' in result['artist'].lower()
        assert result['musicbrainzId'] is not None
        assert 'album' in result
        assert 'year' in result
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_cover_art_download_integration(self):
        """Test cover art download with real API"""
        # First search for a song to get a release ID
        results = search_musicbrainz("The Beatles", "Abbey Road", "Abbey Road", 1)
        if not results or not results[0].get('release', {}).get('id'):
            pytest.skip("Could not find release ID for test")
        
        release_id = results[0]['release']['id']
        
        with tempfile.TemporaryDirectory() as temp_dir:
            song_dir = Path(temp_dir)
            cover_path = get_cover_art(release_id, song_dir)
            
            if cover_path:  # Cover art might not be available for all releases
                assert os.path.exists(cover_path)
                assert os.path.getsize(cover_path) > 0
                assert cover_path.endswith(('.jpg', '.jpeg', '.png'))


class TestMusicBrainzRateLimiting:
    """Test rate limiting and error handling"""
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_multiple_requests_dont_fail(self):
        """Test that multiple requests in succession don't hit rate limits"""
        artists = ["The Beatles", "Pink Floyd", "Led Zeppelin"]
        
        all_successful = True
        for artist in artists:
            try:
                results = search_musicbrainz(artist, "", "", 1)
                # Just ensure we get some kind of response, not necessarily results
                assert isinstance(results, list)
            except Exception as e:
                print(f"Request failed for {artist}: {e}")
                all_successful = False
        
        # We expect at least most requests to succeed
        assert all_successful, "Too many requests failed, possible rate limiting"


# Markers for pytest to control test execution
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow
]
