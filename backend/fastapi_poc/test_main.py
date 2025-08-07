"""
Test suite for FastAPI Proof of Concept

Run with: pytest test_main.py -v
"""

import json

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestBasicEndpoints:
    """Test basic API endpoints"""
    
    def test_root_endpoint(self):
        """Test the root endpoint returns basic info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "docs" in data

    def test_health_endpoint(self):
        """Test health check returns FastAPI info"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["framework"] == "fastapi"
        assert "response_time_ms" in data
        assert "timestamp" in data

    def test_get_songs(self):
        """Test getting songs list"""
        response = client.get("/api/songs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            song = data[0]
            assert "id" in song
            assert "artist" in song
            assert "title" in song

    def test_create_song(self):
        """Test creating a new song with validation"""
        song_data = {
            "artist": "Test Artist",
            "title": "Test Song",
            "video_id": "test123"
        }
        response = client.post("/api/songs", json=song_data)
        assert response.status_code == 200
        data = response.json()
        assert data["artist"] == song_data["artist"]
        assert data["title"] == song_data["title"]
        assert "id" in data

    def test_create_song_validation(self):
        """Test Pydantic validation on song creation"""
        # Missing required field
        invalid_data = {"artist": "Test Artist"}  # Missing title
        response = client.post("/api/songs", json=invalid_data)
        assert response.status_code == 422  # Validation error

    def test_start_audio_processing(self):
        """Test starting audio processing job"""
        job_data = {"song_id": "test-song-123"}
        response = client.post("/api/jobs/process-audio", json=job_data)
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "queued"

    def test_performance_test_endpoint(self):
        """Test performance comparison endpoint"""
        response = client.get("/api/performance-test")
        assert response.status_code == 200
        data = response.json()
        assert data["framework"] == "fastapi"
        assert "response_time_ms" in data
        assert data["async_capable"] is True

class TestWebSockets:
    """Test WebSocket endpoints"""
    
    def test_websocket_jobs(self):
        """Test jobs WebSocket connection and messaging"""
        with client.websocket_connect("/ws/jobs") as websocket:
            # Should receive initial jobs list
            data = websocket.receive_text()
            message = json.loads(data)
            assert message["type"] == "jobs_list"
            assert "jobs" in message
            
            # Test subscription
            websocket.send_text(json.dumps({"type": "subscribe_to_jobs"}))
            data = websocket.receive_text()
            message = json.loads(data)
            assert message["type"] == "subscribed"

    def test_websocket_performance(self):
        """Test performance controls WebSocket"""
        with client.websocket_connect("/ws/performance") as websocket:
            # Should receive initial state
            data = websocket.receive_text()
            message = json.loads(data)
            assert message["type"] == "state_update"
            assert "state" in message
            
            # Test state update
            update_data = {
                "type": "update_controls",
                "data": {"vocal_volume": 0.5}
            }
            websocket.send_text(json.dumps(update_data))
            
            # Should receive broadcast of updated state
            data = websocket.receive_text()
            message = json.loads(data)
            assert message["type"] == "state_update"
            assert message["state"]["vocal_volume"] == 0.5

class TestErrorHandling:
    """Test error handling"""
    
    def test_404_handler(self):
        """Test custom 404 error handler"""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "Not found"
        assert data["framework"] == "fastapi"

class TestPerformanceComparison:
    """Test performance against Flask equivalent"""
    
    def test_response_times(self):
        """Compare response times with Flask"""
        import time

        # Time multiple requests to get average
        times = []
        for _ in range(10):
            start = time.time()
            response = client.get("/api/health")
            end = time.time()
            assert response.status_code == 200
            times.append((end - start) * 1000)  # Convert to ms
        
        avg_time = sum(times) / len(times)
        print(f"\nFastAPI average response time: {avg_time:.2f}ms")
        
        # FastAPI should be faster than 100ms on average
        assert avg_time < 100

    def test_concurrent_requests(self):
        """Test handling concurrent requests"""
        import threading
        import time
        
        results = []
        
        def make_request():
            start = time.time()
            response = client.get("/api/performance-test")
            end = time.time()
            results.append({
                "status": response.status_code,
                "time": (end - start) * 1000
            })
        
        # Create 20 concurrent requests
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # All should succeed
        assert len(results) == 20
        assert all(r["status"] == 200 for r in results)
        
        # Average time should still be reasonable
        avg_time = sum(r["time"] for r in results) / len(results)
        print(f"\nConcurrent requests average time: {avg_time:.2f}ms")
        assert avg_time < 200  # Should handle concurrency well

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
