"""Tests for the library-wide lyrics alignment run: one align_song_lyrics job per song."""

from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from app.db.models import LyricsReport
from app.jobs.batch_tasks import batch_align_lyrics


@contextmanager
def _run_with(*, vocals, dispatched):
    """Only `vocals` songs have a vocals stem; `dispatched` says which jobs get queued."""
    with (
        patch("app.services.lyrics_repair.FileService") as mock_files,
        patch(
            "app.jobs.lyrics_dispatch.enqueue_song_alignment",
            side_effect=lambda song, **_: {"dispatched": dispatched[song.id]},
        ) as mock_enqueue,
    ):
        mock_files.return_value.get_vocals_path.side_effect = (
            lambda song_id, ext: SimpleNamespace(exists=lambda: song_id in vocals)
        )
        yield mock_enqueue


def _add(add_song, song_id, title, day, **fields):
    return add_song(
        song_id,
        title=title,
        artist="Queen",
        date_added=datetime(2026, 10, day),
        **fields,
    )


def test_each_selected_song_is_queued_as_its_own_alignment_job(add_song, db):
    _add(add_song, "a", "Bohemian Rhapsody", 1, synced_lyrics="[00:01.00]Is this")
    _add(
        add_song,
        "b",
        "Somebody to Love",
        2,
        synced_lyrics="[00:01.00]Can anybody",
        word_synced_lyrics="not json",
    )
    # Vocals but no lyrics at all: nothing to repair.
    _add(add_song, "c", "Bicycle Race", 3)
    # Needs alignment, but has no vocals stem to align against yet.
    _add(add_song, "d", "Radio Ga Ga", 4, synced_lyrics="[00:01.00]I'd sit alone")
    db.add(LyricsReport(song_id="b", kind="timing", words_key="k", report_count=1))
    db.commit()

    with _run_with(
        vocals={"a", "b", "c"}, dispatched={"a": True, "b": True}
    ) as mock_enqueue:
        result = batch_align_lyrics.run(mode="repair")

    assert [call.args[0].id for call in mock_enqueue.call_args_list] == ["a", "b"]
    assert all(
        call.kwargs == {"include_remote": True, "background": True}
        for call in mock_enqueue.call_args_list
    )
    assert result["selected"] == 2
    assert result["queued"] == 2
    assert result["alreadyRunning"] == 0
    assert result["skipped"] == 1
    assert result["reasons"]["no_word_timing"] == 1
    assert result["reasons"]["words_mismatch"] == 1
    assert result["reasons"]["reported"] == 1
    assert result["results"][1] == {
        "songId": "b",
        "title": "Queen — Somebody to Love",
        "status": "queued",
        "reasons": ["words_mismatch", "reported"],
    }


def test_a_song_already_aligning_is_not_queued_twice(add_song):
    _add(add_song, "a", "Bohemian Rhapsody", 1, synced_lyrics="[00:01.00]Is this")

    with _run_with(vocals={"a"}, dispatched={"a": False}):
        result = batch_align_lyrics.run(mode="repair")

    assert result["queued"] == 0
    assert result["alreadyRunning"] == 1
    assert result["results"][0]["status"] == "already_running"
