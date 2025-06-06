# backend/tests/performance/test_metadata_performance.py
"""
Performance tests for Metadata Service
"""

import pytest
import time
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.metadata_service import MusicBrainzMetadataService


class TestMetadataServicePerformance:
    
    def setup_method(self):
        self.service = MusicBrainzMetadataService()
    
    @patch('app.services.metadata_service.search_musicbrainz')
    def test_search_response_time(self, mock_search):
        """Test that search responds within reasonable time"""
        # Mock a typical response
        mock_search.return_value = [
            {
                "mbid": "test-123",
                "title": "Test Song",
                "artist": "Test Artist",
                "release": {"title": "Test Album", "date": "2023-01-01"}
            }
        ]
        
        start_time = time.time()
        
        results = self.service.search_metadata(
            artist="Test Artist",
            title="Test Song"
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Should respond in under 100ms for mocked calls
        assert response_time < 0.1
        assert len(results) == 1
    
    @patch('app.services.metadata_service.search_musicbrainz')
    def test_format_large_result_set(self, mock_search):
        """Test formatting performance with large result sets"""
        # Create a large mock result set
        large_result_set = []
        for i in range(100):
            large_result_set.append({
                "mbid": f"test-{i}",
                "title": f"Test Song {i}",
                "artist": f"Test Artist {i}",
                "release": {
                    "title": f"Test Album {i}",
                    "date": f"202{i % 10}-01-01"
                },
                "genre": f"Genre {i}",
                "language": "English"
            })
        
        mock_search.return_value = large_result_set
        
        start_time = time.time()
        
        results = self.service.search_metadata(
            artist="Test Artist",
            title="Test Song",
            limit=100
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process 100 results in under 100ms
        assert processing_time < 0.1
        assert len(results) == 100
        
        # Verify all results are properly formatted
        for i, result in enumerate(results):
            assert result["musicbrainzId"] == f"test-{i}"
            assert result["title"] == f"Test Song {i}"
            assert result["artist"] == f"Test Artist {i}"
    
    @patch('app.services.metadata_service.search_musicbrainz')
    def test_concurrent_search_requests(self, mock_search):
        """Test concurrent search requests performance"""
        mock_search.return_value = [
            {
                "mbid": "test-123",
                "title": "Test Song",
                "artist": "Test Artist"
            }
        ]
        
        def search_task(i):
            return self.service.search_metadata(
                artist=f"Artist {i}",
                title=f"Song {i}"
            )
        
        start_time = time.time()
        
        # Run 10 concurrent searches
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(search_task, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All searches should complete reasonably quickly
        assert total_time < 1.0  # Under 1 second for 10 concurrent searches
        assert len(results) == 10
        
        # All results should be valid
        for result_set in results:
            assert len(result_set) == 1
            assert "musicbrainzId" in result_set[0]
    
    def test_memory_usage_with_large_results(self):
        """Test memory usage doesn't grow excessively with large result sets"""
        import tracemalloc
        
        tracemalloc.start()
        
        with patch('app.services.metadata_service.search_musicbrainz') as mock_search:
            # Create a very large result set
            large_result_set = []
            for i in range(1000):
                large_result_set.append({
                    "mbid": f"test-{i}" * 10,  # Make strings longer
                    "title": f"Very Long Test Song Title {i}" * 5,
                    "artist": f"Very Long Test Artist Name {i}" * 5,
                    "release": {
                        "title": f"Very Long Test Album Title {i}" * 5,
                        "date": f"202{i % 10}-01-01"
                    }
                })
            
            mock_search.return_value = large_result_set
            
            # Take initial memory snapshot
            snapshot1 = tracemalloc.take_snapshot()
            
            # Process the large result set
            results = self.service.search_metadata(
                artist="Test Artist",
                title="Test Song",
                limit=1000
            )
            
            # Take final memory snapshot
            snapshot2 = tracemalloc.take_snapshot()
            
            # Calculate memory difference
            top_stats = snapshot2.compare_to(snapshot1, 'lineno')
            total_memory_increase = sum(stat.size_diff for stat in top_stats)
            
            # Memory increase should be reasonable (less than 10MB for 1000 results)
            assert total_memory_increase < 10 * 1024 * 1024  # 10MB
            assert len(results) == 1000
        
        tracemalloc.stop()


# Mark tests as performance tests
pytestmark = pytest.mark.performance
