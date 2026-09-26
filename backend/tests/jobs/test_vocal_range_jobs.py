"""Tests for vocal range detection: the per-song helper and the library backfill."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from app.jobs.batch_tasks import batch_backfill_vocal_range
from app.jobs.metadata_tasks import detect_and_store_vocal_range

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


def _add_vocals(library, song_id=SONG_ID):
    song_dir = library / song_id
    song_dir.mkdir()
    (song_dir / "vocals.mp3").write_bytes(b"fake")


@patch("app.repositories.song_repository.SongRepository")
@patch("app.db.database.get_db_session")
@patch("app.jobs.metadata_tasks.detect_vocal_range")
class TestDetectAndStoreVocalRange:
    def test_saves_detected_range(self, mock_detect, mock_get_db, mock_repo_cls, library):
        _add_vocals(library)
        mock_get_db.return_value = _make_db_context()
        mock_detect.return_value = ("G2", "E5")

        assert detect_and_store_vocal_range(SONG_ID) == "ok"
        mock_repo_cls.return_value.update.assert_called_once_with(
            SONG_ID, vocal_range_low="G2", vocal_range_high="E5"
        )

    def test_no_vocals_file(self, mock_detect, mock_get_db, mock_repo_cls, library):
        assert detect_and_store_vocal_range(SONG_ID) == "no_audio"
        mock_detect.assert_not_called()
        mock_repo_cls.return_value.update.assert_not_called()

    def test_too_few_voiced_frames(self, mock_detect, mock_get_db, mock_repo_cls, library):
        _add_vocals(library)
        mock_detect.return_value = None

        assert detect_and_store_vocal_range(SONG_ID) == "no_range"
        mock_repo_cls.return_value.update.assert_not_called()

    def test_detection_exception_is_swallowed(
        self, mock_detect, mock_get_db, mock_repo_cls, library
    ):
        _add_vocals(library)
        mock_detect.side_effect = RuntimeError("corrupt mp3")

        assert detect_and_store_vocal_range(SONG_ID) == "error"
        mock_repo_cls.return_value.update.assert_not_called()


@patch("app.jobs.metadata_tasks.detect_and_store_vocal_range")
@patch("app.db.database.get_db_session")
class TestBatchBackfillVocalRange:
    def _session_with_ids(self, mock_get_db, ids):
        session = MagicMock()
        rows = [(song_id,) for song_id in ids]
        session.query.return_value.all.return_value = rows
        session.query.return_value.filter.return_value.all.return_value = rows
        mock_get_db.return_value = _make_db_context(session)
        return session

    def test_tallies_each_outcome(self, mock_get_db, mock_detect):
        self._session_with_ids(mock_get_db, ["a", "b", "c", "d", "e"])
        mock_detect.side_effect = ["ok", "ok", "no_range", "no_audio", "error"]

        result = batch_backfill_vocal_range(mode="missing")

        assert result == {
            "processed": 5,
            "success": 2,
            "skipped": 3,
            "ok": 2,
            "no_range": 1,
            "no_audio": 1,
            "error": 1,
        }
        assert [c.args[0] for c in mock_detect.call_args_list] == ["a", "b", "c", "d", "e"]

    def test_missing_mode_filters_songs_with_a_range(self, mock_get_db, mock_detect):
        session = self._session_with_ids(mock_get_db, [])

        batch_backfill_vocal_range(mode="missing")

        session.query.return_value.filter.assert_called_once()

    def test_all_mode_does_not_filter(self, mock_get_db, mock_detect):
        session = self._session_with_ids(mock_get_db, ["a"])
        mock_detect.return_value = "ok"

        result = batch_backfill_vocal_range(mode="all")

        session.query.return_value.filter.assert_not_called()
        assert result["processed"] == 1
