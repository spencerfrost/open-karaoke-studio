#!/usr/bin/env python3
"""
Quick test script to verify our new error handling system works
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.exceptions import *


def test_error_responses():
    """Test that our error handlers return proper JSON responses"""
    app = create_app()

    with app.test_client() as client:
        print("🧪 Testing Error Handling System")
        print("=" * 50)

        # Test 1: Valid request to see normal response
        print("\n1. Testing normal API response...")
        response = client.get("/api/songs")
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.content_type}")

        # Test 2: Invalid track type (should trigger our custom exception)
        print("\n2. Testing invalid track type error...")
        response = client.get("/api/songs/test-song-id/download/invalid_track")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.get_json()}")

        # Test 3: Non-existent song (should trigger ResourceNotFoundError)
        print("\n3. Testing non-existent song error...")
        response = client.get("/api/songs/nonexistent-song-id")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.get_json()}")

        # Test 4: Request validation - invalid JSON structure
        print("\n4. Testing request validation...")
        response = client.post(
            "/api/songs",
            json={"invalid": "data"},  # Missing required fields
            content_type="application/json",
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.get_json()}")

        # Test 5: Valid request creation
        print("\n5. Testing valid song creation...")
        response = client.post(
            "/api/songs",
            json={"title": "Test Song", "artist": "Test Artist"},
            content_type="application/json",
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 201:
            print("   ✅ Song created successfully")
        else:
            print(f"   Response: {response.get_json()}")

        # Test 6: YouTube validation
        print("\n6. Testing YouTube request validation...")
        response = client.post(
            "/api/youtube/download",
            json={"videoId": "test123"},  # Missing songId
            content_type="application/json",
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.get_json()}")

        print("\n✅ Error handling tests completed!")


if __name__ == "__main__":
    test_error_responses()
