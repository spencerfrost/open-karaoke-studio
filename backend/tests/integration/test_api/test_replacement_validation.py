"""Integration tests for song replacement validation endpoints."""
import json
import uuid
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest


def _create_song(client, title="Test Song", artist="Test Artist", **kwargs):
    """Helper to create a test song."""
    resp = client.post("/api/songs", json={"title": title, "artist": artist, **kwargs})
    assert resp.status_code in (200, 201)
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/songs/{song_id}/validate-youtube-replacement
# ─────────────────────────────────────────────────────────────────────────────


def test_validate_youtube_replacement_song_not_found(client):
    """Should return 404 if song doesn't exist."""
    response = client.post(
        f"/api/songs/{uuid.uuid4()}/validate-youtube-replacement",
        json={"video_id": "dQw4w9WgXcQ", "title": "Test", "artist": "Test"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_validate_youtube_replacement_high_confidence_match(client):
    """Should return validated=true for high-confidence AcoustID match (≥ 0.9)."""
    song = _create_song(client, title="Original", artist="Original Artist")
    
    # Mock YouTube download and AcoustID lookup
    mock_candidates = [
        {
            "score": 0.95,
            "recordingId": "mbid-123",
            "title": "Matched Title",
            "artist": "Matched Artist",
        }
    ]
    
    with patch("app.services.youtube_service.YouTubeService.download_video"), \
         patch("app.services.acoustid_service.AcoustIdService.lookup_candidates", return_value=mock_candidates), \
         patch("pathlib.Path.exists", return_value=True):
        response = client.post(
            f"/api/songs/{song['id']}/validate-youtube-replacement",
            json={"video_id": "dQw4w9WgXcQ", "title": "New Title", "artist": "New Artist"},
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["validated"] is True
    assert data["acoustidStatus"] == "matched"
    assert data["acoustidScore"] == 0.95
    assert data["musicbrainzId"] == "mbid-123"
    assert data["title"] == "Matched Title"
    assert data["artist"] == "Matched Artist"
    assert "audioPath" in data
    assert "✓" in data["message"]


def test_validate_youtube_replacement_low_confidence_match(client):
    """Should return validated=false for low-confidence match (< 0.9)."""
    song = _create_song(client, title="Original", artist="Original Artist")
    
    mock_candidates = [
        {
            "score": 0.75,
            "recordingId": "mbid-456",
            "title": "Maybe Title",
            "artist": "Maybe Artist",
        }
    ]
    
    with patch("app.services.youtube_service.YouTubeService.download_video"), \
         patch("app.services.acoustid_service.AcoustIdService.lookup_candidates", return_value=mock_candidates), \
         patch("pathlib.Path.exists", return_value=True):
        response = client.post(
            f"/api/songs/{song['id']}/validate-youtube-replacement",
            json={"video_id": "dQw4w9WgXcQ"},
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["validated"] is False
    assert data["acoustidStatus"] == "matched"
    assert data["acoustidScore"] == 0.75
    assert "confidence too low" in data["message"].lower()


def test_validate_youtube_replacement_no_match(client):
    """Should return validated=false for no AcoustID match."""
    song = _create_song(client, title="Original", artist="Original Artist")
    
    with patch("app.services.youtube_service.YouTubeService.download_video"), \
         patch("app.services.acoustid_service.AcoustIdService.lookup_candidates", return_value=[]), \
         patch("pathlib.Path.exists", return_value=True):
        response = client.post(
            f"/api/songs/{song['id']}/validate-youtube-replacement",
            json={"video_id": "dQw4w9WgXcQ"},
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["validated"] is False
    assert data["acoustidStatus"] == "no_match"
    assert data["acoustidScore"] is None
    assert "no acoustid match" in data["message"].lower()


def test_validate_youtube_replacement_error_handling(client):
    """Should return 500 on AcoustID service errors."""
    song = _create_song(client, title="Original", artist="Original Artist")
    
    with patch("app.services.youtube_service.YouTubeService.download_video"), \
         patch("app.services.acoustid_service.AcoustIdService.lookup_candidates", side_effect=Exception("API error")):
        response = client.post(
            f"/api/songs/{song['id']}/validate-youtube-replacement",
            json={"video_id": "dQw4w9WgXcQ"},
        )
    
    assert response.status_code == 500
    assert "validation failed" in response.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/songs/{song_id}/validate-upload-replacement
# ─────────────────────────────────────────────────────────────────────────────


def test_validate_upload_replacement_song_not_found(client):
    """Should return 404 if song doesn't exist."""
    audio_data = BytesIO(b"fake mp3 data")
    response = client.post(
        f"/api/songs/{uuid.uuid4()}/validate-upload-replacement",
        data={"audio_file": ("test.mp3", audio_data, "audio/mp3")},
    )
    assert response.status_code == 404


def test_validate_upload_replacement_invalid_file_type(client):
    """Should return 400 for non-audio file."""
    song = _create_song(client, title="Original", artist="Original Artist")
    
    text_data = BytesIO(b"This is not audio")
    response = client.post(
        f"/api/songs/{song['id']}/validate-upload-replacement",
        data={"audio_file": ("test.txt", text_data, "text/plain")},
    )
    
    assert response.status_code == 400
    assert "audio" in response.json()["detail"].lower()


def test_validate_upload_replacement_high_confidence_match(client):
    """Should return validated=true for high-confidence match."""
    song = _create_song(client, title="Original", artist="Original Artist")
    
    mock_candidates = [
        {
            "score": 0.92,
            "recordingId": "mbid-789",
            "title": "Upload Match Title",
            "artist": "Upload Match Artist",
        }
    ]
    
    audio_data = BytesIO(b"fake mp3 audio data")
    
    with patch("app.services.acoustid_service.AcoustIdService.lookup_candidates", return_value=mock_candidates):
        response = client.post(
            f"/api/songs/{song['id']}/validate-upload-replacement",
            data={"audio_file": ("test.mp3", audio_data, "audio/mp3")},
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["validated"] is True
    assert data["acoustidStatus"] == "matched"
    assert data["acoustidScore"] == 0.92
    assert data["musicbrainzId"] == "mbid-789"
    assert data["title"] == "Upload Match Title"
    assert "✓" in data["message"]


def test_validate_upload_replacement_no_match(client):
    """Should return validated=false for no match."""
    song = _create_song(client, title="Original", artist="Original Artist")
    
    audio_data = BytesIO(b"fake mp3 audio data")
    
    with patch("app.services.acoustid_service.AcoustIdService.lookup_candidates", return_value=[]):
        response = client.post(
            f"/api/songs/{song['id']}/validate-upload-replacement",
            data={"audio_file": ("test.mp3", audio_data, "audio/mp3")},
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["validated"] is False
    assert data["acoustidStatus"] == "no_match"


def test_validate_upload_replacement_error_handling(client):
    """Should return 500 on service errors."""
    song = _create_song(client, title="Original", artist="Original Artist")
    
    audio_data = BytesIO(b"fake mp3 audio data")
    
    with patch("app.services.acoustid_service.AcoustIdService.lookup_candidates", side_effect=ValueError("Bad data")):
        response = client.post(
            f"/api/songs/{song['id']}/validate-upload-replacement",
            data={"audio_file": ("test.mp3", audio_data, "audio/mp3")},
        )
    
    assert response.status_code == 500


# ─────────────────────────────────────────────────────────────────────────────
# Helper Function Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_format_validation_message_matched_high_confidence():
    """Test message formatting for high-confidence matches."""
    from app.api.songs import _format_validation_message
    
    msg = _format_validation_message("matched", 0.95)
    assert "✓" in msg
    assert "95%" in msg or "0.95" in msg
    assert "high" in msg.lower()


def test_format_validation_message_matched_low_confidence():
    """Test message formatting for low-confidence matches."""
    from app.api.songs import _format_validation_message
    
    msg = _format_validation_message("matched", 0.65)
    assert "⚠" in msg
    assert "65%" in msg or "0.65" in msg or "confidence too low" in msg.lower()


def test_format_validation_message_no_match():
    """Test message formatting for no match."""
    from app.api.songs import _format_validation_message
    
    msg = _format_validation_message("no_match", None)
    assert "✗" in msg
    assert "no" in msg.lower() and "match" in msg.lower()


def test_format_validation_message_failed():
    """Test message formatting for failed fingerprinting."""
    from app.api.songs import _format_validation_message
    
    msg = _format_validation_message("failed", None)
    assert "✗" in msg
    assert "failed" in msg.lower()


def test_format_validation_message_unknown():
    """Test message formatting for unknown status."""
    from app.api.songs import _format_validation_message
    
    msg = _format_validation_message("unknown_status", None)
    assert "?" in msg
    assert "unknown" in msg.lower()
