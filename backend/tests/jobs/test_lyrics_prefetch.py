"""Tests for early lyrics prefetch task behavior."""

from unittest.mock import patch

import pytest

from app.jobs.lyrics_tasks import prefetch_song_lyrics

SONG_ID = "song-lyrics-123"


def _remote(content, source_type="synced"):
    return {
        "content": content,
        "source_type": source_type,
        "source": "lrclib:1",
        "persist": True,
    }


@pytest.fixture
def remote_attempts():
    """Stand in for the remote lyrics lookup; picking and saving run for real."""
    with patch("app.jobs.lyrics_tasks._build_alignment_attempts") as build:
        yield build


def _add(add_song, **fields):
    return add_song(
        SONG_ID, title="First Fires", artist="Bonobo feat. Grey Reverend", **fields
    )


def test_prefetch_persists_synced_lyrics_when_missing(
    add_song, fetch_song, remote_attempts
):
    _add(add_song)
    remote_attempts.return_value = [_remote("[00:00.00]test synced")]

    result = prefetch_song_lyrics(SONG_ID)

    assert result["status"] == "persisted"
    assert result["persisted_synced_lyrics"] is True
    assert fetch_song(SONG_ID).synced_lyrics == "[00:00.00]test synced"


@patch("app.jobs.lyrics_tasks.analyze_lyrics")
def test_prefetch_formats_synced_lyrics_before_persisting(
    mock_analyze_lyrics, add_song, fetch_song, remote_attempts
):
    _add(add_song)
    original_lrc = "[00:00.00]first line\n[00:10.00]second line"
    formatted_lrc = "[00:00.00]first line\n[00:05.00]\n[00:10.00]second line"
    candidate = _remote(original_lrc)
    remote_attempts.return_value = [candidate]
    mock_analyze_lyrics.return_value = {
        "candidates": [{"after_line_index": 0}],
        "modified_lrc": formatted_lrc,
    }

    result = prefetch_song_lyrics(SONG_ID)

    assert result["status"] == "persisted"
    assert result["persisted_synced_lyrics"] is True
    assert fetch_song(SONG_ID).synced_lyrics == formatted_lrc
    # Alignment runs on the same text that was saved.
    assert candidate["content"] == formatted_lrc
    mock_analyze_lyrics.assert_called_once_with(original_lrc, min_confidence=0.3)


def test_prefetch_does_not_overwrite_existing_synced_lyrics(
    add_song, fetch_song, remote_attempts
):
    _add(add_song, synced_lyrics="[00:00.00]existing synced")
    remote_attempts.return_value = [_remote("[00:00.00]new synced")]

    result = prefetch_song_lyrics(SONG_ID)

    assert result["status"] == "no_change"
    assert result["persisted_synced_lyrics"] is False
    assert fetch_song(SONG_ID).synced_lyrics == "[00:00.00]existing synced"


def test_prefetch_reports_no_candidate_when_none_available(
    add_song, fetch_song, remote_attempts
):
    _add(add_song)
    remote_attempts.return_value = []

    result = prefetch_song_lyrics(SONG_ID)

    assert result == {"status": "no_candidate", "song_id": SONG_ID, "attempt_count": 0}
    saved = fetch_song(SONG_ID)
    assert saved.synced_lyrics is None
    assert saved.plain_lyrics is None
