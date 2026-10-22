"""Tests for vocal range detection: the per-song helper and the library backfill."""

from unittest.mock import patch

import pytest

from app.jobs.batch_tasks import batch_backfill_vocal_range
from app.jobs.metadata_tasks import detect_and_store_vocal_range

SONG_ID = "song-abc-123"


def _add_vocals(library, song_id=SONG_ID):
    song_dir = library / song_id
    song_dir.mkdir()
    (song_dir / "vocals.mp3").write_bytes(b"fake")


@pytest.fixture
def mock_detect():
    """Stand in for the pitch analysis; saving the result runs for real."""
    with patch("app.jobs.metadata_tasks.detect_vocal_range") as detect:
        yield detect


class TestDetectAndStoreVocalRange:
    @pytest.fixture(autouse=True)
    def song(self, add_song):
        add_song(SONG_ID)

    def test_saves_detected_range(self, mock_detect, library, fetch_song):
        _add_vocals(library)
        mock_detect.return_value = ("G2", "E5")

        assert detect_and_store_vocal_range(SONG_ID) == "ok"
        saved = fetch_song(SONG_ID)
        assert (saved.vocal_range_low, saved.vocal_range_high) == ("G2", "E5")

    def test_no_vocals_file(self, mock_detect, library, fetch_song):
        assert detect_and_store_vocal_range(SONG_ID) == "no_audio"
        mock_detect.assert_not_called()
        assert fetch_song(SONG_ID).vocal_range_low is None

    @pytest.mark.parametrize(
        "detect, outcome",
        [
            ({"return_value": None}, "no_range"),
            ({"side_effect": RuntimeError("corrupt mp3")}, "error"),
        ],
    )
    def test_saves_nothing_without_a_range(
        self, mock_detect, library, fetch_song, detect, outcome
    ):
        _add_vocals(library)
        mock_detect.configure_mock(**detect)

        assert detect_and_store_vocal_range(SONG_ID) == outcome
        assert fetch_song(SONG_ID).vocal_range_low is None


class TestBatchBackfillVocalRange:
    def test_tallies_each_outcome(self, add_song, mock_detect, library):
        outcomes = {
            "a": ("G2", "E5"),
            "b": ("C3", "A4"),
            "c": None,
            "e": RuntimeError("corrupt mp3"),
        }
        for song_id in "abcde":
            add_song(song_id)
            # "d" has no vocals stem yet.
            if song_id != "d":
                _add_vocals(library, song_id)

        def detect(vocals_path, _log):
            outcome = outcomes[vocals_path.parent.name]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        mock_detect.side_effect = detect

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

    def test_missing_mode_skips_songs_with_a_range(
        self, add_song, mock_detect, library, fetch_song
    ):
        add_song("detected", vocal_range_low="A2", vocal_range_high="D5")
        add_song("undetected")
        _add_vocals(library, "detected")
        _add_vocals(library, "undetected")
        mock_detect.return_value = ("G2", "E5")

        result = batch_backfill_vocal_range(mode="missing")

        assert result["processed"] == 1
        assert fetch_song("detected").vocal_range_low == "A2"
        assert fetch_song("undetected").vocal_range_low == "G2"

    def test_all_mode_detects_every_song(
        self, add_song, mock_detect, library, fetch_song
    ):
        add_song("detected", vocal_range_low="A2", vocal_range_high="D5")
        add_song("undetected")
        _add_vocals(library, "detected")
        _add_vocals(library, "undetected")
        mock_detect.return_value = ("G2", "E5")

        result = batch_backfill_vocal_range(mode="all")

        assert result["processed"] == 2
        assert fetch_song("detected").vocal_range_low == "G2"
        assert fetch_song("undetected").vocal_range_low == "G2"
