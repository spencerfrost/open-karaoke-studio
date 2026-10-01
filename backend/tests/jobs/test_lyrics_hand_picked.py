"""Tests for hand-picked lyrics, rejected lyrics, and lyrics changing during a run."""

import json
from collections.abc import Collection
from contextlib import ExitStack
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from app.jobs.lyrics_tasks import align_song_lyrics

SONG_ID = "song-hand-picked-123"


def _make_db_context(mock_session):
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=mock_session)
    ctx.__exit__ = Mock(return_value=False)
    return ctx


def _song(**overrides):
    fields = {
        "id": SONG_ID,
        "title": "Blackbird",
        "artist": "The Beatles",
        "album": None,
        "plain_lyrics": None,
        "synced_lyrics": "[00:01.00]hello world",
        "word_synced_lyrics": None,
        "lyrics_hand_picked_at": None,
        "language": "en",
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _alignment(*words: str, score: float = 0.8) -> dict:
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


def _run(
    song,
    *,
    attempts,
    rejected_keys: Collection[str] = (),
    extra_patches=(),
    **task_kwargs
):
    """Run align_song_lyrics with the database, Celery and WhisperX mocked out."""
    mock_repo = MagicMock()
    mock_repo.fetch.return_value = song
    mocks = {}
    with ExitStack() as stack:
        for target, kwargs in [
            ("pathlib.Path.exists", {"return_value": True}),
            (
                "app.config.get_config",
                {"return_value": SimpleNamespace(BASE_LIBRARY_DIR="/karaoke-library")},
            ),
            (
                "app.db.database.get_db_session",
                {"return_value": _make_db_context(MagicMock())},
            ),
            (
                "app.repositories.song_repository.SongRepository",
                {"return_value": mock_repo},
            ),
            (
                "app.repositories.lyrics_report_repository.LyricsReportRepository.rejected_keys",
                {"return_value": set(rejected_keys)},
            ),
            ("app.jobs.lyrics_tasks.job_repository", {}),
            (
                "app.jobs.lyrics_tasks._build_alignment_attempts",
                {"return_value": attempts},
            ),
            (
                "app.jobs.lyrics_tasks.run_alignment_attempt",
                {"return_value": _alignment("hello", "world")},
            ),
            ("app.jobs.lyrics_tasks._queue_fresh_run", {}),
            ("app.jobs.lyrics_tasks.log_lyrics_event", {}),
            ("app.jobs.lyrics_tasks._update_lyrics_alignment_job", {}),
            ("app.jobs.lyrics_tasks._complete_lyrics_alignment_job", {}),
            *extra_patches,
        ]:
            mocks[target.rsplit(".", 1)[-1]] = stack.enter_context(
                patch(target, **kwargs)
            )
        mocks["job_repository"].get_by_id.return_value = None
        result = align_song_lyrics(SONG_ID, **task_kwargs)
    return result, mocks


SYNCED_ATTEMPT = {
    "content": "[00:01.00]hello world",
    "source_type": "synced",
    "source": "db:synced",
    "persist": False,
}


def test_hand_picked_lyrics_are_only_timed_never_replaced_by_fetched_ones():
    song = _song(lyrics_hand_picked_at=datetime(2026, 9, 30, tzinfo=timezone.utc))

    result, mocks = _run(song, attempts=[SYNCED_ATTEMPT])

    assert result["status"] == "ok"
    assert (
        mocks["_build_alignment_attempts"].call_args.kwargs["include_remote"] is False
    )


def test_rejected_lyrics_are_passed_to_candidate_building():
    result, mocks = _run(
        _song(), attempts=[SYNCED_ATTEMPT], rejected_keys={"rejected-key"}
    )

    assert result["status"] == "ok"
    assert mocks["_build_alignment_attempts"].call_args.kwargs["rejected_keys"] == {
        "rejected-key"
    }
    assert mocks["_build_alignment_attempts"].call_args.kwargs["include_remote"] is True


def test_a_transcript_replaces_plain_lyrics_that_were_reported_wrong():
    from app.services.lyrics_retiming import lyrics_words_key

    song = _song(plain_lyrics="wrong words", synced_lyrics=None)
    transcription = {
        "plain_lyrics": "hello world",
        "synced_lyrics": "[00:01.00]hello world",
        "alignment": _alignment("hello", "world"),
        "asr_provider": "whisperx",
        "asr_model": "small",
    }

    result, _ = _run(
        song,
        attempts=[],
        rejected_keys={lyrics_words_key("wrong words", "plain")},
        extra_patches=[
            (
                "app.services.lyrics_transcription.transcribe_lyrics_from_vocals",
                {"return_value": transcription},
            )
        ],
    )

    assert result["fallback_reason"] == "no_candidates"
    assert song.plain_lyrics == "hello world"
    assert song.synced_lyrics == "[00:01.00]hello world"


def test_a_run_stops_before_writing_when_the_lyrics_changed_and_starts_again():
    song = _song()

    # The run starts with one state; by the time it writes, someone has
    # saved or reported the lyrics.
    result, mocks = _run(
        song,
        attempts=[SYNCED_ATTEMPT],
        extra_patches=[
            (
                "app.jobs.lyrics_tasks._lyrics_run_token",
                {"side_effect": [("before",), ("after",)]},
            )
        ],
    )

    assert result == {"status": "superseded", "song_id": SONG_ID}
    assert song.word_synced_lyrics is None
    mocks["_queue_fresh_run"].assert_called_once()


def test_a_run_that_finished_before_the_change_starts_again():
    song = _song()

    result, mocks = _run(
        song,
        attempts=[SYNCED_ATTEMPT],
        extra_patches=[
            ("app.jobs.lyrics_tasks._lyrics_changed_since", {"return_value": True})
        ],
    )

    assert result["status"] == "ok"
    assert json.loads(song.word_synced_lyrics)["lyrics_source"] == "db:synced"
    mocks["_queue_fresh_run"].assert_called_once()


def test_a_run_with_nothing_changed_doesnt_start_again():
    result, mocks = _run(_song(), attempts=[SYNCED_ATTEMPT])

    assert result["status"] == "ok"
    mocks["_queue_fresh_run"].assert_not_called()


# ---------------------------------------------------------------------------
# Acting on reports
# ---------------------------------------------------------------------------


def _state(song, *, pending_reports):
    return {
        "song": {
            "id": song.id,
            "title": song.title,
            "artist": song.artist,
            "album": song.album,
            "plain_lyrics": song.plain_lyrics,
            "synced_lyrics": song.synced_lyrics,
            "word_synced_lyrics": song.word_synced_lyrics,
        },
        "language": "en",
        "hand_picked_at": None,
        "rejected_keys": set(),
        "run_token": ("token",),
        "pending_reports": pending_reports,
    }


def test_out_of_sync_alone_re_times_the_same_words_without_trying_others():
    song = _song()

    result, mocks = _run(
        song,
        attempts=[SYNCED_ATTEMPT],
        extra_patches=[
            (
                "app.jobs.lyrics_tasks._load_song_lyrics_state",
                {"return_value": _state(song, pending_reports=[(1, "timing", 1)])},
            ),
            ("app.jobs.lyrics_tasks._retime_from_asr", {"return_value": None}),
            ("app.jobs.lyrics_tasks._record_report_outcomes", {}),
        ],
    )

    assert result == {"status": "retime_failed", "song_id": SONG_ID}
    mocks["run_alignment_attempt"].assert_not_called()
    assert mocks["_retime_from_asr"].call_args.kwargs["reason"] == "timing_reported"
    assert (
        mocks["_build_alignment_attempts"].call_args.kwargs["include_remote"] is False
    )
    mocks["_record_report_outcomes"].assert_called_once_with(
        SONG_ID, result, [(1, "timing", 1)]
    )


def test_wrong_words_with_out_of_sync_runs_the_full_search():
    song = _song()

    result, mocks = _run(
        song,
        attempts=[SYNCED_ATTEMPT],
        extra_patches=[
            (
                "app.jobs.lyrics_tasks._load_song_lyrics_state",
                {
                    "return_value": _state(
                        song, pending_reports=[(1, "timing", 1), (2, "words", 1)]
                    )
                },
            ),
            ("app.jobs.lyrics_tasks._lyrics_run_token", {"return_value": ("token",)}),
            ("app.jobs.lyrics_tasks._record_report_outcomes", {}),
        ],
    )

    assert result["status"] == "ok"
    mocks["run_alignment_attempt"].assert_called_once()
    assert mocks["_build_alignment_attempts"].call_args.kwargs["include_remote"] is True
