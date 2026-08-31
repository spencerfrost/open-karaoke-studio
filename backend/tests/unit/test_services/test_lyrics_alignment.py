from app.services.lyrics_alignment import (
    AlignedWord,
    _assign_line_indices,
    _assign_line_indices_by_segment_position,
    _build_instrumental_intervals,
    _content_line_indices,
    _segments_to_input_tokens,
    recompute_alignment_line_indices,
)
from app.services.lyrics_analysis import parse_lrc_lines


def _output_word(text, start, score=0.9):
    return {"word": text, "start": start, "end": start + 0.3, "score": score}


# ---------------------------------------------------------------------------
# _assign_line_indices — the token-position walk
# ---------------------------------------------------------------------------


def test_assign_line_indices_survives_a_mid_line_segment_split():
    """
    Regression for the 'Hold On' bug: WhisperX split one input line into two
    output segments (its sentence-splitter treats mid-line text as a sentence
    boundary). The old seg_idx -> line_index mapping shifted every line index
    after the split; the token walk must not.
    """
    segments = [
        {"text": "Why do people lock themselves up in chains"},
        {"text": "No one can change your fate"},
        {"text": "Dont ever let anyone stop your dreams"},
    ]
    input_tokens = _segments_to_input_tokens(segments, line_indices=[0, 1, 2])

    # WhisperX splits line 0's segment into two output segments.
    result_segments = [
        {
            "words": [
                _output_word(w, i * 0.3)
                for i, w in enumerate(["Why", "do", "people", "lock"])
            ]
        },
        {
            "words": [
                _output_word(w, (4 + i) * 0.3)
                for i, w in enumerate(["themselves", "up", "in", "chains"])
            ]
        },
        {
            "words": [
                _output_word(w, (8 + i) * 0.3)
                for i, w in enumerate(["No", "one", "can", "change", "your", "fate"])
            ]
        },
        {
            "words": [
                _output_word(w, (14 + i) * 0.3)
                for i, w in enumerate(
                    ["Dont", "ever", "let", "anyone", "stop", "your", "dreams"]
                )
            ]
        },
    ]

    aligned = _assign_line_indices(result_segments, input_tokens)

    assert aligned is not None
    by_word = {w["word"]: w["line_index"] for w in aligned}
    assert by_word["Why"] == 0
    assert by_word["chains"] == 0  # split subsegment still belongs to line 0
    assert by_word["No"] == 1
    assert by_word["fate"] == 1
    assert by_word["Dont"] == 2
    assert by_word["dreams"] == 2


def test_assign_line_indices_survives_merged_subsegments():
    """WhisperX's groupby can merge subsegments sharing (start, end) into one
    output segment. Since the walk is purely positional across the flattened
    word list, a merge shouldn't matter either."""
    segments = [
        {"text": "Short line one"},
        {"text": "Short line two"},
    ]
    input_tokens = _segments_to_input_tokens(segments, line_indices=[0, 1])

    # Both lines' words land in a single merged output segment.
    result_segments = [
        {
            "words": [
                _output_word(w, i * 0.3)
                for i, w in enumerate(["Short", "line", "one", "Short", "line", "two"])
            ]
        }
    ]

    aligned = _assign_line_indices(result_segments, input_tokens)

    assert aligned is not None
    assert [w["line_index"] for w in aligned] == [0, 0, 0, 1, 1, 1]


def test_assign_line_indices_mismatch_falls_back_safely():
    """A token-walk divergence must not silently store a bad mapping — it
    should be detected and reported via None so the caller can fall back."""
    segments = [{"text": "Hello world"}]
    input_tokens = _segments_to_input_tokens(segments, line_indices=[0])

    result_segments = [
        {"words": [_output_word("Goodbye", 0.0), _output_word("world", 0.3)]}
    ]

    aligned = _assign_line_indices(result_segments, input_tokens)

    assert aligned is None


def test_assign_line_indices_by_segment_position_is_the_old_behaviour():
    """The fallback exists purely so a divergence can't store data worse than
    before this fix — it should reproduce the previous seg_idx-based mapping."""
    result_segments = [
        {"words": [_output_word("Why", 0.0)]},
        {"words": [_output_word("chains", 0.3)]},
    ]

    aligned = _assign_line_indices_by_segment_position(
        result_segments, line_indices=[0, 1]
    )

    assert [w["line_index"] for w in aligned] == [0, 1]


# ---------------------------------------------------------------------------
# Blank lines never receive words
# ---------------------------------------------------------------------------


def test_blank_lrc_lines_are_excluded_from_content_line_indices():
    lrc = "[00:01.00]First line\n[00:02.00]\n[00:03.00]Second line\n"
    lrc_lines = parse_lrc_lines(lrc)

    content_indices = _content_line_indices(lrc_lines)

    # Position 1 (the blank line) must never appear as a source-line index.
    assert content_indices == [0, 2]


def test_assign_line_indices_never_targets_a_blank_line():
    lrc = "[00:01.00]First line\n[00:02.00]\n[00:03.00]Second line\n"
    lrc_lines = parse_lrc_lines(lrc)
    content_indices = _content_line_indices(lrc_lines)
    content_lines = [l for l in lrc_lines if l["text"].strip()]

    segments = [{"text": l["text"].strip()} for l in content_lines]
    input_tokens = _segments_to_input_tokens(segments, content_indices)

    result_segments = [
        {"words": [_output_word(w, i * 0.3) for i, w in enumerate(["First", "line"])]},
        {
            "words": [
                _output_word(w, (2 + i) * 0.3) for i, w in enumerate(["Second", "line"])
            ]
        },
    ]

    aligned = _assign_line_indices(result_segments, input_tokens)

    assert aligned is not None
    assert all(w["line_index"] != 1 for w in aligned)


# ---------------------------------------------------------------------------
# _build_instrumental_intervals — one rule, no intro special case
# ---------------------------------------------------------------------------


def test_intro_gap_and_identical_mid_song_gap_get_the_same_decision():
    words = [
        AlignedWord(word="Hello", start=5.0, end=5.5, score=0.9, line_index=0),
        AlignedWord(word="there", start=5.5, end=6.0, score=0.9, line_index=0),
        # Gap of 5.0s before this word — same duration as the intro gap above.
        AlignedWord(word="World", start=11.0, end=11.5, score=0.9, line_index=1),
    ]

    below_threshold = _build_instrumental_intervals(
        words, min_gap_seconds=6.0, lead_in_seconds=1.5
    )
    assert below_threshold == []  # both gaps are 5.0s, unified threshold is 6.0s

    above_threshold = _build_instrumental_intervals(
        words, min_gap_seconds=4.0, lead_in_seconds=1.5
    )
    assert {i["next_line_index"] for i in above_threshold} == {0, 1}
    durations = {i["duration"] for i in above_threshold}
    assert durations == {5.0}


def test_instrumental_interval_names_the_line_that_starts_at_its_end():
    words = [
        AlignedWord(word="Hello", start=6.5, end=7.0, score=0.9, line_index=0),
        AlignedWord(word="World", start=14.0, end=14.5, score=0.9, line_index=1),
    ]

    intervals = _build_instrumental_intervals(
        words, min_gap_seconds=6.0, lead_in_seconds=1.5
    )

    assert (
        len(intervals) == 2
    )  # intro before "Hello" and the mid-song gap before "World"
    for interval in intervals:
        next_word = next(
            w for w in words if w["line_index"] == interval["next_line_index"]
        )
        assert next_word["start"] == interval["end"]


# ---------------------------------------------------------------------------
# recompute_alignment_line_indices — the offline backfill path
# ---------------------------------------------------------------------------


def test_recompute_line_indices_from_stored_words_synced():
    lrc = "[00:01.00]First line here\n[00:02.00]\n[00:03.00]Second line here\n"
    words = [
        AlignedWord(word=w, start=i * 0.3, end=i * 0.3 + 0.3, score=0.9, line_index=99)
        for i, w in enumerate(["First", "line", "here", "Second", "line", "here"])
    ]

    recomputed = recompute_alignment_line_indices(words, source_type="synced", content=lrc)

    assert recomputed is not None
    assert [w["line_index"] for w in recomputed] == [0, 0, 0, 2, 2, 2]
    # Timings are untouched — only the label changes.
    assert [w["start"] for w in recomputed] == [w["start"] for w in words]


def test_recompute_line_indices_from_stored_words_plain():
    plain = "First line here\n[Chorus]\nSecond line here\n"
    words = [
        AlignedWord(word=w, start=i * 0.3, end=i * 0.3 + 0.3, score=0.9, line_index=99)
        for i, w in enumerate(["First", "line", "here", "Second", "line", "here"])
    ]

    recomputed = recompute_alignment_line_indices(words, source_type="plain", content=plain)

    assert recomputed is not None
    assert [w["line_index"] for w in recomputed] == [0, 0, 0, 1, 1, 1]


def test_recompute_line_indices_returns_none_on_divergence():
    lrc = "[00:01.00]First line here\n"
    words = [
        AlignedWord(word=w, start=i * 0.3, end=i * 0.3 + 0.3, score=0.9, line_index=0)
        for i, w in enumerate(["Totally", "different", "words"])
    ]

    assert recompute_alignment_line_indices(words, source_type="synced", content=lrc) is None
