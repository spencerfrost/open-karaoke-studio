"""Unit tests for app/services/acoustid_service.py."""
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.repositories.song_repository import SongRepository
from app.services.acoustid_service import AcoustIdService


@pytest.fixture
def song_repo():
    repo = Mock(spec=SongRepository)
    return repo


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.ACOUSTID_API_KEY = "test-acoustid-key"
    return cfg


@pytest.fixture
def svc(song_repo):
    return AcoustIdService(song_repo=song_repo)


def test_no_api_key_marks_failed(svc, song_repo):
    cfg = MagicMock()
    cfg.ACOUSTID_API_KEY = ""
    with patch("app.services.acoustid_service.get_config", return_value=cfg):
        svc.fingerprint_and_identify("song-1", "/fake/path.mp3")
    song_repo.update.assert_called_once_with("song-1", acoustid_fingerprint_status="failed")


def test_no_results_marks_no_match(svc, song_repo, mock_config):
    with patch("app.services.acoustid_service.get_config", return_value=mock_config), \
         patch("app.services.acoustid_service.acoustid.match", return_value=iter([])):
        svc.fingerprint_and_identify("song-1", "/fake/path.mp3")
    song_repo.update.assert_called_once_with("song-1", acoustid_fingerprint_status="no_match")


def test_high_confidence_auto_corrects(svc, song_repo, mock_config):
    """Score >= 0.85 should auto-correct title and artist."""
    results = [(0.95, "mbid-abc", "Correct Title", "Correct Artist")]
    with patch("app.services.acoustid_service.get_config", return_value=mock_config), \
         patch("app.services.acoustid_service.acoustid.match", return_value=iter(results)):
        svc.fingerprint_and_identify("song-1", "/fake/path.mp3")
    song_repo.update.assert_called_once_with(
        "song-1",
        acoustid_score=0.95,
        musicbrainz_recording_id="mbid-abc",
        acoustid_fingerprint_status="matched",
        title="Correct Title",
        artist="Correct Artist",
    )


def test_low_confidence_no_auto_correct(svc, song_repo, mock_config):
    """Score < 0.85 should store match data but NOT overwrite title/artist."""
    results = [(0.60, "mbid-xyz", "Maybe Title", "Maybe Artist")]
    with patch("app.services.acoustid_service.get_config", return_value=mock_config), \
         patch("app.services.acoustid_service.acoustid.match", return_value=iter(results)):
        svc.fingerprint_and_identify("song-1", "/fake/path.mp3")
    call_kwargs = song_repo.update.call_args[1]
    assert call_kwargs["acoustid_fingerprint_status"] == "matched"
    assert call_kwargs["acoustid_score"] == 0.60
    assert "title" not in call_kwargs
    assert "artist" not in call_kwargs


def test_fingerprint_generation_error_marks_failed(svc, song_repo, mock_config):
    import acoustid

    with patch("app.services.acoustid_service.get_config", return_value=mock_config), \
         patch("app.services.acoustid_service.acoustid.match", side_effect=acoustid.FingerprintGenerationError("fpcalc missing")):
        svc.fingerprint_and_identify("song-1", "/fake/path.mp3")
    song_repo.update.assert_called_once_with("song-1", acoustid_fingerprint_status="failed")


def test_web_service_error_marks_failed(svc, song_repo, mock_config):
    import acoustid

    with patch("app.services.acoustid_service.get_config", return_value=mock_config), \
         patch("app.services.acoustid_service.acoustid.match", side_effect=acoustid.WebServiceError("timeout")):
        svc.fingerprint_and_identify("song-1", "/fake/path.mp3")
    song_repo.update.assert_called_once_with("song-1", acoustid_fingerprint_status="failed")


def test_unexpected_exception_marks_failed(svc, song_repo, mock_config):
    with patch("app.services.acoustid_service.get_config", return_value=mock_config), \
         patch("app.services.acoustid_service.acoustid.match", side_effect=RuntimeError("oops")):
        svc.fingerprint_and_identify("song-1", "/fake/path.mp3")
    song_repo.update.assert_called_once_with("song-1", acoustid_fingerprint_status="failed")


def test_picks_highest_score_from_multiple_results(svc, song_repo, mock_config):
    """When multiple results exist, pick the one with the highest score."""
    results = [
        (0.70, "mbid-low", "Low Match", "Artist A"),
        (0.92, "mbid-high", "High Match", "Artist B"),
        (0.50, "mbid-lowest", "Lowest Match", "Artist C"),
    ]
    with patch("app.services.acoustid_service.get_config", return_value=mock_config), \
         patch("app.services.acoustid_service.acoustid.match", return_value=iter(results)):
        svc.fingerprint_and_identify("song-1", "/fake/path.mp3")
    call_kwargs = song_repo.update.call_args[1]
    assert call_kwargs["musicbrainz_recording_id"] == "mbid-high"
    assert call_kwargs["title"] == "High Match"
