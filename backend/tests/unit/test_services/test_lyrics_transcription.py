from time import perf_counter
from unittest.mock import patch

from app.services.lyrics_transcription import _build_transcription_result


def _build(segments):
    with patch("app.services.lyrics_transcription.log_lyrics_event"):
        return _build_transcription_result(
            song_id="song-1",
            segments=segments,
            language="en",
            provider="whisperx",
            model_name="large-v3",
            started_at=perf_counter(),
        )


def _word(text, start=None, end=None, score=0.9):
    word = {"word": text}
    if start is not None:
        word.update(start=start, end=end, score=score)
    return word


def test_untimed_words_stay_in_the_line_and_the_word_list():
    result = _build(
        [
            {
                "start": 5.0,
                "text": "Back in 1990 we sang",
                "words": [
                    _word("Back", 5.0, 5.3),
                    _word("in", 5.3, 5.5),
                    _word("1990"),
                    _word("we", 6.0, 6.2),
                    _word("sang", 6.2, 6.8),
                ],
            }
        ]
    )

    assert result is not None
    assert result["synced_lyrics"] == "[00:05.00]Back in 1990 we sang"
    untimed = result["alignment"]["words"][2]
    assert untimed == {
        "word": "1990",
        "start": 5.5,
        "end": 5.5,
        "score": 0.0,
        "line_index": 0,
    }


def test_punctuation_words_are_attached_to_the_word_before():
    result = _build(
        [
            {
                "start": 1.0,
                "text": "Hello , world !",
                "words": [
                    _word("Hello", 1.0, 1.4),
                    _word(","),
                    _word("world", 1.5, 2.0),
                    _word("!"),
                ],
            }
        ]
    )

    assert result is not None
    assert result["plain_lyrics"] == "Hello, world!"
    assert [w["word"] for w in result["alignment"]["words"]] == ["Hello,", "world!"]


def test_line_indexes_count_only_lines_that_reach_the_synced_lyrics():
    result = _build(
        [
            {
                "start": 1.0,
                "text": "first line",
                "words": [_word("first", 1.0, 1.2), _word("line", 1.2, 1.5)],
            },
            {"start": None, "text": "no timestamp", "words": []},
            {"start": 3.0, "text": "   ", "words": []},
            {
                "start": 4.0,
                "text": "second line",
                "words": [_word("second", 4.0, 4.3), _word("line", 4.3, 4.6)],
            },
        ]
    )

    assert result is not None
    assert result["synced_lyrics"].splitlines() == [
        "[00:01.00]first line",
        "[00:04.00]second line",
    ]
    assert [w["line_index"] for w in result["alignment"]["words"]] == [0, 0, 1, 1]
