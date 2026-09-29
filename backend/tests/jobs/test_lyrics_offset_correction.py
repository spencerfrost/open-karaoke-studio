"""Tests for shifting low-confidence synced lyrics onto the vocals."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.jobs.lyrics_tasks import _offset_rejection_reason, align_song_lyrics

SONG_ID = "song-lyrics-offset-123"
LATE_LRC = "[00:12.00]hello world\n[00:16.00]second line here"


def _make_db_context(mock_session=None):
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=mock_session or MagicMock())
    ctx.__exit__ = Mock(return_value=False)
    return ctx


def _alignment(mean_score, line_indices=(0, 0, 1, 1, 1)):
    words = ["hello", "world", "second", "line", "here"]
    return {
        "words": [
            {"word": w, "start": float(i), "end": i + 0.4, "score": mean_score, "line_index": line}
            for i, (w, line) in enumerate(zip(words, line_indices))
        ],
        "instrumental_intervals": [],
        "language": "en",
        "aligned_at": "2026-09-29T00:00:00+00:00",
        "word_count": len(words),
        "line_count": 2,
        "mean_score": mean_score,
    }


def _sweep(shift, score, baseline_score):
    return {
        "shift": shift,
        "score": score,
        "baseline_score": baseline_score,
        "gain": round(score - baseline_score, 3),
        "scores": {0.0: baseline_score, shift: score},
    }


@pytest.fixture
def task_env():
    """Patch the task's collaborators; the song starts with a 2s-late LRC that aligns poorly."""
    song = SimpleNamespace(
        id=SONG_ID,
        title="Test Song",
        artist="Test Artist",
        album=None,
        plain_lyrics=None,
        synced_lyrics=LATE_LRC,
        word_synced_lyrics=None,
    )
    mock_session = MagicMock()
    mock_repo = MagicMock()
    mock_repo.fetch.side_effect = [song, song]

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("app.config.get_config", return_value=SimpleNamespace(BASE_LIBRARY_DIR="/karaoke-library")),
        patch("app.db.database.get_db_session", return_value=_make_db_context(mock_session)),
        patch("app.repositories.song_repository.SongRepository", return_value=mock_repo),
        patch("app.jobs.lyrics_tasks.job_repository") as mock_job_repository,
        patch(
            "app.jobs.lyrics_tasks._build_alignment_attempts",
            return_value=[{"content": LATE_LRC, "source_type": "synced", "source": "db:synced", "persist": False}],
        ),
        patch("app.jobs.lyrics_tasks.run_alignment_attempt", return_value=_alignment(0.12)),
        patch("app.jobs.lyrics_tasks.log_lyrics_event"),
        patch("app.jobs.lyrics_tasks._update_lyrics_alignment_job"),
        patch("app.jobs.lyrics_tasks._complete_lyrics_alignment_job") as mock_complete_job,
        patch("app.services.lyrics_offset.sweep_lrc_offset") as mock_sweep,
        patch("app.services.lyrics_alignment.align_lyrics_to_vocals") as mock_realign,
        patch("app.services.lyrics_transcription.transcribe_lyrics_from_vocals", return_value=None) as mock_transcribe,
    ):
        mock_job_repository.get_by_id.return_value = None
        yield SimpleNamespace(
            song=song,
            session=mock_session,
            sweep=mock_sweep,
            realign=mock_realign,
            transcribe=mock_transcribe,
            complete_job=mock_complete_job,
        )


def test_late_lyrics_are_shifted_onto_the_vocals_and_keep_their_word_timings(task_env):
    task_env.sweep.return_value = _sweep(shift=-2.0, score=0.71, baseline_score=0.12)
    task_env.realign.return_value = _alignment(0.71)

    result = align_song_lyrics(SONG_ID)

    assert result["status"] == "offset_corrected"
    assert result["offset"] == -2.0
    assert result["source"] == "db:synced"

    # The shift is applied as-is: 2s-late lyrics move 2s earlier.
    assert "[00:10.00]hello world" in task_env.song.synced_lyrics
    assert "[00:14.00]second line here" in task_env.song.synced_lyrics

    # Word timings come from aligning the exact stored text, not wiped.
    realigned_lrc = task_env.realign.call_args.args[0]
    assert realigned_lrc == task_env.song.synced_lyrics
    stored = json.loads(task_env.song.word_synced_lyrics)
    assert stored["offset_applied"] == -2.0
    assert stored["mean_score"] == 0.71
    assert stored["lyrics_source"] == "db:synced"
    assert len(stored["words"]) == 5

    task_env.transcribe.assert_not_called()
    task_env.session.commit.assert_called_once()
    task_env.complete_job.assert_called_once()


def test_small_sweep_gain_leaves_the_lyrics_alone_and_falls_back_to_asr(task_env):
    task_env.sweep.return_value = _sweep(shift=-0.5, score=0.13, baseline_score=0.12)

    result = align_song_lyrics(SONG_ID)

    assert result["status"] == "low_confidence"
    assert task_env.song.synced_lyrics == LATE_LRC
    assert task_env.song.word_synced_lyrics is None
    task_env.realign.assert_not_called()
    task_env.transcribe.assert_called_once()


def test_shift_is_not_stored_when_realigning_the_shifted_lyrics_scores_low(task_env):
    task_env.sweep.return_value = _sweep(shift=-2.0, score=0.71, baseline_score=0.12)
    task_env.realign.return_value = _alignment(0.2)

    result = align_song_lyrics(SONG_ID)

    assert result["status"] == "low_confidence"
    assert task_env.song.synced_lyrics == LATE_LRC
    task_env.transcribe.assert_called_once()


@pytest.mark.parametrize(
    ("sweep", "reason"),
    [
        (_sweep(shift=0.0, score=0.25, baseline_score=0.25), "no_shift"),
        (_sweep(shift=-0.5, score=0.27, baseline_score=0.25), "gain_too_small"),
        (_sweep(shift=3.0, score=0.28, baseline_score=0.10), "score_too_low"),
        (_sweep(shift=3.0, score=0.45, baseline_score=0.10), None),
    ],
)
def test_offset_rejection_reason(sweep, reason):
    assert _offset_rejection_reason(sweep) == reason
