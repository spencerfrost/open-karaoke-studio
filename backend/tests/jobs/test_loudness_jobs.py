"""Tests for loudness measurement: the per-song helper and the library backfill."""

from unittest.mock import patch

import pytest

from app.jobs.batch_tasks import batch_backfill_loudness
from app.jobs.metadata_tasks import detect_and_store_loudness
from app.services.audio import LoudnessResult
from app.services.processing_versions import LOUDNESS_VERSION

SONG_ID = "song-abc-123"


@pytest.fixture
def mock_detect():
    """Stand in for the ffmpeg measurement; saving the result runs for real."""
    with patch("app.jobs.metadata_tasks.detect_loudness") as detect:
        yield detect


class TestDetectAndStoreLoudness:
    @pytest.fixture(autouse=True)
    def song(self, add_song):
        add_song(SONG_ID)

    def test_saves_measurement_and_gain(self, mock_detect, library, fetch_song):
        mock_detect.return_value = LoudnessResult(-9.8, 0.3, -6.2)

        assert detect_and_store_loudness(SONG_ID) == "ok"
        mock_detect.assert_called_once_with(library / SONG_ID)
        saved = fetch_song(SONG_ID)
        assert saved.loudness_lufs == -9.8
        assert saved.true_peak_dbtp == 0.3
        assert saved.gain_db == -6.2
        assert saved.loudness_version == LOUDNESS_VERSION

    @pytest.mark.parametrize(
        "detect, outcome",
        [
            ({"side_effect": FileNotFoundError("instrumental.mp3")}, "no_audio"),
            ({"return_value": None}, "silent"),
            ({"side_effect": RuntimeError("ffmpeg loudnorm failed (1)")}, "error"),
        ],
    )
    def test_saves_nothing_without_a_measurement(
        self, mock_detect, library, fetch_song, detect, outcome
    ):
        mock_detect.configure_mock(**detect)

        assert detect_and_store_loudness(SONG_ID) == outcome
        saved = fetch_song(SONG_ID)
        assert saved.loudness_lufs is None
        assert saved.gain_db is None
        # Silence is an answer; a step that couldn't run is tried again.
        assert saved.loudness_version == (
            LOUDNESS_VERSION if outcome == "silent" else None
        )


class TestBatchBackfillLoudness:
    def test_tallies_each_outcome(self, add_song, mock_detect, library):
        for song_id in "abcde":
            add_song(song_id)
        outcomes = {
            "a": LoudnessResult(-9.0, 0.0, -5.0),
            "b": LoudnessResult(-12.0, -1.0, -2.0),
            "c": None,
            "d": FileNotFoundError("instrumental.mp3"),
            "e": RuntimeError("ffmpeg failed"),
        }

        def detect(song_dir):
            outcome = outcomes[song_dir.name]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        mock_detect.side_effect = detect

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

    def test_missing_mode_skips_measured_songs(
        self, add_song, mock_detect, library, fetch_song
    ):
        add_song(
            "measured",
            loudness_lufs=-10.0,
            true_peak_dbtp=0.0,
            gain_db=-4.0,
            loudness_version=LOUDNESS_VERSION,
        )
        add_song("unmeasured")
        mock_detect.return_value = LoudnessResult(-9.0, 0.0, -5.0)

        result = batch_backfill_loudness(mode="missing")

        assert result["processed"] == 1
        mock_detect.assert_called_once_with(library / "unmeasured")
        assert fetch_song("measured").gain_db == -4.0
        assert fetch_song("unmeasured").gain_db == -5.0

    def test_all_mode_measures_every_song(
        self, add_song, mock_detect, library, fetch_song
    ):
        add_song("measured", loudness_lufs=-10.0, true_peak_dbtp=0.0, gain_db=-4.0)
        add_song("unmeasured")
        mock_detect.return_value = LoudnessResult(-9.0, 0.0, -5.0)

        result = batch_backfill_loudness(mode="all")

        assert result["processed"] == 2
        assert fetch_song("measured").gain_db == -5.0
        assert fetch_song("unmeasured").gain_db == -5.0
