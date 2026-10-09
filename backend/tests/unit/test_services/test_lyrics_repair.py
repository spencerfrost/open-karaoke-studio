"""Tests for picking which songs a library-wide lyrics alignment run queues."""

import json
from types import SimpleNamespace

from app.services.lyrics_repair import count_reasons, repair_reasons

LRC = "[00:01.00]First line here\n[00:02.00]\n[00:03.00]Second line here\n"


def _words(texts, line_indexes):
    return [
        {
            "word": text,
            "start": i * 0.3,
            "end": i * 0.3 + 0.3,
            "score": 0.9,
            "line_index": line,
        }
        for i, (text, line) in enumerate(zip(texts, line_indexes))
    ]


def _payload(words, **fields):
    return json.dumps({"words": words, "lyrics_source_type": "synced", **fields})


def _song(**overrides):
    fields = {
        "id": "song-1",
        "synced_lyrics": LRC,
        "plain_lyrics": None,
        "word_synced_lyrics": None,
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


GOOD_WORDS = _words(
    ["First", "line", "here", "Second", "line", "here"], [0, 0, 0, 2, 2, 2]
)


def test_words_that_read_as_the_lyrics_need_nothing():
    song = _song(word_synced_lyrics=_payload(GOOD_WORDS))

    assert repair_reasons(song, reported=False) == []


def test_synced_lyrics_without_word_timings():
    assert repair_reasons(_song(), reported=False) == ["no_word_timing"]


def test_plain_lyrics_only():
    song = _song(synced_lyrics=None, plain_lyrics="First line here")

    assert repair_reasons(song, reported=False) == ["plain_only"]


def test_no_lyrics_at_all_is_not_a_repair():
    song = _song(synced_lyrics=None)

    assert repair_reasons(song, reported=False) == []


def test_word_timings_aligned_to_plain_lyrics():
    song = _song(word_synced_lyrics=_payload(GOOD_WORDS, lyrics_source_type="plain"))

    assert repair_reasons(song, reported=False) == ["plain_timing"]


def test_words_with_other_text_than_the_lyrics():
    words = _words(
        ["First", "line", "there", "Second", "line", "here"], [0, 0, 0, 2, 2, 2]
    )
    song = _song(word_synced_lyrics=_payload(words))

    assert repair_reasons(song, reported=False) == ["words_mismatch"]


def test_words_pointing_at_the_wrong_line():
    words = _words(
        ["First", "line", "here", "Second", "line", "here"], [0, 0, 2, 2, 2, 2]
    )
    song = _song(word_synced_lyrics=_payload(words))

    assert repair_reasons(song, reported=False) == ["words_mismatch"]


def test_word_timings_without_synced_lyrics_to_match():
    song = _song(
        synced_lyrics=None,
        plain_lyrics="First line here",
        word_synced_lyrics=_payload(GOOD_WORDS),
    )

    assert repair_reasons(song, reported=False) == ["words_mismatch"]


def test_unreadable_word_timings():
    song = _song(word_synced_lyrics="{not json")

    assert repair_reasons(song, reported=False) == ["words_mismatch"]


def test_an_open_report_adds_its_reason():
    good = _song(word_synced_lyrics=_payload(GOOD_WORDS))

    assert repair_reasons(good, reported=True) == ["reported"]
    assert repair_reasons(_song(), reported=True) == ["no_word_timing", "reported"]


def test_count_reasons_counts_each_reason_once_per_song():
    selected = [
        (_song(), ["no_word_timing", "reported"]),
        (_song(), ["no_word_timing"]),
        (_song(), []),
    ]

    assert count_reasons(selected) == {
        "no_word_timing": 2,
        "plain_only": 0,
        "plain_timing": 0,
        "words_mismatch": 0,
        "reported": 1,
    }
