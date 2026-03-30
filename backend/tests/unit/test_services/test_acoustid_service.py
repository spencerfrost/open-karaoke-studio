"""Unit tests for app/services/acoustid_service.py."""
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.repositories.song_repository import SongRepository
from app.services.acoustid_service import AcoustIdService


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _raw_response(*recordings_per_score):
    """
    Build a mock AcoustID raw API response dict.

    Each argument is a (score, list_of_recording_dicts) tuple.
    Recording dicts should have: id, title, artists, releases.
    """
    results = []
    for score, recordings in recordings_per_score:
        results.append({"score": score, "recordings": recordings})
    return {"status": "ok", "results": results}


def _rec(mbid, title, artist, albums=None):
    """Shorthand for building a recording dict."""
    return {
        "id": mbid,
        "title": title,
        "artists": [{"name": artist}],
        "releases": [{"title": a} for a in (albums or [])],
    }


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def song_repo():
    return Mock(spec=SongRepository)


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.ACOUSTID_API_KEY = "test-acoustid-key"
    return cfg


@pytest.fixture
def svc(song_repo):
    return AcoustIdService(song_repo=song_repo)


# ─── Tests ────────────────────────────────────────────────────────────────────

def test_no_api_key_marks_failed(svc, song_repo):
    cfg = MagicMock()
    cfg.ACOUSTID_API_KEY = ""
    with patch("app.services.acoustid_service.get_config", return_value=cfg):
        svc.fingerprint_and_identify("song-1", "/fake/path.mp3")
    song_repo.update.assert_called_once_with("song-1", acoustid_fingerprint_status="failed")


def test_no_results_marks_no_match(svc, song_repo, mock_config):
    raw = {"status": "ok", "results": []}
    with patch("app.services.acoustid_service.get_config", return_value=mock_config), \
         patch("app.services.acoustid_service.acoustid.match", return_value=raw):
        svc.fingerprint_and_identify("song-1", "/fake/path.mp3")
    song_repo.update.assert_called_once_with("song-1", acoustid_fingerprint_status="no_match")


def test_high_confidence_auto_corrects(svc, song_repo, mock_config):
    """Single candidate at score >= 0.9 should auto-correct title and artist."""
    raw = _raw_response((0.95, [_rec("mbid-abc", "Correct Title", "Correct Artist")]))
    with patch("app.services.acoustid_service.get_config", return_value=mock_config), \
         patch("app.services.acoustid_service.acoustid.match", return_value=raw):
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
    """Score < 0.9 should store match data but NOT overwrite title/artist."""
    raw = _raw_response((0.60, [_rec("mbid-xyz", "Maybe Title", "Maybe Artist")]))
    with patch("app.services.acoustid_service.get_config", return_value=mock_config), \
         patch("app.services.acoustid_service.acoustid.match", return_value=raw):
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
    """When multiple results exist at different scores, pick the highest."""
    raw = _raw_response(
        (0.70, [_rec("mbid-low", "Low Match", "Artist A")]),
        (0.92, [_rec("mbid-high", "High Match", "Artist B")]),
        (0.50, [_rec("mbid-lowest", "Lowest Match", "Artist C")]),
    )
    with patch("app.services.acoustid_service.get_config", return_value=mock_config), \
         patch("app.services.acoustid_service.acoustid.match", return_value=raw):
        svc.fingerprint_and_identify("song-1", "/fake/path.mp3")
    call_kwargs = song_repo.update.call_args[1]
    assert call_kwargs["musicbrainz_recording_id"] == "mbid-high"
    assert call_kwargs["title"] == "High Match"


def test_tied_candidates_without_album_flagged_ambiguous(svc, song_repo, mock_config):
    """Multiple candidates tied at >= 0.9 with no album to break the tie → ambiguous."""
    mock_song = Mock()
    mock_song.album = None
    song_repo.fetch.return_value = mock_song

    raw = _raw_response((0.98, [
        _rec("mbid-a", "Title A", "Artist A"),
        _rec("mbid-b", "Title B", "Artist B"),
    ]))
    with patch("app.services.acoustid_service.get_config", return_value=mock_config), \
         patch("app.services.acoustid_service.acoustid.match", return_value=raw):
        svc.fingerprint_and_identify("song-1", "/fake/path.mp3")
    song_repo.update.assert_called_once_with(
        "song-1",
        acoustid_score=0.98,
        acoustid_fingerprint_status="ambiguous",
    )


def test_album_tiebreaker_resolves_to_correct_candidate(svc, song_repo, mock_config):
    """When album matches exactly one tied candidate, that candidate is auto-applied."""
    mock_song = Mock()
    mock_song.album = "O Brother, Where Art Thou?"
    song_repo.fetch.return_value = mock_song

    raw = _raw_response((0.98, [
        _rec("mbid-wrong", "16", "DJ Panin", albums=["Some Random Album"]),
        _rec("mbid-correct", "A Man of Constant Sorrow", "The Soggy Bottom Boys",
             albums=["O Brother, Where Art Thou? (Soundtrack from the Motion Picture)"]),
    ]))
    with patch("app.services.acoustid_service.get_config", return_value=mock_config), \
         patch("app.services.acoustid_service.acoustid.match", return_value=raw):
        svc.fingerprint_and_identify("song-1", "/fake/path.mp3")

    call_kwargs = song_repo.update.call_args[1]
    assert call_kwargs["acoustid_fingerprint_status"] == "matched"
    assert call_kwargs["title"] == "A Man of Constant Sorrow"
    assert call_kwargs["artist"] == "The Soggy Bottom Boys"
    assert call_kwargs["musicbrainz_recording_id"] == "mbid-correct"


def test_album_tiebreaker_ambiguous_when_multiple_album_matches(svc, song_repo, mock_config):
    """If album matches multiple candidates (e.g. compilation), still flag ambiguous."""
    mock_song = Mock()
    mock_song.album = "Greatest Hits"
    song_repo.fetch.return_value = mock_song

    raw = _raw_response((0.95, [
        _rec("mbid-a", "Song A", "Artist A", albums=["Greatest Hits"]),
        _rec("mbid-b", "Song B", "Artist B", albums=["Greatest Hits"]),
    ]))
    with patch("app.services.acoustid_service.get_config", return_value=mock_config), \
         patch("app.services.acoustid_service.acoustid.match", return_value=raw):
        svc.fingerprint_and_identify("song-1", "/fake/path.mp3")

    call_kwargs = song_repo.update.call_args[1]
    assert call_kwargs["acoustid_fingerprint_status"] == "ambiguous"
