"""Tests for vocal range detection: the per-song helper, when it's queued, and the backfill."""

import json
from typing import Optional
from unittest.mock import patch

import pytest

from app.jobs.batch_tasks import batch_backfill_vocal_range
from app.jobs.metadata_tasks import (
    detect_and_store_vocal_range,
    detect_song_singing_map,
    queue_vocal_range_if_ready,
)
from app.services.processing_versions import VOCAL_RANGE_VERSION
from app.services.vocal_range import lyrics_md5

SONG_ID = "song-abc-123"
SINGING_MAP = json.dumps({"lead": [[10.0, 40.0], [50.0, 90.0]], "backing": []})
LRC = "[00:12.00]First line\n[00:15.50]Second line\n"


def _add_vocals(library, song_id=SONG_ID):
    song_dir = library / song_id
    song_dir.mkdir()
    (song_dir / "vocals.mp3").write_bytes(b"fake")


def _range(
    low: Optional[str] = "G2", high: Optional[str] = "E5", label: Optional[str] = None
):
    detail = {"method": "lyrics-v2", "gates": ["lead"], "pitched_share": 0.4}
    return {"low": low, "high": high, "label": label, "detail": detail}


@pytest.fixture
def mock_detect():
    """Stand in for the pitch analysis; saving the result runs for real."""
    with patch("app.jobs.metadata_tasks.detect_vocal_range") as detect:
        yield detect


@pytest.fixture
def send_task():
    with patch("app.jobs.metadata_tasks.celery.send_task") as send:
        yield send


class TestDetectAndStoreVocalRange:
    @pytest.fixture(autouse=True)
    def song(self, add_song):
        add_song(SONG_ID, singing_map=SINGING_MAP, synced_lyrics=LRC, duration=100.0)

    def test_saves_detected_range_and_detail(self, mock_detect, library, fetch_song):
        _add_vocals(library)
        mock_detect.return_value = _range()

        assert detect_and_store_vocal_range(SONG_ID) == "ok"
        saved = fetch_song(SONG_ID)
        assert (saved.vocal_range_low, saved.vocal_range_high) == ("G2", "E5")
        assert saved.vocal_range_version == VOCAL_RANGE_VERSION
        detail = json.loads(saved.vocal_range_detail)
        assert detail["method"] == "lyrics-v2"
        assert detail["label"] is None
        assert detail["lyrics_md5"] == lyrics_md5(LRC)

    def test_passes_the_lead_and_the_lyric_lines(self, mock_detect, library):
        _add_vocals(library)
        mock_detect.return_value = _range()

        detect_and_store_vocal_range(SONG_ID)

        context = mock_detect.call_args.args[1]
        assert context.lead == [(10.0, 40.0), (50.0, 90.0)]
        # The last line runs MAX_LINE_SECONDS past its timestamp.
        assert context.lyric_lines == [(12.0, 15.5), (15.5, 25.5)]

    def test_a_label_replaces_an_old_range(
        self, add_song, mock_detect, library, fetch_song
    ):
        add_song(
            "rap",
            singing_map=SINGING_MAP,
            vocal_range_low="C2",
            vocal_range_high="C6",
            vocal_range_version=1,
        )
        _add_vocals(library, "rap")
        mock_detect.return_value = _range(None, None, label="rapped")

        assert detect_and_store_vocal_range("rap") == "labelled"
        saved = fetch_song("rap")
        assert (saved.vocal_range_low, saved.vocal_range_high) == (None, None)
        assert json.loads(saved.vocal_range_detail)["label"] == "rapped"
        assert saved.vocal_range_version == VOCAL_RANGE_VERSION

    def test_no_held_note_is_an_answer(self, mock_detect, library, fetch_song):
        _add_vocals(library)
        mock_detect.return_value = _range(None, None)

        assert detect_and_store_vocal_range(SONG_ID) == "no_range"
        assert fetch_song(SONG_ID).vocal_range_version == VOCAL_RANGE_VERSION

    def test_no_vocals_file(self, mock_detect, library, fetch_song):
        assert detect_and_store_vocal_range(SONG_ID) == "no_audio"
        mock_detect.assert_not_called()
        assert fetch_song(SONG_ID).vocal_range_low is None

    def test_waits_for_the_singing_map(
        self, add_song, mock_detect, library, fetch_song
    ):
        add_song("no-map")
        _add_vocals(library, "no-map")

        assert detect_and_store_vocal_range("no-map") == "waiting"
        mock_detect.assert_not_called()
        assert fetch_song("no-map").vocal_range_version is None

    def test_a_failed_analysis_is_tried_again(self, mock_detect, library, fetch_song):
        _add_vocals(library)
        mock_detect.side_effect = RuntimeError("corrupt mp3")

        assert detect_and_store_vocal_range(SONG_ID) == "error"
        saved = fetch_song(SONG_ID)
        assert saved.vocal_range_low is None
        assert saved.vocal_range_version is None


class TestQueueVocalRangeIfReady:
    """The range waits for both the singing map and the lyrics."""

    @pytest.mark.parametrize(
        "fields, ready",
        [
            ({"singing_map": SINGING_MAP, "word_timing_version": 1}, True),
            ({"singing_map": SINGING_MAP}, False),
            ({"word_timing_version": 1}, False),
            # Up to date for these lyrics.
            (
                {
                    "singing_map": SINGING_MAP,
                    "word_timing_version": 1,
                    "synced_lyrics": LRC,
                    "vocal_range_version": VOCAL_RANGE_VERSION,
                    "vocal_range_detail": json.dumps({"lyrics_md5": lyrics_md5(LRC)}),
                },
                False,
            ),
            # Measured before the synced lyrics arrived.
            (
                {
                    "singing_map": SINGING_MAP,
                    "word_timing_version": 1,
                    "synced_lyrics": LRC,
                    "vocal_range_version": VOCAL_RANGE_VERSION,
                    "vocal_range_detail": json.dumps({"lyrics_md5": None}),
                },
                True,
            ),
        ],
    )
    def test_queues_only_when_both_are_in(self, add_song, send_task, fields, ready):
        add_song(SONG_ID, **fields)

        assert queue_vocal_range_if_ready(SONG_ID) is ready
        if ready:
            send_task.assert_called_once_with("detect_song_vocal_range", args=[SONG_ID])
        else:
            send_task.assert_not_called()

    def test_the_singing_map_task_queues_it(self, add_song, send_task):
        add_song(SONG_ID, word_timing_version=1)
        with patch(
            "app.services.singing_map.measure_singing_map",
            return_value={"lead": [[1.0, 2.0]], "backing": []},
        ):
            detect_song_singing_map(SONG_ID)

        send_task.assert_called_once_with("detect_song_vocal_range", args=[SONG_ID])


class TestBatchBackfillVocalRange:
    def test_tallies_each_outcome(self, add_song, mock_detect, library):
        outcomes = {
            "a": _range("G2", "E5"),
            "b": _range(None, None, label="rapped"),
            "c": _range(None, None),
            "e": RuntimeError("corrupt mp3"),
        }
        for song_id in "abcdef":
            add_song(song_id, singing_map=None if song_id == "f" else SINGING_MAP)
            # "d" has no vocals stem yet.
            if song_id != "d":
                _add_vocals(library, song_id)

        def detect(vocals_path, _context, _log):
            outcome = outcomes[vocals_path.parent.name]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        mock_detect.side_effect = detect

        result = batch_backfill_vocal_range(mode="missing")

        assert result == {
            "processed": 6,
            "success": 2,
            "skipped": 4,
            "ok": 1,
            "labelled": 1,
            "no_range": 1,
            "waiting": 1,
            "no_audio": 1,
            "error": 1,
        }

    def test_missing_mode_skips_songs_with_a_range(
        self, add_song, mock_detect, library, fetch_song
    ):
        add_song(
            "detected",
            singing_map=SINGING_MAP,
            vocal_range_low="A2",
            vocal_range_high="D5",
            vocal_range_version=VOCAL_RANGE_VERSION,
        )
        add_song("undetected", singing_map=SINGING_MAP)
        _add_vocals(library, "detected")
        _add_vocals(library, "undetected")
        mock_detect.return_value = _range()

        result = batch_backfill_vocal_range(mode="missing")

        assert result["processed"] == 1
        assert fetch_song("detected").vocal_range_low == "A2"
        assert fetch_song("undetected").vocal_range_low == "G2"

    def test_all_mode_detects_every_song(
        self, add_song, mock_detect, library, fetch_song
    ):
        add_song(
            "detected",
            singing_map=SINGING_MAP,
            vocal_range_low="A2",
            vocal_range_high="D5",
        )
        add_song("undetected", singing_map=SINGING_MAP)
        _add_vocals(library, "detected")
        _add_vocals(library, "undetected")
        mock_detect.return_value = _range()

        result = batch_backfill_vocal_range(mode="all")

        assert result["processed"] == 2
        assert fetch_song("detected").vocal_range_low == "G2"
        assert fetch_song("undetected").vocal_range_low == "G2"
