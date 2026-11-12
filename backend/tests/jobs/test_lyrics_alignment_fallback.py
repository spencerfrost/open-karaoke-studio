"""Tests for ASR fallback behavior in lyrics alignment."""

import json
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from app.jobs.lyrics_tasks import align_song_lyrics

SONG_ID = "song-lyrics-asr-123"


def _asr_transcription(*words: str) -> dict:
    return {
        "plain_lyrics": " ".join(words),
        "synced_lyrics": "[00:01.00]" + " ".join(words),
        "alignment": {
            "words": [
                {
                    "word": word,
                    "start": 1.0 + i * 0.4,
                    "end": 1.3 + i * 0.4,
                    "score": 0.9,
                    "line_index": 0,
                }
                for i, word in enumerate(words)
            ],
            "instrumental_intervals": [],
            "language": "en",
            "aligned_at": "2026-09-30T00:00:00+00:00",
            "word_count": len(words),
            "line_count": 1,
            "mean_score": 0.9,
        },
        "asr_provider": "whisperx",
        "asr_model": "small",
    }


def _alignment_of(*words: str, score: float = 0.8) -> dict:
    return {
        "words": [
            {
                "word": word,
                "start": 1.0 + i * 0.4,
                "end": 1.3 + i * 0.4,
                "score": score,
                "line_index": 0,
            }
            for i, word in enumerate(words)
        ],
        "instrumental_intervals": [],
        "language": "en",
        "aligned_at": "2026-09-30T00:00:00+00:00",
        "word_count": len(words),
        "line_count": 1,
        "mean_score": score,
    }


def _attempt(content, source_type):
    return {
        "content": content,
        "source_type": source_type,
        "source": f"db:{source_type}",
        "persist": False,
    }


@pytest.fixture
def vocals(library):
    """A vocals stem on disk; the models that would read it are patched per test."""
    song_dir = library / SONG_ID
    song_dir.mkdir()
    (song_dir / "vocals.mp3").write_bytes(b"fake")


@pytest.fixture
def job_progress():
    """Job progress publishes events; the song row is what these tests check."""
    with (
        patch("app.jobs.lyrics_tasks._update_lyrics_alignment_job") as update,
        patch("app.jobs.lyrics_tasks._complete_lyrics_alignment_job") as complete,
    ):
        yield update, complete


def _run(
    attempts,
    *,
    transcription,
    attempt_alignment=None,
    chunked=None,
    retimed=None,
):
    """Run align_song_lyrics with the candidate lookup and every model patched."""
    with ExitStack() as stack:
        mocks = {
            "transcribe": stack.enter_context(
                patch(
                    "app.services.lyrics_transcription.transcribe_lyrics_from_vocals",
                    return_value=transcription,
                )
            ),
            "align_chunks": stack.enter_context(
                patch(
                    "app.services.lyrics_alignment.align_line_chunks",
                    return_value=chunked,
                )
            ),
            "align": stack.enter_context(
                patch(
                    "app.services.lyrics_alignment.align_lyrics_to_vocals",
                    return_value=retimed,
                )
            ),
            "run_alignment": stack.enter_context(
                patch(
                    "app.jobs.lyrics_tasks.run_alignment_attempt",
                    return_value=attempt_alignment,
                )
            ),
        }
        stack.enter_context(
            patch(
                "app.jobs.lyrics_tasks._build_alignment_attempts",
                return_value=attempts,
            )
        )
        stack.enter_context(
            patch("app.jobs.lyrics_tasks._apply_offset_correction", return_value=None)
        )
        result = align_song_lyrics(SONG_ID)
    return result, mocks


def test_align_song_lyrics_uses_asr_fallback_when_no_candidates(
    add_song, fetch_song, vocals, job_progress
):
    add_song(SONG_ID, language="en")
    transcription = _asr_transcription("hello", "world")
    transcription.pop("asr_provider")
    transcription.pop("asr_model")

    result, mocks = _run([], transcription=transcription)

    assert result["status"] == "ok"
    assert result["song_id"] == SONG_ID
    assert result["source"] == "asr:whisperx"
    assert result["fallback_reason"] == "no_candidates"
    assert result["asr_provider"] == "whisperx"
    assert result["asr_model"] == "unknown"
    saved = fetch_song(SONG_ID)
    assert saved.plain_lyrics == "hello world"
    assert saved.synced_lyrics == "[00:01.00]hello world"
    stored = json.loads(saved.word_synced_lyrics)
    assert [word["word"] for word in stored["words"]] == ["hello", "world"]
    mocks["transcribe"].assert_called_once()
    update, complete = job_progress
    update.assert_called()
    complete.assert_called_once()


def test_low_confidence_lyrics_are_never_replaced_by_a_transcript(
    add_song, fetch_song, vocals, job_progress
):
    add_song(
        SONG_ID,
        language="en",
        plain_lyrics="old plain lyrics",
        synced_lyrics="[00:00.00]old synced lyrics",
    )

    result, mocks = _run(
        [_attempt("[00:00.00]old synced lyrics", "synced")],
        attempt_alignment=_alignment_of("old", "synced", "lyrics", score=0.2),
        transcription=_asr_transcription("new", "asr"),
    )

    # ASR heard different words, so it can't time these lyrics, and its
    # transcript doesn't replace them: they stay, scrolling line by line.
    assert result["status"] == "low_confidence"
    saved = fetch_song(SONG_ID)
    assert saved.plain_lyrics == "old plain lyrics"
    assert saved.synced_lyrics == "[00:00.00]old synced lyrics"
    assert saved.word_synced_lyrics is None
    mocks["run_alignment"].assert_called_once()
    mocks["transcribe"].assert_called_once()
    _, complete = job_progress
    complete.assert_called_once()


def _run_plain_only(add_song, transcription, alignment=None, chunked=None):
    """Run align_song_lyrics for a song whose only candidate is plain lyrics."""
    add_song(SONG_ID, language="en", plain_lyrics="Human plain lyrics")

    result, mocks = _run(
        [_attempt("Human plain lyrics", "plain")],
        transcription=transcription,
        chunked=chunked,
        retimed=alignment,
    )

    # Plain lyrics are never force-aligned as they are.
    mocks["run_alignment"].assert_not_called()
    return result, mocks["align_chunks"], mocks["align"]


def test_plain_lyrics_are_timed_from_asr_and_keep_their_words(
    add_song, fetch_song, vocals, job_progress
):
    result, mock_align_chunks, mock_align = _run_plain_only(
        add_song,
        _asr_transcription("human", "plain", "lyrics"),
        _alignment_of("Human", "plain", "lyrics"),
        chunked=_alignment_of("Human", "plain", "lyrics"),
    )

    assert result["status"] == "retimed"
    assert result["reason"] == "plain_only"
    # ASR heard the line, so it gets its own chunk around where it was sung.
    lines, chunks = mock_align_chunks.call_args.args[:2]
    assert lines == ["Human plain lyrics"]
    assert [(chunk["first_line"], chunk["last_line"]) for chunk in chunks] == [(0, 0)]
    # The LRC aligned for real is the plain text, timed where the chunk alignment put it.
    aligned_lrc = mock_align.call_args.args[0]
    assert aligned_lrc == "[00:00.75]Human plain lyrics"
    saved = fetch_song(SONG_ID)
    assert saved.synced_lyrics == aligned_lrc
    assert saved.plain_lyrics == "Human plain lyrics"
    stored = json.loads(saved.word_synced_lyrics)
    assert [word["word"] for word in stored["words"]] == ["Human", "plain", "lyrics"]
    assert stored["lyrics_source_type"] == "synced"
    assert stored["retimed_from"] == "plain"
    assert stored["retimed_by"] == "asr:whisperx"


def test_plain_lyrics_stay_untimed_when_the_singing_is_different_words(
    add_song, fetch_song, vocals, job_progress
):
    result, mock_align_chunks, mock_align = _run_plain_only(
        add_song, _asr_transcription("something", "else", "entirely")
    )

    assert result == {"status": "plain_only", "song_id": SONG_ID}
    mock_align_chunks.assert_not_called()
    mock_align.assert_not_called()
    saved = fetch_song(SONG_ID)
    assert saved.plain_lyrics == "Human plain lyrics"
    assert saved.synced_lyrics is None
    assert saved.word_synced_lyrics is None


def test_plain_lyrics_stay_untimed_when_the_retimed_alignment_scores_low(
    add_song, fetch_song, vocals, job_progress
):
    result, _, _ = _run_plain_only(
        add_song,
        _asr_transcription("human", "plain", "lyrics"),
        _alignment_of("Human", "plain", "lyrics", score=0.1),
        chunked=_alignment_of("Human", "plain", "lyrics", score=0.1),
    )

    assert result == {"status": "plain_only", "song_id": SONG_ID}
    saved = fetch_song(SONG_ID)
    assert saved.synced_lyrics is None
    assert saved.word_synced_lyrics is None


def test_plain_lyrics_stay_untimed_when_asr_is_unavailable(
    add_song, fetch_song, vocals, job_progress
):
    result, mock_align_chunks, mock_align = _run_plain_only(add_song, None)

    assert result == {"status": "plain_only", "song_id": SONG_ID}
    mock_align_chunks.assert_not_called()
    mock_align.assert_not_called()
    saved = fetch_song(SONG_ID)
    assert saved.plain_lyrics == "Human plain lyrics"
    assert saved.synced_lyrics is None
    assert saved.word_synced_lyrics is None


def test_low_confidence_synced_lyrics_are_retimed_with_their_own_words(
    add_song, fetch_song, vocals, job_progress
):
    add_song(
        SONG_ID,
        language="en",
        plain_lyrics="old plain lyrics",
        synced_lyrics="[00:30.00]old synced lyrics",
    )

    result, _ = _run(
        [_attempt("[00:30.00]old synced lyrics", "synced")],
        attempt_alignment=_alignment_of("old", "synced", "lyrics", score=0.1),
        transcription=_asr_transcription("old", "synced", "lyrics"),
        chunked=_alignment_of("old", "synced", "lyrics"),
        retimed=_alignment_of("old", "synced", "lyrics"),
    )

    assert result["status"] == "retimed"
    assert result["reason"] == "low_confidence"
    # Same words, new time: the LRC's 0:30 was wrong, the singing starts at 0:01.
    saved = fetch_song(SONG_ID)
    assert saved.synced_lyrics == "[00:00.75]old synced lyrics"
    assert saved.plain_lyrics == "old plain lyrics"
    stored = json.loads(saved.word_synced_lyrics)
    assert stored["retimed_from"] == "synced"
