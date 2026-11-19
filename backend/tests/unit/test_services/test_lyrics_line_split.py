import json

from app.services.lyrics_line_split import (
    MAX_LINE_WORDS,
    TRANSCRIPT_SOURCE_MARK,
    is_transcript,
    long_line_count,
    split_long_lines,
    split_words_into_lines,
)


def _words(text, start, line_index=0, step=0.4, pause_after=None):
    words = []
    at = start
    for i, token in enumerate(text.split()):
        words.append(
            {
                "word": token,
                "start": round(at, 3),
                "end": round(at + step - 0.05, 3),
                "score": 0.9,
                "line_index": line_index,
            }
        )
        at += step
        if pause_after and i in pause_after:
            at += pause_after[i]
    return words


def _texts(lines):
    return [" ".join(w["word"] for w in line) for line in lines]


def test_a_pause_starts_a_new_line():
    words = _words("we sang all night then we went home", 0.0, pause_after={3: 1.5})
    assert _texts(split_words_into_lines(words)) == [
        "we sang all night",
        "then we went home",
    ]


def test_a_short_pause_or_comma_alone_keeps_a_short_line_whole():
    words = _words("we sang, all night", 0.0, pause_after={1: 0.8})
    assert _texts(split_words_into_lines(words)) == ["we sang, all night"]


def test_a_long_line_is_cut_at_its_longest_breath():
    text = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen"
    words = _words(text, 0.0, pause_after={9: 0.5})
    assert _texts(split_words_into_lines(words)) == [
        "one two three four five six seven eight nine ten",
        "eleven twelve thirteen fourteen",
    ]


def test_a_comma_counts_as_a_breath_when_the_gaps_are_even():
    text = "one two three four five, six seven eight nine ten eleven twelve thirteen"
    assert _texts(split_words_into_lines(_words(text, 0.0))) == [
        "one two three four five,",
        "six seven eight nine ten eleven twelve thirteen",
    ]


def test_every_part_fits_however_long_the_line():
    words = _words(" ".join(f"w{i}" for i in range(50)), 0.0)
    lines = split_words_into_lines(words)
    assert all(3 <= len(line) <= MAX_LINE_WORDS for line in lines)
    assert sum(len(line) for line in lines) == 50


LONG = (
    "Dream a new room Dream a new room Dream a new room "
    "Road is long and winding Like a good mystery unfolding"
)


def _stored():
    synced = "\n".join(
        [
            "[ar:ALO]",
            "[00:01.00]Welcome to your barbecue.",
            "[00:05.00]",
            f"[00:10.00]{LONG}",
            "[00:30.00]Fake out endings",
        ]
    )
    words = (
        _words("Welcome to your barbecue.", 1.0, 0)
        + _words(LONG, 10.0, 2, pause_after={11: 1.5})
        + _words("Fake out endings", 30.0, 3)
    )
    plain = "Welcome to your barbecue.\n\n" + LONG + "\nFake out endings"
    # Re-timed since the transcript, as Barbeque was: the source no longer says ASR.
    payload = {"words": words, "line_count": 3, "lyrics_source": "db:synced"}
    return synced, payload, plain


def test_stored_lyrics_get_their_long_line_cut_and_words_renumbered():
    synced, payload, plain = _stored()
    result = split_long_lines(synced, payload, plain)

    assert result is not None
    assert result["lines_split"] == 1
    assert result["synced_lyrics"].splitlines() == [
        "[ar:ALO]",
        "[00:01.00]Welcome to your barbecue.",
        "[00:05.00]",
        "[00:10.00]Dream a new room Dream a new room Dream a new room",
        "[00:16.30]Road is long and winding Like a good mystery unfolding",
        "[00:30.00]Fake out endings",
    ]
    assert result["plain_lyrics"] == "\n".join(
        [
            "Welcome to your barbecue.",
            "Dream a new room Dream a new room Dream a new room",
            "Road is long and winding Like a good mystery unfolding",
            "Fake out endings",
        ]
    )
    indexes = [w["line_index"] for w in result["word_payload"]["words"]]
    assert indexes == [0] * 4 + [2] * 12 + [3] * 10 + [4] * 3
    assert result["word_payload"]["line_count"] == 4
    assert result["word_payload"]["lyrics_source"] == "db:synced"
    json.dumps(result["word_payload"])


def test_plain_lyrics_written_apart_from_the_lrc_are_left_alone():
    synced, payload, _ = _stored()
    result = split_long_lines(synced, payload, "Some other\nplain text")
    assert result is not None
    assert result["plain_lyrics"] is None


def test_nothing_changes_when_no_line_is_too_long():
    synced = "[00:01.00]Short line\n[00:03.00]Another"
    payload = {"words": _words("Short line", 1.0, 0) + _words("Another", 3.0, 1)}
    assert split_long_lines(synced, payload) is None


def test_a_line_whose_words_dont_match_its_text_stays_whole():
    synced = f"[00:10.00]{LONG}"
    payload = {
        "words": _words(LONG.replace("winding", "windy"), 10.0, 0),
        "lyrics_source": "asr:whisperx",
    }
    assert split_long_lines(synced, payload) is None


def test_words_on_a_line_the_text_lacks_leave_the_song_alone():
    synced, payload, plain = _stored()
    payload["words"] += _words("stray", 40.0, 9)
    assert split_long_lines(synced, payload, plain) is None


def test_long_line_count():
    synced, _, _ = _stored()
    assert long_line_count(synced, transcript=False) == 1
    assert long_line_count(None, transcript=False) == 0


def test_a_written_lrc_keeps_lines_a_rapper_would_write():
    # 16 words: too long for a transcript, fine in an LRC someone wrote.
    verse = "I got a lot on my mind and I keep it moving all the time yeah"
    synced = f"[00:10.00]{verse}"
    words = _words(verse, 10.0, 0, pause_after={7: 1.0})
    written = {"words": words, "lyrics_source": "lrclib:1"}
    transcript = {"words": words, "lyrics_source": "asr:whisperx"}

    assert long_line_count(synced, transcript=False) == 0
    assert long_line_count(synced, transcript=True) == 1
    assert split_long_lines(synced, written) is None
    result = split_long_lines(synced, transcript)
    assert result is not None
    assert result["synced_lyrics"].splitlines() == [
        "[00:10.00]I got a lot on my mind and",
        "[00:14.20]I keep it moving all the time yeah",
    ]


def test_a_written_lrc_line_past_the_written_limit_is_cut():
    line = " ".join(f"w{i}" for i in range(25))
    payload = {"words": _words(line, 0.0, 0), "lyrics_source": "db:synced"}
    result = split_long_lines(f"[00:00.00]{line}", payload)
    assert result is not None
    assert long_line_count(result["synced_lyrics"], transcript=False) == 0


def test_a_break_timed_inside_a_cut_line_moves_to_its_end():
    synced = f"[00:10.00]{LONG}\n[00:14.00]\n[00:30.00]Fake out endings"
    words = _words(LONG, 10.0, 0, pause_after={11: 1.5}) + _words(
        "Fake out endings", 30.0, 2
    )
    payload = {"words": words, "lyrics_source": "asr:whisperx"}
    result = split_long_lines(synced, payload)

    assert result is not None
    # Last word starts at 10 + 21 * 0.4 + 1.5 and ends 0.35 s later.
    assert result["synced_lyrics"].splitlines()[2:] == [
        "[00:20.25]",
        "[00:30.00]Fake out endings",
    ]


def test_the_transcript_mark_matches_a_stored_transcript_payload():
    payload = {"words": [], "lyrics_source": "asr:whisperx"}
    assert TRANSCRIPT_SOURCE_MARK in json.dumps(payload)
    assert is_transcript(payload)
    assert TRANSCRIPT_SOURCE_MARK not in json.dumps({"lyrics_source": "lrclib:1"})
