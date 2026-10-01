"""Tests for timing a lyrics text from an ASR transcript."""

from app.services.lyrics_alignment import AlignedWord
from app.services.lyrics_analysis import parse_lrc_lines
from app.services.lyrics_retiming import (
    CHUNK_SLACK_SECONDS,
    LEAD_IN_SECONDS,
    WORD_SECONDS,
    _longest_common_subsequence,
    lrc_from_aligned_lines,
    lyrics_text_lines,
    plan_retiming,
)


def _asr(*timed_words: tuple[str, float], score: float = 0.9) -> list[dict]:
    """ASR words, each sung for 0.3s from the given start."""
    return [
        {"word": word, "start": start, "end": start + 0.3, "score": score}
        for word, start in timed_words
    ]


def _chunk_spans(plan) -> list[tuple[int, int]]:
    return [(chunk["first_line"], chunk["last_line"]) for chunk in plan["chunks"]]


# ---------------------------------------------------------------------------
# lyrics_text_lines
# ---------------------------------------------------------------------------


def test_lyrics_text_lines_drops_headers_blanks_and_timestamps():
    plain = "[Chorus]\nBlackbird singing\n\n  in the dead of night  \n...\n"
    synced = "[00:01.00]Blackbird singing\n[00:03.00]\n[00:04.00]in the dead of night\n"

    assert lyrics_text_lines(plain, "plain") == [
        "Blackbird singing",
        "in the dead of night",
    ]
    assert lyrics_text_lines(synced, "synced") == [
        "Blackbird singing",
        "in the dead of night",
    ]


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


def test_a_repeated_chorus_pairs_with_its_own_repetition():
    # difflib's longest-run-first matching paired the text's second chorus
    # with the audio's first, squashing everything between them.
    text = ["hey", "ya", "verse", "one", "hey", "ya", "verse", "two", "hey", "ya"]
    heard = ["hey", "ya", "verse", "one", "hey", "ya", "verse", "too", "hey", "ya"]

    pairs = _longest_common_subsequence(text, heard)

    assert pairs == [(i, i) for i in range(10) if i != 7]


# ---------------------------------------------------------------------------
# plan_retiming
# ---------------------------------------------------------------------------


def test_each_clearly_heard_line_starts_a_chunk():
    lines = ["Blackbird singing", "in the dead of night"]
    asr = _asr(
        ("blackbird", 12.0),
        ("singing", 12.5),
        ("in", 15.0),
        ("the", 15.3),
        ("dead", 15.6),
    )

    plan = plan_retiming(lines, asr)

    assert plan is not None
    assert _chunk_spans(plan) == [(0, 0), (1, 1)]
    assert plan["chunks"][0]["start"] == 12.0 - CHUNK_SLACK_SECONDS
    assert plan["chunks"][0]["end"] == 15.0 + CHUNK_SLACK_SECONDS
    assert plan["chunks"][1]["start"] == 15.0 - CHUNK_SLACK_SECONDS
    assert plan["match_ratio"] == round(5 / 7, 3)
    assert plan["anchor_count"] == 2


def test_matching_ignores_case_and_punctuation():
    plan = plan_retiming(
        ["Don’t stop, believin'!"],
        _asr(("dont", 1.0), ("stop", 1.3), ("believin", 1.6)),
    )

    assert plan is not None
    assert plan["match_ratio"] == 1.0


def test_a_misheard_first_word_backs_the_chunk_up_to_it():
    lines = ["Blackbird singing in the dead"]
    asr = _asr(
        ("blackboard", 12.0),
        ("singing", 12.4),
        ("in", 12.8),
        ("the", 13.0),
        ("dead", 13.3),
    )

    plan = plan_retiming(lines, asr)

    assert plan is not None
    assert plan["chunks"][0]["start"] == round(
        12.4 - WORD_SECONDS - CHUNK_SLACK_SECONDS, 3
    )


def test_lines_asr_misheard_join_the_chunk_before_them():
    lines = ["first line here", "misheard words entirely", "last line here"]
    asr = _asr(
        ("first", 1.0),
        ("line", 1.3),
        ("here", 1.6),
        ("whatever", 5.0),
        ("last", 10.0),
        ("line", 10.3),
    )

    plan = plan_retiming(lines, asr)

    assert plan is not None
    # The middle line is aligned somewhere between the two heard lines.
    assert _chunk_spans(plan) == [(0, 1), (2, 2)]
    assert plan["chunks"][0]["end"] == 10.0 + CHUNK_SLACK_SECONDS


def test_lines_before_the_first_heard_line_get_a_chunk_from_the_start():
    lines = ["unheard intro words", "the chorus starts here"]
    asr = _asr(("the", 20.0), ("chorus", 20.3), ("starts", 20.6))

    plan = plan_retiming(lines, asr)

    assert plan is not None
    assert _chunk_spans(plan) == [(0, 0), (1, 1)]
    assert plan["chunks"][0]["start"] == 0.0


def test_low_confidence_asr_words_dont_cut_chunks():
    # Where ASR squeezes a verse into a few seconds, its word scores are low.
    lines = ["I journey through the desert", "of the mind", "I drift along the ocean"]
    asr = _asr(("i", 99.8), ("journey", 100.0), ("through", 101.4)) + _asr(
        ("of", 102.7),
        ("the", 102.9),
        ("mind", 103.3),
        ("i", 106.1),
        ("drift", 106.1),
        score=0.2,
    )

    plan = plan_retiming(lines, asr)

    assert plan is not None
    assert _chunk_spans(plan) == [(0, 2)]
    assert plan["anchor_count"] == 1


def test_a_single_common_word_doesnt_make_a_line_clearly_heard():
    lines = ["first line here", "and the other", "last line here"]
    asr = _asr(
        ("first", 1.0),
        ("line", 1.3),
        ("here", 1.6),
        ("the", 5.0),
        ("last", 10.0),
        ("line", 10.3),
    )

    plan = plan_retiming(lines, asr)

    assert plan is not None
    assert _chunk_spans(plan) == [(0, 1), (2, 2)]


def test_untimed_asr_words_dont_count_as_heard():
    asr = [
        {"word": "twenty", "start": 3.0, "end": 3.0, "score": 0.0},
        {"word": "two", "start": 4.0, "end": 4.3, "score": 0.9},
        {"word": "birds", "start": 4.4, "end": 4.7, "score": 0.9},
    ]

    plan = plan_retiming(["twenty two birds"], asr)

    assert plan is not None
    assert plan["match_ratio"] == round(2 / 3, 3)


def test_lyrics_of_another_song_match_poorly():
    lines = ["completely different words", "from some other song"]
    asr = _asr(
        ("blackbird", 1.0),
        ("singing", 1.3),
        ("in", 1.6),
        ("the", 1.9),
        ("dead", 2.2),
        ("of", 2.5),
    )

    plan = plan_retiming(lines, asr)

    assert plan is None or plan["match_ratio"] < 0.5


def test_nothing_clearly_heard_returns_none():
    assert plan_retiming([], _asr(("hello", 1.0))) is None
    assert plan_retiming(["hello"], []) is None
    assert plan_retiming(["hello"], _asr(("goodbye", 1.0))) is None


# ---------------------------------------------------------------------------
# lrc_from_aligned_lines
# ---------------------------------------------------------------------------


def _word(word: str, start: float, line_index: int) -> AlignedWord:
    return AlignedWord(
        word=word, start=start, end=start + 0.3, score=0.8, line_index=line_index
    )


def test_lines_start_just_before_their_first_aligned_word():
    lines = ["Blackbird singing", "in the dead"]
    words = [
        _word("Blackbird", 12.0, 0),
        _word("singing", 12.5, 0),
        _word("in", 15.0, 1),
    ]

    lrc = lrc_from_aligned_lines(lines, words)

    assert lrc is not None
    parsed = parse_lrc_lines(lrc)
    assert [line["text"] for line in parsed] == lines
    assert [line["timestamp"] for line in parsed] == [
        12.0 - LEAD_IN_SECONDS,
        15.0 - LEAD_IN_SECONDS,
    ]


def test_a_line_with_no_aligned_words_follows_the_line_before():
    lines = ["first line", "1999", "last line"]
    words = [_word("first", 1.0, 0), _word("line", 1.4, 0), _word("last", 10.0, 2)]

    lrc = lrc_from_aligned_lines(lines, words)

    assert lrc is not None
    assert [line["timestamp"] for line in parse_lrc_lines(lrc)] == [0.75, 1.7, 9.75]


def test_lines_never_overlap_or_go_backwards():
    lines = ["one two", "three"]
    # The aligner put the second line's first word before the first line ended.
    words = [_word("one", 1.0, 0), _word("two", 1.5, 0), _word("three", 1.6, 1)]

    lrc = lrc_from_aligned_lines(lines, words)

    assert lrc is not None
    assert [line["timestamp"] for line in parse_lrc_lines(lrc)] == [0.75, 1.8]


def test_no_aligned_words_returns_none():
    assert lrc_from_aligned_lines(["hello"], []) is None


# ---------------------------------------------------------------------------
# lyrics_words_key
# ---------------------------------------------------------------------------


def test_words_key_ignores_timestamps_punctuation_case_blanks_and_headers():
    from app.services.lyrics_retiming import lyrics_words_key

    synced = (
        "[00:01.00]Blackbird singing,\n[00:03.00]\n[00:04.00]In the dead of night!\n"
    )
    plain = "[Verse 1]\nblackbird singing\n\nin the DEAD of night\n"

    assert lyrics_words_key(synced, "synced") == lyrics_words_key(plain, "plain")


def test_words_key_differs_for_different_words():
    from app.services.lyrics_retiming import lyrics_words_key

    assert lyrics_words_key("Blackbird singing", "plain") != lyrics_words_key(
        "Blackbird flying", "plain"
    )


def test_words_key_is_none_without_words():
    from app.services.lyrics_retiming import lyrics_words_key

    assert lyrics_words_key("\n[Chorus]\n...\n", "plain") is None
