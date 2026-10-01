"""Tests that lyrics alignment runs in the song's language."""

from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.jobs.lyrics_tasks import align_song_lyrics

SONG_ID = "song-lyrics-language-123"
LRC = "[00:10.00]bonjour tout le monde\n[00:13.00]encore une ligne"


def _make_db_context(mock_session):
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=mock_session)
    ctx.__exit__ = Mock(return_value=False)
    return ctx


def _alignment(mean_score):
    words = [("bonjour", 0), ("tout", 0), ("le", 0), ("monde", 0), ("encore", 1), ("une", 1), ("ligne", 1)]
    return {
        "words": [
            {"word": w, "start": float(i), "end": i + 0.5, "score": mean_score, "line_index": line}
            for i, (w, line) in enumerate(words)
        ],
        "instrumental_intervals": [],
        "language": "fr",
        "aligned_at": "2026-09-30T00:00:00+00:00",
        "word_count": len(words),
        "line_count": 2,
        "mean_score": mean_score,
    }


@pytest.fixture
def task_env():
    song = SimpleNamespace(
        id=SONG_ID,
        title="Alors on danse",
        artist="Stromae",
        album=None,
        plain_lyrics=None,
        synced_lyrics=LRC,
        word_synced_lyrics=None,
        lyrics_hand_picked_at=None,
        language=None,
    )
    mock_repo = MagicMock()
    mock_repo.fetch.return_value = song
    mock_repo.update.side_effect = lambda _song_id, **fields: [setattr(song, k, v) for k, v in fields.items()]

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("app.config.get_config", return_value=SimpleNamespace(BASE_LIBRARY_DIR="/karaoke-library")),
        patch("app.db.database.get_db_session", return_value=_make_db_context(MagicMock())),
        patch("app.repositories.song_repository.SongRepository", return_value=mock_repo),
        patch("app.jobs.lyrics_tasks.job_repository") as mock_job_repository,
        patch(
            "app.jobs.lyrics_tasks._build_alignment_attempts",
            return_value=[{"content": LRC, "source_type": "synced", "source": "db:synced", "persist": False}],
        ),
        patch("app.jobs.lyrics_tasks.run_alignment_attempt", return_value=_alignment(0.8)) as mock_run_alignment,
        patch("app.jobs.lyrics_tasks.log_lyrics_event"),
        patch("app.jobs.lyrics_tasks._update_lyrics_alignment_job"),
        patch("app.jobs.lyrics_tasks._complete_lyrics_alignment_job"),
        patch("app.services.lyrics_language.detect_vocals_language") as mock_detect,
        patch("app.services.lyrics_transcription.transcribe_lyrics_from_vocals", return_value=None),
    ):
        mock_job_repository.get_by_id.return_value = None
        yield SimpleNamespace(song=song, run_alignment=mock_run_alignment, detect=mock_detect)


def _aligned_language(task_env) -> str:
    return task_env.run_alignment.call_args.kwargs["language"]


def test_the_songs_stored_language_is_used_without_detecting(task_env):
    task_env.song.language = "fr"

    align_song_lyrics(SONG_ID)

    assert _aligned_language(task_env) == "fr"
    task_env.detect.assert_not_called()


def test_a_requested_language_overrides_the_songs_for_that_run(task_env):
    task_env.song.language = "fr"

    align_song_lyrics(SONG_ID, language="de")

    assert _aligned_language(task_env) == "de"
    assert task_env.song.language == "fr"


def test_a_confident_detection_is_used_and_stored_on_the_song(task_env):
    task_env.detect.return_value = {"language": "fr", "probability": 0.94}

    align_song_lyrics(SONG_ID)

    assert _aligned_language(task_env) == "fr"
    assert task_env.song.language == "fr"


@pytest.mark.parametrize("detected", [None, {"language": "fr", "probability": 0.31}])
def test_an_unsure_or_failed_detection_falls_back_to_english_without_storing(task_env, detected):
    task_env.detect.return_value = detected

    align_song_lyrics(SONG_ID)

    assert _aligned_language(task_env) == "en"
    assert task_env.song.language is None


def test_a_language_without_word_alignment_keeps_line_timed_lyrics(task_env):
    task_env.song.language = "ja"

    result = align_song_lyrics(SONG_ID)

    assert result == {"status": "no_alignment_model", "song_id": SONG_ID, "language": "ja"}
    task_env.run_alignment.assert_not_called()
    assert task_env.song.synced_lyrics == LRC
