"""Tests for early lyrics prefetch task behavior."""

from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from app.jobs.lyrics_tasks import prefetch_song_lyrics


SONG_ID = "song-lyrics-123"


def _make_db_context(mock_session=None):
    """Return a mock for get_db_session used as a context manager."""
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=mock_session or MagicMock())
    ctx.__exit__ = Mock(return_value=False)
    return ctx


@patch("app.jobs.lyrics_tasks.log_lyrics_event")
@patch("app.jobs.lyrics_tasks.select_initial_lyrics")
@patch("app.jobs.lyrics_tasks._build_alignment_attempts")
@patch("app.repositories.song_repository.SongRepository")
@patch("app.db.database.get_db_session")
def test_prefetch_persists_synced_lyrics_when_missing(
    mock_get_db,
    mock_repo_cls,
    mock_build_attempts,
    mock_select_initial,
    _mock_log,
):
    song = SimpleNamespace(
        id=SONG_ID,
        title="First Fires",
        artist="Bonobo feat. Grey Reverend",
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

    candidate = {
        "content": "[00:00.00]test synced",
        "source_type": "synced",
        "source": "lrclib:1",
        "persist": True,
    }
    mock_build_attempts.return_value = [candidate]
    mock_select_initial.return_value = candidate

    result = prefetch_song_lyrics(SONG_ID)

    assert result["status"] == "persisted"
    assert result["persisted_synced_lyrics"] is True
    assert song.synced_lyrics == "[00:00.00]test synced"
    mock_session.commit.assert_called_once()


@patch("app.jobs.lyrics_tasks.log_lyrics_event")
@patch("app.jobs.lyrics_tasks.select_initial_lyrics")
@patch("app.jobs.lyrics_tasks._build_alignment_attempts")
@patch("app.jobs.lyrics_tasks.analyze_lyrics")
@patch("app.repositories.song_repository.SongRepository")
@patch("app.db.database.get_db_session")
def test_prefetch_formats_synced_lyrics_before_persisting(
    mock_get_db,
    mock_repo_cls,
    mock_analyze_lyrics,
    mock_build_attempts,
    mock_select_initial,
    _mock_log,
):
    song = SimpleNamespace(
        id=SONG_ID,
        title="First Fires",
        artist="Bonobo feat. Grey Reverend",
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

    original_lrc = "[00:00.00]first line\n[00:10.00]second line"
    candidate = {
        "content": original_lrc,
        "source_type": "synced",
        "source": "lrclib:1",
        "persist": True,
    }
    formatted_lrc = "[00:00.00]first line\n[00:05.00]\n[00:10.00]second line"
    mock_build_attempts.return_value = [candidate]
    mock_select_initial.return_value = candidate
    mock_analyze_lyrics.return_value = {
        "candidates": [{"after_line_index": 0}],
        "modified_lrc": formatted_lrc,
    }

    result = prefetch_song_lyrics(SONG_ID)

    assert result["status"] == "persisted"
    assert result["persisted_synced_lyrics"] is True
    assert song.synced_lyrics == formatted_lrc
    assert candidate["content"] == formatted_lrc
    mock_analyze_lyrics.assert_called_once_with(original_lrc, min_confidence=0.3)
    mock_session.commit.assert_called_once()


@patch("app.jobs.lyrics_tasks.log_lyrics_event")
@patch("app.jobs.lyrics_tasks.select_initial_lyrics")
@patch("app.jobs.lyrics_tasks._build_alignment_attempts")
@patch("app.repositories.song_repository.SongRepository")
@patch("app.db.database.get_db_session")
def test_prefetch_does_not_overwrite_existing_synced_lyrics(
    mock_get_db,
    mock_repo_cls,
    mock_build_attempts,
    mock_select_initial,
    _mock_log,
):
    song = SimpleNamespace(
        id=SONG_ID,
        title="First Fires",
        artist="Bonobo feat. Grey Reverend",
        album=None,
        plain_lyrics=None,
        synced_lyrics="[00:00.00]existing synced",
        word_synced_lyrics=None,
    )

    mock_session = MagicMock()
    mock_get_db.return_value = _make_db_context(mock_session)
    mock_repo = MagicMock()
    mock_repo.fetch.side_effect = [song, song]
    mock_repo_cls.return_value = mock_repo

    candidate = {
        "content": "[00:00.00]new synced",
        "source_type": "synced",
        "source": "lrclib:1",
        "persist": True,
    }
    mock_build_attempts.return_value = [candidate]
    mock_select_initial.return_value = candidate

    result = prefetch_song_lyrics(SONG_ID)

    assert result["status"] == "no_change"
    assert result["persisted_synced_lyrics"] is False
    assert song.synced_lyrics == "[00:00.00]existing synced"
    mock_session.commit.assert_not_called()


@patch("app.jobs.lyrics_tasks.log_lyrics_event")
@patch("app.jobs.lyrics_tasks.select_initial_lyrics", return_value=None)
@patch("app.jobs.lyrics_tasks._build_alignment_attempts", return_value=[])
@patch("app.repositories.song_repository.SongRepository")
@patch("app.db.database.get_db_session")
def test_prefetch_reports_no_candidate_when_none_available(
    mock_get_db,
    mock_repo_cls,
    _mock_build_attempts,
    _mock_select_initial,
    _mock_log,
):
    song = SimpleNamespace(
        id=SONG_ID,
        title="First Fires",
        artist="Bonobo feat. Grey Reverend",
        album=None,
        plain_lyrics=None,
        synced_lyrics=None,
        word_synced_lyrics=None,
    )

    mock_session = MagicMock()
    mock_get_db.return_value = _make_db_context(mock_session)
    mock_repo = MagicMock()
    mock_repo.fetch.return_value = song
    mock_repo_cls.return_value = mock_repo

    result = prefetch_song_lyrics(SONG_ID)

    assert result == {"status": "no_candidate", "song_id": SONG_ID, "attempt_count": 0}
    mock_session.commit.assert_not_called()
