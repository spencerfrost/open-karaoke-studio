"""Tests for cutting stored lyric lines too long to be one line."""

import json

from app.jobs.batch_tasks import batch_split_long_lyric_lines
from app.jobs.lyrics_line_tasks import split_stored_long_lines
from app.services.lrc_offset_layer import lrc_md5

LONG = (
    "Dream a new room Dream a new room Dream a new room "
    "Road is long and winding Like a good mystery unfolding"
)


def _words(text, start, line_index, pause_after=None):
    words = []
    at = start
    for i, token in enumerate(text.split()):
        words.append(
            {
                "word": token,
                "start": round(at, 3),
                "end": round(at + 0.35, 3),
                "score": 0.9,
                "line_index": line_index,
            }
        )
        at += 0.4
        if pause_after and i in pause_after:
            at += pause_after[i]
    return words


def _transcript_song(add_song, song_id, **fields):
    synced = f"[00:01.00]Welcome home.\n[00:10.00]{LONG}"
    payload = {
        "words": _words("Welcome home.", 1.0, 0)
        + _words(LONG, 10.0, 1, pause_after={11: 1.5}),
        "lyrics_source": "asr:whisperx",
    }
    fields.setdefault("lrc_offset_lrc_md5", lrc_md5(synced))
    return add_song(
        song_id,
        synced_lyrics=synced,
        plain_lyrics=f"Welcome home.\n{LONG}",
        word_synced_lyrics=json.dumps(payload),
        **fields,
    )


class TestSplitStoredLongLines:
    def test_cuts_the_line_and_keeps_the_offset_sweep(self, add_song, fetch_song):
        _transcript_song(add_song, "long-1")

        assert split_stored_long_lines("long-1") == "split"

        song = fetch_song("long-1")
        assert song.synced_lyrics.splitlines() == [
            "[00:01.00]Welcome home.",
            "[00:10.00]Dream a new room Dream a new room Dream a new room",
            "[00:16.30]Road is long and winding Like a good mystery unfolding",
        ]
        assert song.plain_lyrics.splitlines()[1:] == [
            "Dream a new room Dream a new room Dream a new room",
            "Road is long and winding Like a good mystery unfolding",
        ]
        words = json.loads(song.word_synced_lyrics)["words"]
        assert {w["line_index"] for w in words} == {0, 1, 2}
        assert song.lrc_offset_lrc_md5 == lrc_md5(song.synced_lyrics)

    def test_a_stale_offset_sweep_stays_stale(self, add_song, fetch_song):
        _transcript_song(add_song, "long-2", lrc_offset_lrc_md5="0" * 32)

        assert split_stored_long_lines("long-2") == "split"
        assert fetch_song("long-2").lrc_offset_lrc_md5 == "0" * 32

    def test_outcomes_without_anything_to_cut(self, add_song):
        add_song("short", synced_lyrics="[00:01.00]Hi", word_synced_lyrics=None)
        add_song(
            "fits",
            synced_lyrics="[00:01.00]Hi",
            word_synced_lyrics=json.dumps({"words": _words("Hi", 1.0, 0)}),
        )

        assert split_stored_long_lines("short") == "no_timing"
        assert split_stored_long_lines("fits") == "fine"
        assert split_stored_long_lines("missing-song") == "no_timing"


class TestBatchSplitLongLyricLines:
    def test_runs_on_the_songs_with_long_lines(self, add_song, fetch_song):
        _transcript_song(add_song, "batch-long")
        add_song(
            "batch-fits",
            synced_lyrics="[00:01.00]Hi",
            word_synced_lyrics=json.dumps({"words": _words("Hi", 1.0, 0)}),
        )

        result = batch_split_long_lyric_lines(mode="missing")

        assert result["split"] >= 1
        assert result["error"] == 0
        assert len(fetch_song("batch-long").synced_lyrics.splitlines()) == 3
