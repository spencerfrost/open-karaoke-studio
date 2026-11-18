"""Finding a fixed lyrics line again, and putting the fix back on it."""

from dataclasses import dataclass
from typing import Optional

from app.services.lyrics_analysis import parse_lrc_lines
from app.services.lyrics_line_fixes import (
    anchor_for_line,
    apply_fixes_to_attempts,
    apply_line_fixes,
    carry_line_words,
    find_shown_line,
    fix_is_shown,
    line_key,
    line_window,
    locate_fix,
    replace_line_words,
)
from app.services.lyrics_retiming import lyrics_words_key

SONG = "\n".join(
    [
        "[00:10.00]Is this the real life",
        "[00:14.00]Is this just fantasy",
        "[00:18.00]Caught in a landslide",
        "[00:22.00]No escape from reality",
    ]
)

# A chorus sung twice: the second "Mama oooh" is the one that's wrong.
CHORUS = "\n".join(
    [
        "[00:30.00]Mama just killed a man",
        "[00:34.00]Mama oooh",
        "[00:38.00]Didn't mean to make you cry",
        "[01:30.00]Mama just killed a man",
        "[01:34.00]Mama oooh",
        "[01:38.00]Didn't mean to make you cry",
    ]
)


@dataclass
class Fix:
    old_text: str
    new_text: str
    line_start: Optional[float]
    prev_text: Optional[str]
    next_text: Optional[str]
    occurrence: int


def _fix(content: str, line_start: float, old: str, new: str) -> Fix:
    index = find_shown_line(content, line_start=line_start, text=old)
    assert index is not None
    anchor = anchor_for_line(content, index, reads=[old, new])
    return Fix(
        old_text=old,
        new_text=new,
        line_start=line_start,
        prev_text=anchor.prev_text,
        next_text=anchor.next_text,
        occurrence=anchor.occurrence,
    )


def _texts(content: str) -> list[str]:
    return [line["text"] for line in parse_lrc_lines(content)]


def test_line_key_ignores_case_and_punctuation():
    assert line_key("Is this the REAL life?") == "is this the real life"
    assert line_key("  ") == ""


def test_find_shown_line_needs_both_time_and_text():
    assert find_shown_line(SONG, line_start=14.0, text="Is this just fantasy") == 1
    assert find_shown_line(SONG, line_start=14.0, text="Is this the real life") is None
    assert find_shown_line(SONG, line_start=15.0, text="Is this just fantasy") is None


def test_a_fix_replaces_its_line_and_keeps_the_timestamp():
    fix = _fix(SONG, 14.0, "Is this just fantasy", "Is this just fantasy?")
    fixed = apply_line_fixes(SONG, [fix])
    assert fixed is not None
    assert "[00:14.00]Is this just fantasy?" in fixed.splitlines()
    assert _texts(fixed)[0] == "Is this the real life"


def test_unchanged_text_is_returned_as_is():
    fix = _fix(SONG, 14.0, "Is this just fantasy", "Is it just fantasy")
    fixed = apply_line_fixes(SONG, [fix])
    assert apply_line_fixes(fixed, [fix]) is fixed


def test_a_fix_survives_a_re_time_that_moves_every_line():
    fix = _fix(SONG, 18.0, "Caught in a landslide", "Caught in a landslide, no")
    retimed = SONG.replace("[00:1", "[00:4").replace("[00:2", "[00:5")
    fixed = apply_line_fixes(retimed, [fix])
    assert fixed is not None
    assert _texts(fixed)[2] == "Caught in a landslide, no"


def test_a_fix_survives_break_lines_being_inserted():
    fix = _fix(SONG, 18.0, "Caught in a landslide", "Caught in a landslide, no")
    with_breaks = SONG.replace("[00:18.00]Caught", "[00:16.00]\n[00:18.00]Caught")
    fixed = apply_line_fixes(with_breaks, [fix])
    assert fixed is not None
    assert _texts(fixed)[3] == "Caught in a landslide, no"
    assert _texts(fixed)[2] == ""


def test_a_repeated_line_fix_stays_on_the_one_that_was_fixed():
    fix = _fix(CHORUS, 94.0, "Mama oooh", "Mama, ooh")
    fixed = apply_line_fixes(CHORUS, [fix])
    assert fixed is not None
    assert _texts(fixed)[1] == "Mama oooh"
    assert _texts(fixed)[4] == "Mama, ooh"
    # Applying again finds the fixed line, not the other "Mama oooh".
    again = apply_line_fixes(fixed, [fix])
    assert _texts(again or "")[1] == "Mama oooh"


def test_a_repeated_line_fix_holds_after_everything_shifts():
    fix = _fix(CHORUS, 94.0, "Mama oooh", "Mama, ooh")
    fixed = apply_line_fixes(CHORUS, [fix]) or ""
    shifted = fixed.replace("[00:3", "[00:4").replace("[01:3", "[01:0")
    again = apply_line_fixes(shifted, [fix])
    assert _texts(again or "")[1] == "Mama oooh"
    assert _texts(again or "")[4] == "Mama, ooh"


def test_a_fix_whose_line_is_gone_is_lost_and_changes_nothing():
    fix = _fix(SONG, 18.0, "Caught in a landslide", "Caught in a landslide, no")
    other = "[00:10.00]Different words entirely\n[00:12.00]Nothing alike"
    assert locate_fix(other, fix) is None
    assert apply_line_fixes(other, [fix]) is other
    assert fix_is_shown(other, fix) is False


def test_fix_is_shown_only_while_the_fixed_text_is_on_screen():
    fix = _fix(SONG, 18.0, "Caught in a landslide", "Caught in a landslide, no")
    assert fix_is_shown(SONG, fix) is False
    assert fix_is_shown(apply_line_fixes(SONG, [fix]), fix) is True


def test_plain_lyrics_take_the_fix_too():
    plain = "\n".join(_texts(SONG))
    fix = _fix(SONG, 18.0, "Caught in a landslide", "Caught in a landslide, no")
    fixed = apply_line_fixes(plain, [fix], "plain")
    assert (fixed or "").splitlines()[2] == "Caught in a landslide, no"


def test_attempts_get_fixes_and_rejected_fixed_text_is_dropped():
    fix = _fix(SONG, 18.0, "Caught in a landslide", "Caught in a landslide, no")
    fixed_text = apply_line_fixes(SONG, [fix]) or ""
    attempts = [
        {"content": SONG, "source_type": "synced", "source": "db:synced"},
        {"content": SONG, "source_type": "synced", "source": "lrclib:1"},
    ]
    result = apply_fixes_to_attempts(attempts, [fix])
    assert [a["source"] for a in result] == ["db:synced"]
    assert result[0]["content"] == fixed_text

    rejected = {lyrics_words_key(fixed_text, "synced") or ""}
    assert apply_fixes_to_attempts(attempts, [fix], rejected) == []


def test_window_runs_from_the_previous_lines_end_to_the_next_lines_start():
    lines = parse_lrc_lines(SONG)
    words = [
        {"word": "real", "start": 10.2, "end": 12.5, "score": 0.9, "line_index": 0},
        {
            "word": "landslide",
            "start": 18.4,
            "end": 19.0,
            "score": 0.9,
            "line_index": 2,
        },
    ]
    assert line_window(lines, words, 1) == (12.5, 18.4)
    # No words on the previous line: the line's own time opens the window,
    # and a next line without words closes it at its LRC time.
    assert line_window(lines, words, 2) == (18.0, 22.0)
    # The last line runs a few seconds past its time, never past the song.
    assert line_window(lines, words, 3) == (19.0, 32.0)
    assert line_window(lines, words, 3, song_duration=25.0) == (19.0, 25.0)
    assert line_window(lines, [], 0) == (5.0, 14.0)


def test_replacing_a_lines_words_keeps_line_order():
    payload = {
        "words": [
            {"word": "a", "start": 1.0, "end": 1.5, "score": 0.9, "line_index": 0},
            {"word": "b", "start": 5.0, "end": 5.5, "score": 0.5, "line_index": 1},
            {"word": "c", "start": 9.0, "end": 9.5, "score": 0.9, "line_index": 2},
        ],
        "aligned_at": "2026-11-11T00:00:00",
        "lyrics_source": "db:synced",
    }
    patched = replace_line_words(
        payload,
        1,
        [
            {"word": "x", "start": 4.0, "end": 4.4, "score": 0.7, "line_index": 0},
            {"word": "y", "start": 4.5, "end": 5.0, "score": 0.7, "line_index": 0},
        ],
    )
    assert [w["word"] for w in patched["words"]] == ["a", "x", "y", "c"]
    assert [w["line_index"] for w in patched["words"]] == [0, 1, 1, 2]
    assert patched["word_count"] == 4
    assert patched["lyrics_source"] == "db:synced"
    emptied = replace_line_words(payload, 1, [])
    assert [w["word"] for w in emptied["words"]] == ["a", "c"]


def test_carried_words_keep_their_own_times_when_the_count_is_the_same():
    payload = {
        "words": [
            {"word": "a", "start": 1.0, "end": 1.5, "score": 0.9, "line_index": 0},
            {"word": "bee", "start": 5.0, "end": 5.5, "score": 0.5, "line_index": 1},
            {"word": "sea", "start": 5.5, "end": 7.0, "score": 0.6, "line_index": 1},
        ]
    }
    words, same_words = carry_line_words(payload, 1, "be sea")
    assert [(w["word"], w["start"], w["end"]) for w in words] == [
        ("be", 5.0, 5.5),
        ("sea", 5.5, 7.0),
    ]
    assert same_words is False
    assert carry_line_words(payload, 1, "Bee, sea!")[1] is True


def test_carried_words_share_the_lines_span_when_the_count_changes():
    payload = {
        "words": [
            {"word": "bee", "start": 5.0, "end": 5.5, "score": 0.5, "line_index": 1},
            {"word": "sea", "start": 5.5, "end": 7.0, "score": 0.6, "line_index": 1},
        ]
    }
    words, same_words = carry_line_words(payload, 1, "be at the sea")
    assert [(w["start"], w["end"]) for w in words] == [
        (5.0, 5.5),
        (5.5, 6.0),
        (6.0, 6.5),
        (6.5, 7.0),
    ]
    assert same_words is False
    assert carry_line_words(payload, 0, "nothing here") == ([], False)


def test_an_anchored_match_needs_a_neighbour_or_the_same_time():
    fix = _fix(SONG, 14.0, "Is this just fantasy", "Is this just a fantasy")
    elsewhere = "[00:40.00]Mama\n[00:44.00]Is this just fantasy\n[00:48.00]Oooh"
    assert locate_fix(elsewhere, fix) == 1
    assert locate_fix(elsewhere, fix, anchored=True) is None
    assert locate_fix(SONG, fix, anchored=True) == 1
