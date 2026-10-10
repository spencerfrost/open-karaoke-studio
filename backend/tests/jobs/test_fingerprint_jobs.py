"""Tests for the fingerprint_single_song Celery task."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

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
@patch("app.jobs.metadata_tasks.celery")
class TestFingerprintSingleSong:
    def test_uses_instrumental_when_exists(
        self, mock_celery, mock_get_db, mock_acoustid_cls, mock_repo_cls, mock_config
    ):
        mock_session = MagicMock()
        mock_get_db.return_value = _make_db_context(mock_session)
        mock_acoustid_cls.return_value.fingerprint_and_link.return_value = "matched"

        with patch.object(Path, "exists", side_effect=[False, True, False]):
            result = fingerprint_single_song(SONG_ID)

        assert result == {"status": "matched", "song_id": SONG_ID}
        mock_acoustid_cls.return_value.fingerprint_and_link.assert_called_once()
        args = mock_acoustid_cls.return_value.fingerprint_and_link.call_args[0]
        assert args[0] == SONG_ID
        assert str(args[1]).endswith("instrumental.mp3")

    def test_uses_vocals_when_instrumental_missing(
        self, mock_celery, mock_get_db, mock_acoustid_cls, mock_repo_cls, mock_config
    ):
        mock_session = MagicMock()
        mock_get_db.return_value = _make_db_context(mock_session)

        mock_acoustid_cls.return_value.fingerprint_and_link.return_value = "matched"

        with patch.object(Path, "exists", side_effect=[False, False, True]):
            result = fingerprint_single_song(SONG_ID)

        assert result == {"status": "matched", "song_id": SONG_ID}
        args = mock_acoustid_cls.return_value.fingerprint_and_link.call_args[0]
        assert str(args[1]).endswith("vocals.mp3")

    def test_no_audio_updates_status_and_returns_no_audio(
        self, mock_celery, mock_get_db, mock_acoustid_cls, mock_repo_cls, mock_config
    ):
        mock_session = MagicMock()
        mock_get_db.return_value = _make_db_context(mock_session)

        with patch.object(Path, "exists", return_value=False):
            result = fingerprint_single_song(SONG_ID)

        assert result == {"status": "no_audio", "song_id": SONG_ID}
        mock_repo_cls.return_value.update.assert_called_once_with(
            SONG_ID, acoustid_fingerprint_status="failed"
        )
        mock_acoustid_cls.return_value.fingerprint_and_link.assert_not_called()

    def test_fingerprint_exception_is_swallowed(
        self, mock_celery, mock_get_db, mock_acoustid_cls, mock_repo_cls, mock_config
    ):
        mock_session = MagicMock()
        mock_get_db.return_value = _make_db_context(mock_session)
        mock_acoustid_cls.return_value.fingerprint_and_link.side_effect = Exception(
            "AcoustID API down"
        )

        with patch.object(Path, "exists", return_value=True):
            result = fingerprint_single_song(SONG_ID)

        assert result == {"status": "error", "song_id": SONG_ID}
        mock_celery.send_task.assert_not_called()

    def test_a_link_sends_the_credits_step(
        self, mock_celery, mock_get_db, mock_acoustid_cls, mock_repo_cls, mock_config
    ):
        mock_get_db.return_value = _make_db_context()
        mock_acoustid_cls.return_value.fingerprint_and_link.return_value = "matched"

        with patch.object(Path, "exists", return_value=True):
            fingerprint_single_song(SONG_ID)

        mock_celery.send_task.assert_called_once_with(
            "enrich_song_artist_credits", args=[SONG_ID]
        )

    @pytest.mark.parametrize(
        "outcome", ["suggested", "ambiguous", "no_match", "failed", "skipped"]
    )
    def test_no_link_sends_no_credits_step(
        self,
        mock_celery,
        mock_get_db,
        mock_acoustid_cls,
        mock_repo_cls,
        mock_config,
        outcome,
    ):
        mock_get_db.return_value = _make_db_context()
        mock_acoustid_cls.return_value.fingerprint_and_link.return_value = outcome

        with patch.object(Path, "exists", return_value=True):
            result = fingerprint_single_song(SONG_ID)

        assert result["status"] == outcome
        mock_celery.send_task.assert_not_called()
