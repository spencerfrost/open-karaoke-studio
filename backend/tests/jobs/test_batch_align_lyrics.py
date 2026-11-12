"""Tests for the library-wide lyrics alignment run: one align_song_lyrics job per song."""

from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from app.db.database import SessionLocal
from app.db.models import BatchRun, DbJob, JobStatus, LyricsReport
from app.jobs.batch_tasks import batch_align_lyrics
from app.jobs.lyrics_dispatch import cancel_queued_alignments
from app.repositories.batch_run_repository import BatchRunRepository


@contextmanager
def _run_with(*, vocals, dispatched):
    """Only `vocals` songs have a vocals stem; `dispatched` says which jobs get queued."""
    with (
        patch("app.services.lyrics_repair.FileService") as mock_files,
        patch(
            "app.jobs.lyrics_dispatch.enqueue_song_alignment",
            side_effect=lambda song, **_: {
                "dispatched": dispatched[song.id],
                "jobId": f"lyrics-align:{song.id}",
            },
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


def test_retime_keeps_each_songs_lyrics_and_skips_songs_without_any(add_song):
    _add(add_song, "a", "Bohemian Rhapsody", 1, synced_lyrics="[00:01.00]Is this")
    _add(add_song, "b", "Somebody to Love", 2, plain_lyrics="Can anybody")
    # No lyrics to keep: a re-time has nothing to time.
    _add(add_song, "c", "Bicycle Race", 3)

    with _run_with(
        vocals={"a", "b", "c"}, dispatched={"a": True, "b": True}
    ) as mock_enqueue:
        result = batch_align_lyrics.run(mode="retime")

    assert [call.args[0].id for call in mock_enqueue.call_args_list] == ["a", "b"]
    assert all(
        call.kwargs == {"include_remote": False, "background": True}
        for call in mock_enqueue.call_args_list
    )
    assert result["queued"] == 2


def _job(song_id, status, task_id=None):
    return DbJob(
        id=f"lyrics-align:{song_id}",
        filename="lyrics-alignment",
        status=status.value,
        song_id=song_id,
        task_id=task_id,
    )


def _refreshed_run(run_id):
    with SessionLocal() as session:
        BatchRunRepository(session).refresh_handed_off()
        run = session.get(BatchRun, run_id)
        return run.status, run.total, run.done


def test_the_run_stays_open_until_the_songs_it_queued_have_aligned(add_song, db):
    _add(add_song, "a", "Bohemian Rhapsody", 1, synced_lyrics="[00:01.00]Is this")
    _add(add_song, "b", "Somebody to Love", 2, synced_lyrics="[00:01.00]Can")
    # Already aligning when the run starts: not queued, so not waited on.
    _add(add_song, "c", "Bicycle Race", 3, synced_lyrics="[00:01.00]Bicycle")
    with SessionLocal() as session:
        run_id = BatchRunRepository(session).create("lyrics_alignment", "retime").id

    with _run_with(
        vocals={"a", "b", "c"}, dispatched={"a": True, "b": True, "c": False}
    ):
        batch_align_lyrics.run(mode="retime", run_id=run_id)
    # What enqueue_song_alignment would have written.
    db.add_all([_job("a", JobStatus.PENDING), _job("b", JobStatus.PROCESSING)])
    db.commit()

    assert _refreshed_run(run_id) == ("running", 2, 0)

    # A finished alignment's job row is deleted.
    db.query(DbJob).filter(DbJob.id == "lyrics-align:b").delete()
    db.commit()
    assert _refreshed_run(run_id) == ("running", 2, 1)

    db.query(DbJob).filter(DbJob.id == "lyrics-align:a").delete()
    db.commit()
    assert _refreshed_run(run_id) == ("done", 2, 2)


def test_a_run_that_queued_nothing_finishes_at_once(add_song):
    _add(add_song, "a", "Bohemian Rhapsody", 1, synced_lyrics="[00:01.00]Is this")
    with SessionLocal() as session:
        run_id = BatchRunRepository(session).create("lyrics_alignment", "retime").id

    with _run_with(vocals={"a"}, dispatched={"a": False}):
        batch_align_lyrics.run(mode="retime", run_id=run_id)

    assert _refreshed_run(run_id)[0] == "done"


def test_stopping_takes_waiting_alignments_off_the_queue(db):
    db.add_all(
        [
            _job("a", JobStatus.PENDING, task_id="t-a"),
            _job("b", JobStatus.PENDING, task_id="t-b"),
            _job("c", JobStatus.PROCESSING, task_id="t-c"),
        ]
    )
    db.commit()

    with patch("app.jobs.lyrics_dispatch.celery.control.revoke") as revoke:
        stopped = cancel_queued_alignments(
            ["lyrics-align:a", "lyrics-align:b", "lyrics-align:c"]
        )

    assert stopped == 2
    revoke.assert_called_once_with(["t-a", "t-b"])
    db.expire_all()
    # The one aligning now is left to finish.
    assert [job.id for job in db.query(DbJob).all()] == ["lyrics-align:c"]
