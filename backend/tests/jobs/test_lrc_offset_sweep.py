"""Tests for the LRC offset sweep job: sweep and store the layer, review it on
Compare word timing, apply it.

Rows and files are real; the GPU sweep and alignment are mocked.
"""

import json
from unittest.mock import patch

import pytest

from app.db.database import SessionLocal
from app.db.models import DbSong
from app.jobs.batch_tasks import batch_sweep_lrc_offsets
from app.services import lrc_offset_layer
from app.services import word_timing_experiments as wte
from app.services.file_service import FileService
from app.services.lrc_offset_layer import REVIEW_ID, lrc_md5
from app.services.processing_versions import LRC_OFFSET_VERSION

LRC = "[00:10.00] hello world\n[00:15.00] good night"
OFF = "a" * 8 + "-0000-0000-0000-" + "0" * 12  # Compare needs uuid-shaped ids
RIGHT = "b" * 8 + "-0000-0000-0000-" + "0" * 12


def _sweep(shift, gain):
    return {
        "shift": shift,
        "score": 0.45 + gain,
        "baseline_score": 0.45,
        "gain": gain,
        "scores": {0.0: 0.45, shift: 0.45 + gain},
    }


def _alignment(start, score=0.7):
    words = [
        {"word": w, "start": start + i, "end": start + i + 0.5, "score": 0.7}
        for i, w in enumerate(["hello", "world"])
    ] + [
        {"word": w, "start": start + 5 + i, "end": start + 5.5 + i, "score": 0.7}
        for i, w in enumerate(["good", "night"])
    ]
    for word, line in zip(words, [0, 0, 1, 1]):
        word["line_index"] = line
    return {
        "words": words,
        "mean_score": score,
        "language": "en",
        "word_count": 4,
        "line_count": 2,
        "aligned_at": "2026-11-11T00:00:00Z",
        "instrumental_intervals": [],
    }


@pytest.fixture
def songs(add_song):
    for song_id in (OFF, RIGHT):
        add_song(
            song_id,
            synced_lyrics=LRC,
            word_synced_lyrics=json.dumps(_alignment(10.0, score=0.45)),
        )
        vocals = FileService().get_vocals_path(song_id, ".mp3")
        vocals.parent.mkdir(parents=True, exist_ok=True)
        vocals.write_bytes(b"fake")
    add_song("no-vocals", synced_lyrics=LRC)
    add_song("no-lyrics")
    yield
    for song_id in (OFF, RIGHT):
        FileService().get_vocals_path(song_id, ".mp3").unlink(missing_ok=True)


@pytest.fixture
def swept(songs):
    """Run the sweep: OFF is 4 s early with a clear gain, RIGHT is right."""

    def sweep(lrc, vocals, **kwargs):
        assert kwargs["max_shift"] == 12.0 and kwargs["step"] == 1.0
        assert kwargs["fine_around_zero"] is False
        return _sweep(4.0, 0.25) if OFF in str(vocals) else _sweep(0.0, 0.0)

    with (
        patch("app.services.lyrics_offset.sweep_lrc_offset", side_effect=sweep),
        patch(
            "app.services.lyrics_alignment.align_lyrics_to_vocals",
            return_value=_alignment(14.0),
        ),
    ):
        result = batch_sweep_lrc_offsets(mode="missing")
    return result


def _song(song_id):
    with SessionLocal() as session:
        song = session.get(DbSong, song_id)
        song.lrc_offset_sweep  # load the deferred column
        return song


def _select(mode):
    with SessionLocal() as session:
        return lrc_offset_layer.select_ids(session, mode)


class TestSweep:
    def test_selects_songs_with_synced_lyrics_and_vocals(self, songs):
        assert _select("missing") == [OFF, RIGHT]
        assert _select("apply") == []

    def test_a_shift_that_passes_waits_to_be_applied(self, swept):
        assert swept["shift"] == 1 and swept["no_shift"] == 1
        song = _song(OFF)
        layer = json.loads(song.lrc_offset_sweep)
        assert song.lrc_offset_pending_shift == 4.0
        assert song.lrc_offset_version == LRC_OFFSET_VERSION
        assert song.lrc_offset_lrc_md5 == lrc_md5(LRC)
        assert (layer["shift"], layer["gain"], layer["passes"]) == (4.0, 0.25, True)
        assert layer["shifted"]["words"][0]["start"] == 14.0
        # Nothing the TV shows changed.
        assert song.synced_lyrics == LRC

    def test_no_shift_is_stored_and_not_swept_again(self, swept):
        song = _song(RIGHT)
        assert song.lrc_offset_pending_shift is None
        assert json.loads(song.lrc_offset_sweep)["rejection"] == "no_shift"
        assert _select("missing") == []
        assert _select("apply") == [OFF]

    def test_changed_lyrics_make_the_sweep_stale(self, swept):
        with SessionLocal() as session:
            session.get(DbSong, OFF).synced_lyrics = LRC + "\n[00:20.00] again"
            session.commit()

        assert _select("missing") == [OFF]
        assert _select("apply") == []

    def test_the_waiting_shift_is_on_compare_word_timing(self, swept):
        with SessionLocal() as session:
            ids = [e["id"] for e in wte.list_experiments(session)]
            listing = wte.list_songs(REVIEW_ID, session)
            detail = wte.song_detail(REVIEW_ID, OFF, session)

        assert REVIEW_ID in ids
        assert [s["songId"] for s in listing["songs"]] == [OFF]
        assert listing["songs"][0]["group"] == "clear"
        assert [m["key"] for m in detail["moments"]] == ["line:0", "line:1"]

    def test_answers_are_kept_on_the_song(self, swept):
        with SessionLocal() as session:
            wte.save_answers(
                REVIEW_ID, OFF, [{"key": "line:0", "answer": "b_right"}], session
            )
        with SessionLocal() as session:
            assert (
                wte.song_detail(REVIEW_ID, OFF, session)["moments"][0]["answer"]
                == "b_right"
            )
        assert json.loads(_song(OFF).lrc_offset_sweep)["answers"] == {
            "line:0": "b_right"
        }

    def test_a_song_not_waiting_is_not_found_on_compare(self, swept):
        with SessionLocal() as session, pytest.raises(wte.NotFound):
            wte.song_detail(REVIEW_ID, RIGHT, session)


class TestApply:
    def test_apply_shifts_the_lrc_and_its_timing(self, swept):
        with patch(
            "app.services.lyrics_alignment.align_lyrics_to_vocals",
            return_value=_alignment(14.0),
        ) as align:
            result = batch_sweep_lrc_offsets(mode="apply")

        assert result["applied"] == 1
        assert align.call_args.args[0].startswith("[00:14.00] hello world")
        song = _song(OFF)
        assert song.synced_lyrics.startswith("[00:14.00] hello world")
        timing = json.loads(song.word_synced_lyrics)
        assert timing["offset_applied"] == 4.0
        assert timing["words"][0]["start"] == 14.0
        layer = json.loads(song.lrc_offset_sweep)
        assert layer["applied_shift"] == 4.0 and "shifted" not in layer
        assert song.lrc_offset_pending_shift is None
        # The layer now describes the shifted LRC: not swept or applied again.
        assert _select("missing") == []
        assert _select("apply") == []

    def test_a_shift_that_no_longer_aligns_is_left_alone(self, swept):
        with patch(
            "app.services.lyrics_alignment.align_lyrics_to_vocals",
            return_value=_alignment(14.0, score=0.1),
        ):
            result = batch_sweep_lrc_offsets(mode="apply")

        assert result["rejected"] == 1
        assert _song(OFF).synced_lyrics == LRC
