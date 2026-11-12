"""Tests for the singing map: the per-song helper and the library backfill."""

import json
from unittest.mock import patch

import pytest

from app.jobs.batch_tasks import batch_backfill_singing_map
from app.jobs.metadata_tasks import detect_and_store_singing_map
from app.services.processing_versions import SINGING_MAP_VERSION

SONG_ID = "song-abc-123"
MAP = {"method": "rms", "lead": [[1.0, 5.0]], "backing": [], "duration": 10.0}


@pytest.fixture
def mock_measure():
    """Stand in for reading the stems; saving the map runs for real."""
    with patch("app.services.singing_map.measure_singing_map") as measure:
        yield measure


class TestDetectAndStoreSingingMap:
    @pytest.fixture(autouse=True)
    def song(self, add_song):
        add_song(SONG_ID)

    def test_saves_the_map(self, mock_measure, library, fetch_song):
        mock_measure.return_value = MAP

        assert detect_and_store_singing_map(SONG_ID) == "ok"
        mock_measure.assert_called_once_with(library / SONG_ID)
        saved = fetch_song(SONG_ID)
        assert json.loads(saved.singing_map) == MAP
        assert saved.singing_map_version == SINGING_MAP_VERSION

    @pytest.mark.parametrize(
        "error, outcome",
        [(FileNotFoundError("vocals.mp3"), "no_audio"), (RuntimeError("bad"), "error")],
    )
    def test_saves_nothing_without_a_map(
        self, mock_measure, library, fetch_song, error, outcome
    ):
        mock_measure.side_effect = error

        assert detect_and_store_singing_map(SONG_ID) == outcome
        saved = fetch_song(SONG_ID)
        assert saved.singing_map is None
        assert saved.singing_map_version is None


class TestBatchBackfillSingingMap:
    def test_tallies_each_outcome(self, add_song, mock_measure, library):
        for song_id in "abc":
            add_song(song_id)
        outcomes = {"a": MAP, "b": FileNotFoundError("vocals.mp3"), "c": OSError()}

        def measure(song_dir):
            outcome = outcomes[song_dir.name]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        mock_measure.side_effect = measure

        assert batch_backfill_singing_map(mode="missing") == {
            "processed": 3,
            "success": 1,
            "skipped": 2,
            "ok": 1,
            "no_audio": 1,
            "error": 1,
        }

    def test_missing_mode_skips_measured_songs(
        self, add_song, mock_measure, library, fetch_song
    ):
        add_song(
            "measured",
            singing_map=json.dumps({"lead": []}),
            singing_map_version=SINGING_MAP_VERSION,
        )
        add_song("unmeasured")
        mock_measure.return_value = MAP

        assert batch_backfill_singing_map(mode="missing")["processed"] == 1
        mock_measure.assert_called_once_with(library / "unmeasured")
        assert json.loads(fetch_song("measured").singing_map) == {"lead": []}

    def test_all_mode_measures_every_song(
        self, add_song, mock_measure, library, fetch_song
    ):
        add_song("measured", singing_map=json.dumps({"lead": []}))
        mock_measure.return_value = MAP

        assert batch_backfill_singing_map(mode="all")["processed"] == 1
        assert json.loads(fetch_song("measured").singing_map) == MAP
