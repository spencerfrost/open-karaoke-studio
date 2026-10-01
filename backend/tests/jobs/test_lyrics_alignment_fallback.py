"""Tests for ASR fallback behavior in lyrics alignment."""

import json
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
        lyrics_hand_picked_at=None,
        language="en",
    )
    mock_session = MagicMock()
    mock_get_db.return_value = _make_db_context(mock_session)
    mock_repo = MagicMock()
    mock_repo.fetch.return_value = song
    mock_repo_cls.return_value = mock_repo

    mock_transcribe.return_value = {
        "plain_lyrics": "hello world",
        "synced_lyrics": "[00:00.00]hello world",
        "alignment": {
            "words": [
                {
                    "word": "hello",
                    "start": 0.0,
                    "end": 0.4,
                    "score": 0.9,
                    "line_index": 0,
                },
                {
                    "word": "world",
                    "start": 0.4,
                    "end": 0.9,
                    "score": 0.9,
                    "line_index": 0,
                },
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
def test_low_confidence_lyrics_are_never_replaced_by_a_transcript(
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
        lyrics_hand_picked_at=None,
        language="en",
    )
    mock_session = MagicMock()
    mock_get_db.return_value = _make_db_context(mock_session)
    mock_repo = MagicMock()
    mock_repo.fetch.return_value = song
    mock_repo_cls.return_value = mock_repo

    mock_build_attempts.return_value = [
        {
            "content": "[00:00.00]old synced lyrics",
            "source_type": "synced",
            "source": "db:synced",
            "persist": False,
        }
    ]
    mock_run_alignment.return_value = {
        "words": [
            {"word": "old", "start": 0.0, "end": 0.3, "score": 0.2, "line_index": 0},
            {"word": "synced", "start": 0.3, "end": 0.6, "score": 0.2, "line_index": 0},
            {"word": "lyrics", "start": 0.6, "end": 0.9, "score": 0.2, "line_index": 0},
        ],
        "instrumental_intervals": [],
        "language": "en",
        "aligned_at": "2026-06-02T00:00:00+00:00",
        "word_count": 3,
        "line_count": 1,
        "mean_score": 0.2,
    }
    mock_transcribe.return_value = {
        "plain_lyrics": "new asr",
        "synced_lyrics": "[00:00.00]new asr",
        "alignment": {
            "words": [
                {
                    "word": "new",
                    "start": 0.0,
                    "end": 0.3,
                    "score": 0.8,
                    "line_index": 0,
                },
                {
                    "word": "asr",
                    "start": 0.3,
                    "end": 0.6,
                    "score": 0.8,
                    "line_index": 0,
                },
            ],
            "instrumental_intervals": [],
            "language": "en",
            "aligned_at": "2026-06-02T00:00:00+00:00",
            "word_count": 2,
            "line_count": 1,
            "mean_score": 0.8,
        },
    }

    with patch("app.jobs.lyrics_tasks._apply_offset_correction", return_value=None):
        result = align_song_lyrics(SONG_ID)

    # ASR heard different words, so it can't time these lyrics, and its
    # transcript doesn't replace them: they stay, scrolling line by line.
    assert result["status"] == "low_confidence"
    assert song.plain_lyrics == "old plain lyrics"
    assert song.synced_lyrics == "[00:00.00]old synced lyrics"
    assert song.word_synced_lyrics is None
    mock_run_alignment.assert_called_once()
    mock_transcribe.assert_called_once()
    mock_update_job.assert_called()
    mock_complete_job.assert_called_once()
    mock_session.commit.assert_not_called()


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


def _run_plain_only(transcription, alignment=None, chunked=None):
    """Run align_song_lyrics for a song whose only candidate is plain lyrics."""
    song = SimpleNamespace(
        id=SONG_ID,
        title="Test Song",
        artist="Test Artist",
        album=None,
        plain_lyrics="Human plain lyrics",
        synced_lyrics=None,
        word_synced_lyrics=None,
        lyrics_hand_picked_at=None,
        language="en",
    )
    mock_repo = MagicMock()
    mock_repo.fetch.return_value = song
    plain_attempt = {
        "content": "Human plain lyrics",
        "source_type": "plain",
        "source": "db:plain",
        "persist": False,
    }

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
            "app.services.lyrics_transcription.transcribe_lyrics_from_vocals",
            return_value=transcription,
        ),
        patch(
            "app.services.lyrics_alignment.align_line_chunks", return_value=chunked
        ) as mock_align_chunks,
        patch(
            "app.services.lyrics_alignment.align_lyrics_to_vocals",
            return_value=alignment,
        ) as mock_align,
        patch(
            "app.jobs.lyrics_tasks._build_alignment_attempts",
            return_value=[plain_attempt],
        ),
        patch("app.jobs.lyrics_tasks.run_alignment_attempt") as mock_run_alignment,
        patch("app.jobs.lyrics_tasks.log_lyrics_event"),
        patch("app.jobs.lyrics_tasks._update_lyrics_alignment_job"),
        patch("app.jobs.lyrics_tasks._complete_lyrics_alignment_job"),
    ):
        mock_job_repository.get_by_id.return_value = None
        result = align_song_lyrics(SONG_ID)

    # Plain lyrics are never force-aligned as they are.
    mock_run_alignment.assert_not_called()
    return song, result, mock_align_chunks, mock_align


def test_plain_lyrics_are_timed_from_asr_and_keep_their_words():
    song, result, mock_align_chunks, mock_align = _run_plain_only(
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
    assert song.synced_lyrics == aligned_lrc
    assert song.plain_lyrics == "Human plain lyrics"
    stored = json.loads(song.word_synced_lyrics)
    assert [word["word"] for word in stored["words"]] == ["Human", "plain", "lyrics"]
    assert stored["lyrics_source_type"] == "synced"
    assert stored["retimed_from"] == "plain"
    assert stored["retimed_by"] == "asr:whisperx"


def test_plain_lyrics_stay_untimed_when_the_singing_is_different_words():
    song, result, mock_align_chunks, mock_align = _run_plain_only(
        _asr_transcription("something", "else", "entirely")
    )

    assert result == {"status": "plain_only", "song_id": SONG_ID}
    mock_align_chunks.assert_not_called()
    mock_align.assert_not_called()
    assert song.plain_lyrics == "Human plain lyrics"
    assert song.synced_lyrics is None
    assert song.word_synced_lyrics is None


def test_plain_lyrics_stay_untimed_when_the_retimed_alignment_scores_low():
    song, result, _, _ = _run_plain_only(
        _asr_transcription("human", "plain", "lyrics"),
        _alignment_of("Human", "plain", "lyrics", score=0.1),
        chunked=_alignment_of("Human", "plain", "lyrics", score=0.1),
    )

    assert result == {"status": "plain_only", "song_id": SONG_ID}
    assert song.synced_lyrics is None
    assert song.word_synced_lyrics is None


def test_plain_lyrics_stay_untimed_when_asr_is_unavailable():
    song, result, mock_align_chunks, mock_align = _run_plain_only(None)

    assert result == {"status": "plain_only", "song_id": SONG_ID}
    mock_align_chunks.assert_not_called()
    mock_align.assert_not_called()
    assert song.plain_lyrics == "Human plain lyrics"
    assert song.synced_lyrics is None
    assert song.word_synced_lyrics is None


def test_low_confidence_synced_lyrics_are_retimed_with_their_own_words():
    song = SimpleNamespace(
        id=SONG_ID,
        title="Test Song",
        artist="Test Artist",
        album=None,
        plain_lyrics="old plain lyrics",
        synced_lyrics="[00:30.00]old synced lyrics",
        word_synced_lyrics=None,
        lyrics_hand_picked_at=None,
        language="en",
    )
    mock_repo = MagicMock()
    mock_repo.fetch.return_value = song
    synced_attempt = {
        "content": "[00:30.00]old synced lyrics",
        "source_type": "synced",
        "source": "db:synced",
        "persist": False,
    }

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
            "app.services.lyrics_transcription.transcribe_lyrics_from_vocals",
            return_value=_asr_transcription("old", "synced", "lyrics"),
        ),
        patch(
            "app.services.lyrics_alignment.align_line_chunks",
            return_value=_alignment_of("old", "synced", "lyrics"),
        ),
        patch(
            "app.services.lyrics_alignment.align_lyrics_to_vocals",
            return_value=_alignment_of("old", "synced", "lyrics"),
        ),
        patch(
            "app.jobs.lyrics_tasks._build_alignment_attempts",
            return_value=[synced_attempt],
        ),
        patch(
            "app.jobs.lyrics_tasks.run_alignment_attempt",
            return_value=_alignment_of("old", "synced", "lyrics", score=0.1),
        ),
        patch("app.jobs.lyrics_tasks._apply_offset_correction", return_value=None),
        patch("app.jobs.lyrics_tasks.log_lyrics_event"),
        patch("app.jobs.lyrics_tasks._update_lyrics_alignment_job"),
        patch("app.jobs.lyrics_tasks._complete_lyrics_alignment_job"),
    ):
        mock_job_repository.get_by_id.return_value = None
        result = align_song_lyrics(SONG_ID)

    assert result["status"] == "retimed"
    assert result["reason"] == "low_confidence"
    # Same words, new time: the LRC's 0:30 was wrong, the singing starts at 0:01.
    assert song.synced_lyrics == "[00:00.75]old synced lyrics"
    assert song.plain_lyrics == "old plain lyrics"
    stored = json.loads(song.word_synced_lyrics)
    assert stored["retimed_from"] == "synced"
