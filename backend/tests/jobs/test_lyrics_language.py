"""Tests that lyrics alignment runs in the song's language."""

from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.jobs.lyrics_tasks import align_song_lyrics

SONG_ID = "song-lyrics-language-123"
LRC = (
    "[00:10.00]Qui dit étude dit travail\n"
    "[00:13.00]Qui dit taf te dit les thunes\n"
    "[00:16.00]Qui dit argent dit dépenses\n"
    "[00:19.00]Qui dit crédit dit créance\n"
    "[00:22.00]Qui dit dette te dit huissier\n"
    "[00:25.00]Oui, dit assis dans la merde\n"
    "[00:28.00]Qui dit amour dit les gosses\n"
    "[00:31.00]Dit toujours et dit divorce\n"
    "[00:34.00]Qui dit proches te dit deuils\n"
    "[00:37.00]Car les problèmes ne viennent pas seuls"
)
ENGLISH_LRC = (
    "[00:43.00]It's bugging me, grating me\n"
    "[00:46.00]And twisting me around\n"
    "[00:50.00]Yeah, I'm endlessly caving in\n"
    "[00:54.00]And turning inside out\n"
    "[01:00.00]'Cause I want it now, I want it now\n"
    "[01:07.00]Give me your heart and your soul\n"
    "[01:11.00]And I'm breaking out, I'm breaking out\n"
    "[01:17.00]Last chance to lose control\n"
    "[01:48.00]And dreaming I'm alive"
)


def _make_db_context(mock_session):
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=mock_session)
    ctx.__exit__ = Mock(return_value=False)
    return ctx


def _alignment(mean_score):
    words = [
        (word, line)
        for line, text in enumerate(LRC.splitlines())
        for word in text.split("]", 1)[1].split()
    ]
    return {
        "words": [
            {
                "word": w,
                "start": float(i),
                "end": i + 0.5,
                "score": mean_score,
                "line_index": line,
            }
            for i, (w, line) in enumerate(words)
        ],
        "instrumental_intervals": [],
        "language": "fr",
        "aligned_at": "2026-09-30T00:00:00+00:00",
        "word_count": len(words),
        "line_count": 4,
        "mean_score": mean_score,
    }


def _attempt(content):
    return {
        "content": content,
        "source_type": "synced",
        "source": "db:synced",
        "persist": False,
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
        singing_map=None,
    )
    mock_repo = MagicMock()
    mock_repo.fetch.return_value = song
    mock_repo.update.side_effect = lambda _song_id, **fields: [
        setattr(song, k, v) for k, v in fields.items()
    ]

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch(
            "app.config.get_config",
            return_value=SimpleNamespace(BASE_LIBRARY_DIR="/karaoke-library"),
        ),
        patch(
            "app.db.database.get_db_session", return_value=_make_db_context(MagicMock())
        ),
        patch(
            "app.repositories.song_repository.SongRepository", return_value=mock_repo
        ),
        patch("app.jobs.lyrics_tasks.job_repository") as mock_job_repository,
        patch(
            "app.jobs.lyrics_tasks._build_alignment_attempts",
            return_value=[_attempt(LRC)],
        ) as mock_build_attempts,
        patch(
            "app.jobs.lyrics_tasks.run_alignment_attempt", return_value=_alignment(0.8)
        ) as mock_run_alignment,
        patch("app.jobs.lyrics_tasks._apply_offset_correction", return_value=None),
        patch("app.jobs.lyrics_tasks.log_lyrics_event"),
        patch("app.jobs.lyrics_tasks._update_lyrics_alignment_job"),
        patch("app.jobs.lyrics_tasks._complete_lyrics_alignment_job"),
        patch("app.services.lyrics_language.detect_vocals_language") as mock_detect,
        patch(
            "app.services.lyrics_transcription.transcribe_lyrics_from_vocals",
            return_value=None,
        ) as mock_transcribe,
    ):
        mock_job_repository.get_by_id.return_value = None
        yield SimpleNamespace(
            song=song,
            run_alignment=mock_run_alignment,
            detect=mock_detect,
            build_attempts=mock_build_attempts,
            transcribe=mock_transcribe,
        )


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


def test_the_lyrics_text_decides_and_is_stored_without_listening(task_env):
    align_song_lyrics(SONG_ID)

    assert _aligned_language(task_env) == "fr"
    assert task_env.song.language == "fr"
    task_env.detect.assert_not_called()


def test_english_lyrics_are_aligned_in_english_whatever_the_singing_sounds_like(
    task_env,
):
    # Whisper heard Muse's Hysteria as Danish (0.52) and aligned it as Danish.
    task_env.build_attempts.return_value = [_attempt(ENGLISH_LRC)]
    task_env.detect.return_value = {"language": "da", "probability": 0.52}

    align_song_lyrics(SONG_ID)

    assert _aligned_language(task_env) == "en"
    assert task_env.song.language == "en"
    task_env.detect.assert_not_called()


def test_too_little_text_falls_back_to_english_without_storing(task_env):
    task_env.build_attempts.return_value = [_attempt("[00:10.00]Oh oh oh")]

    align_song_lyrics(SONG_ID)

    assert _aligned_language(task_env) == "en"
    assert task_env.song.language is None
    task_env.detect.assert_not_called()


def test_without_lyrics_a_guess_from_the_singing_is_used_but_never_stored(task_env):
    task_env.build_attempts.return_value = []
    task_env.detect.return_value = {"language": "fr", "probability": 0.94}

    align_song_lyrics(SONG_ID)

    assert task_env.transcribe.call_args.kwargs["language"] == "fr"
    assert task_env.song.language is None


@pytest.mark.parametrize("detected", [None, {"language": "fr", "probability": 0.31}])
def test_without_lyrics_an_unsure_guess_transcribes_in_english(task_env, detected):
    task_env.build_attempts.return_value = []
    task_env.detect.return_value = detected

    align_song_lyrics(SONG_ID)

    assert task_env.transcribe.call_args.kwargs["language"] == "en"
    assert task_env.song.language is None


def test_a_language_without_word_alignment_keeps_line_timed_lyrics(task_env):
    task_env.song.language = "ja"

    result = align_song_lyrics(SONG_ID)

    assert result == {
        "status": "no_alignment_model",
        "song_id": SONG_ID,
        "language": "ja",
    }
    task_env.run_alignment.assert_not_called()
    assert task_env.song.synced_lyrics == LRC
