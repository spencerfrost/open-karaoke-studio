"""Tests for ASR fallback behavior in lyrics alignment."""

from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from app.jobs.lyrics_tasks import align_song_lyrics


SONG_ID = "song-lyrics-asr-123"


def _make_db_context(mock_session=None):
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=mock_session or MagicMock())
    ctx.__exit__ = Mock(return_value=False)
    return ctx


@patch("app.jobs.lyrics_tasks._complete_lyrics_alignment_job")
@patch("app.jobs.lyrics_tasks._update_lyrics_alignment_job")
@patch("app.jobs.lyrics_tasks.log_lyrics_event")
@patch("app.jobs.lyrics_tasks._build_alignment_attempts", return_value=[])
@patch("app.services.lyrics_transcription.transcribe_lyrics_from_vocals")
@patch("app.jobs.lyrics_tasks.job_repository")
@patch("app.repositories.song_repository.SongRepository")
@patch("app.db.database.get_db_session")
@patch("app.config.get_config")
@patch("pathlib.Path.exists", return_value=True)
def test_align_song_lyrics_uses_asr_fallback_when_no_candidates(
    _mock_exists,
    mock_get_config,
    mock_get_db,
    mock_repo_cls,
    mock_job_repository,
    mock_transcribe,
    _mock_build_attempts,
    _mock_log,
    mock_update_job,
    mock_complete_job,
):
    mock_get_config.return_value = SimpleNamespace(BASE_LIBRARY_DIR="/karaoke-library")
    mock_job_repository.get_by_id.return_value = None

    song = SimpleNamespace(
        id=SONG_ID,
        title="Test Song",
        artist="Test Artist",
        album=None,
        plain_lyrics=None,
        synced_lyrics=None,
        word_synced_lyrics=None,
    )
    mock_session = MagicMock()
    mock_get_db.return_value = _make_db_context(mock_session)
    mock_repo = MagicMock()
    mock_repo.fetch.side_effect = [song, song]
    mock_repo_cls.return_value = mock_repo

    mock_transcribe.return_value = {
        "plain_lyrics": "hello world",
        "synced_lyrics": "[00:00.00]hello world",
        "alignment": {
            "words": [
                {"word": "hello", "start": 0.0, "end": 0.4, "score": 0.9, "line_index": 0},
                {"word": "world", "start": 0.4, "end": 0.9, "score": 0.9, "line_index": 0},
            ],
            "instrumental_intervals": [],
            "language": "en",
            "aligned_at": "2026-06-02T00:00:00+00:00",
            "word_count": 2,
            "line_count": 1,
            "mean_score": 0.9,
        },
    }

    result = align_song_lyrics(SONG_ID)

    assert result["status"] == "ok"
    assert result["song_id"] == SONG_ID
    assert result["source"] == "asr:whisperx"
    assert result["fallback_reason"] == "no_candidates"
    assert result["asr_provider"] == "whisperx"
    assert result["asr_model"] == "unknown"
    assert song.plain_lyrics == "hello world"
    assert song.synced_lyrics == "[00:00.00]hello world"
    assert song.word_synced_lyrics is not None
    mock_transcribe.assert_called_once()
    mock_update_job.assert_called()
    mock_complete_job.assert_called_once()
    mock_session.commit.assert_called_once()


@patch("app.jobs.lyrics_tasks._complete_lyrics_alignment_job")
@patch("app.jobs.lyrics_tasks._update_lyrics_alignment_job")
@patch("app.jobs.lyrics_tasks.log_lyrics_event")
@patch("app.jobs.lyrics_tasks.run_alignment_attempt")
@patch("app.jobs.lyrics_tasks._build_alignment_attempts")
@patch("app.services.lyrics_transcription.transcribe_lyrics_from_vocals")
@patch("app.jobs.lyrics_tasks.job_repository")
@patch("app.repositories.song_repository.SongRepository")
@patch("app.db.database.get_db_session")
@patch("app.config.get_config")
@patch("pathlib.Path.exists", return_value=True)
def test_align_song_lyrics_uses_asr_fallback_when_alignment_is_low_confidence(
    _mock_exists,
    mock_get_config,
    mock_get_db,
    mock_repo_cls,
    mock_job_repository,
    mock_transcribe,
    mock_build_attempts,
    mock_run_alignment,
    _mock_log,
    mock_update_job,
    mock_complete_job,
):
    mock_get_config.return_value = SimpleNamespace(BASE_LIBRARY_DIR="/karaoke-library")
    mock_job_repository.get_by_id.return_value = None

    song = SimpleNamespace(
        id=SONG_ID,
        title="Test Song",
        artist="Test Artist",
        album=None,
        plain_lyrics="old plain lyrics",
        synced_lyrics="[00:00.00]old synced lyrics",
        word_synced_lyrics=None,
    )
    mock_session = MagicMock()
    mock_get_db.return_value = _make_db_context(mock_session)
    mock_repo = MagicMock()
    mock_repo.fetch.side_effect = [song, song]
    mock_repo_cls.return_value = mock_repo

    mock_build_attempts.return_value = [
        {
            "content": "old plain lyrics",
            "source_type": "plain",
            "source": "db:plain",
            "persist": False,
        }
    ]
    mock_run_alignment.return_value = {
        "words": [
            {"word": "old", "start": 0.0, "end": 0.3, "score": 0.2, "line_index": 0},
            {"word": "plain", "start": 0.3, "end": 0.6, "score": 0.2, "line_index": 0},
        ],
        "instrumental_intervals": [],
        "language": "en",
        "aligned_at": "2026-06-02T00:00:00+00:00",
        "word_count": 2,
        "line_count": 1,
        "mean_score": 0.2,
    }
    mock_transcribe.return_value = {
        "plain_lyrics": "new asr plain lyrics",
        "synced_lyrics": "[00:00.00]new asr plain lyrics",
        "alignment": {
            "words": [
                {"word": "new", "start": 0.0, "end": 0.3, "score": 0.8, "line_index": 0},
                {"word": "asr", "start": 0.3, "end": 0.6, "score": 0.8, "line_index": 0},
            ],
            "instrumental_intervals": [],
            "language": "en",
            "aligned_at": "2026-06-02T00:00:00+00:00",
            "word_count": 2,
            "line_count": 1,
            "mean_score": 0.8,
        },
    }

    result = align_song_lyrics(SONG_ID)

    assert result["status"] == "ok"
    assert result["song_id"] == SONG_ID
    assert result["source"] == "asr:whisperx"
    assert result["fallback_reason"] == "low_confidence"
    assert result["asr_provider"] == "whisperx"
    assert result["asr_model"] == "unknown"
    assert song.plain_lyrics == "new asr plain lyrics"
    assert song.synced_lyrics == "[00:00.00]new asr plain lyrics"
    assert song.word_synced_lyrics is not None
    mock_run_alignment.assert_called_once()
    mock_transcribe.assert_called_once()
    mock_update_job.assert_called()
    mock_complete_job.assert_called_once()
    mock_session.commit.assert_called_once()