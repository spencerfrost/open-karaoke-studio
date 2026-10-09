"""Tests for loudness measurement: the per-song helper and the library backfill."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from app.jobs.batch_tasks import batch_backfill_loudness
from app.jobs.metadata_tasks import detect_and_store_loudness
from app.services.audio import LoudnessResult

SONG_ID = "song-abc-123"


def _make_db_context(mock_session=None):
    """Return a mock for get_db_session used as a context manager."""
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=mock_session or MagicMock())
    ctx.__exit__ = Mock(return_value=False)
    return ctx


@pytest.fixture
def library(tmp_path):
    with patch("app.config.get_config", return_value=Mock(BASE_LIBRARY_DIR=tmp_path)):
        yield tmp_path


@patch("app.repositories.song_repository.SongRepository")
@patch("app.db.database.get_db_session")
@patch("app.jobs.metadata_tasks.detect_loudness")
class TestDetectAndStoreLoudness:
    def test_saves_measurement_and_gain(
        self, mock_detect, mock_get_db, mock_repo_cls, library
    ):
        mock_get_db.return_value = _make_db_context()
        mock_detect.return_value = LoudnessResult(-9.8, 0.3, -6.2)

        assert detect_and_store_loudness(SONG_ID) == "ok"
        mock_detect.assert_called_once_with(library / SONG_ID)
        mock_repo_cls.return_value.update.assert_called_once_with(
            SONG_ID, loudness_lufs=-9.8, true_peak_dbtp=0.3, gain_db=-6.2
        )

    def test_no_instrumental(self, mock_detect, mock_get_db, mock_repo_cls, library):
        mock_detect.side_effect = FileNotFoundError("instrumental.mp3")

        assert detect_and_store_loudness(SONG_ID) == "no_audio"
        mock_repo_cls.return_value.update.assert_not_called()

    def test_silent_song_leaves_gain_unset(
        self, mock_detect, mock_get_db, mock_repo_cls, library
    ):
        mock_detect.return_value = None

        assert detect_and_store_loudness(SONG_ID) == "silent"
        mock_repo_cls.return_value.update.assert_not_called()

    def test_ffmpeg_failure_is_swallowed(
        self, mock_detect, mock_get_db, mock_repo_cls, library
    ):
        mock_detect.side_effect = RuntimeError("ffmpeg loudnorm failed (1)")

        assert detect_and_store_loudness(SONG_ID) == "error"
        mock_repo_cls.return_value.update.assert_not_called()


@patch("app.jobs.metadata_tasks.detect_and_store_loudness")
@patch("app.db.database.get_db_session")
class TestBatchBackfillLoudness:
    def _session_with_ids(self, mock_get_db, ids):
        session = MagicMock()
        rows = [(song_id,) for song_id in ids]
        session.query.return_value.all.return_value = rows
        session.query.return_value.filter.return_value.all.return_value = rows
        mock_get_db.return_value = _make_db_context(session)
        return session

    def test_tallies_each_outcome(self, mock_get_db, mock_detect):
        self._session_with_ids(mock_get_db, ["a", "b", "c", "d", "e"])
        mock_detect.side_effect = ["ok", "ok", "silent", "no_audio", "error"]

        result = batch_backfill_loudness(mode="missing")

        assert result == {
            "processed": 5,
            "success": 2,
            "skipped": 3,
            "ok": 2,
            "silent": 1,
            "no_audio": 1,
            "error": 1,
        }

    def test_missing_mode_filters_to_unmeasured_songs(self, mock_get_db, mock_detect):
        session = self._session_with_ids(mock_get_db, [])

        batch_backfill_loudness(mode="missing")

        session.query.return_value.filter.assert_called_once()

    def test_all_mode_measures_every_song(self, mock_get_db, mock_detect):
        session = self._session_with_ids(mock_get_db, ["a"])
        mock_detect.return_value = "ok"

        batch_backfill_loudness(mode="all")

        session.query.return_value.filter.assert_not_called()
        mock_detect.assert_called_once_with("a")
