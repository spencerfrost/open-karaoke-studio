"""Tests for the fingerprint_single_song Celery task."""
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest

from app.jobs.jobs import fingerprint_single_song


SONG_ID = "song-abc-123"
FAKE_LIB = "/fake/lib"


def _make_db_context(mock_session=None):
    """Return a mock for get_db_session used as a context manager."""
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=mock_session or MagicMock())
    ctx.__exit__ = Mock(return_value=False)
    return ctx


@patch("app.config.get_config", return_value=Mock(BASE_LIBRARY_DIR=FAKE_LIB))
@patch("app.repositories.song_repository.SongRepository")
@patch("app.services.acoustid_service.AcoustIdService")
@patch("app.db.database.get_db_session")
class TestFingerprintSingleSong:
    def test_uses_instrumental_when_exists(
        self, mock_get_db, mock_acoustid_cls, mock_repo_cls, mock_config
    ):
        mock_session = MagicMock()
        mock_get_db.return_value = _make_db_context(mock_session)

        with patch.object(Path, "exists", side_effect=[True, False]):
            result = fingerprint_single_song(SONG_ID)

        assert result == {"status": "ok", "song_id": SONG_ID}
        mock_acoustid_cls.return_value.fingerprint_and_identify.assert_called_once()
        args = mock_acoustid_cls.return_value.fingerprint_and_identify.call_args[0]
        assert args[0] == SONG_ID
        assert str(args[1]).endswith("instrumental.mp3")

    def test_uses_vocals_when_instrumental_missing(
        self, mock_get_db, mock_acoustid_cls, mock_repo_cls, mock_config
    ):
        mock_session = MagicMock()
        mock_get_db.return_value = _make_db_context(mock_session)

        with patch.object(Path, "exists", side_effect=[False, True]):
            result = fingerprint_single_song(SONG_ID)

        assert result == {"status": "ok", "song_id": SONG_ID}
        args = mock_acoustid_cls.return_value.fingerprint_and_identify.call_args[0]
        assert str(args[1]).endswith("vocals.mp3")

    def test_no_audio_updates_status_and_returns_no_audio(
        self, mock_get_db, mock_acoustid_cls, mock_repo_cls, mock_config
    ):
        mock_session = MagicMock()
        mock_get_db.return_value = _make_db_context(mock_session)

        with patch.object(Path, "exists", return_value=False):
            result = fingerprint_single_song(SONG_ID)

        assert result == {"status": "no_audio", "song_id": SONG_ID}
        mock_repo_cls.return_value.update.assert_called_once_with(
            SONG_ID, acoustid_fingerprint_status="failed"
        )
        mock_acoustid_cls.return_value.fingerprint_and_identify.assert_not_called()

    def test_fingerprint_exception_is_swallowed(
        self, mock_get_db, mock_acoustid_cls, mock_repo_cls, mock_config
    ):
        mock_session = MagicMock()
        mock_get_db.return_value = _make_db_context(mock_session)
        mock_acoustid_cls.return_value.fingerprint_and_identify.side_effect = Exception(
            "AcoustID API down"
        )

        with patch.object(Path, "exists", return_value=True):
            result = fingerprint_single_song(SONG_ID)

        assert result == {"status": "ok", "song_id": SONG_ID}
