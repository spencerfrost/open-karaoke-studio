"""Tests for pausing batch runs between songs, and resuming them.

The duration backfill stands in for every song-by-song task: they share
run.begin and run.each. Rows are real; librosa and the GPU are mocked.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest

from app.db.database import SessionLocal
from app.db.models import BatchRun
from app.jobs._batch_runs import resume_interrupted_runs
from app.jobs.batch_tasks import batch_backfill_duration
from app.repositories.batch_run_repository import STALE_AFTER, BatchRunRepository
from app.utils.clock import utc_now

SONGS = ["a", "b", "c", "d", "e"]


def _new_run(kind="duration", mode="missing", **fields):
    with SessionLocal() as session:
        run = BatchRunRepository(session).create(kind, mode)
        for name, value in fields.items():
            setattr(run, name, value)
        session.commit()
        return run.id


def _status(run_id):
    with SessionLocal() as session:
        return session.get(BatchRun, run_id).status


def _fetch_run(run_id):
    with SessionLocal() as session:
        return session.get(BatchRun, run_id)


def _press(action, run_id):
    with SessionLocal() as session:
        repo = BatchRunRepository(session)
        return getattr(repo, action)(repo.get(run_id))


@pytest.fixture
def songs(add_song, library):
    for song_id in SONGS:
        add_song(song_id)
        (library / song_id).mkdir()
        (library / song_id / "original.mp3").write_bytes(b"fake")
    return SONGS


@pytest.fixture
def released():
    with patch(
        "app.services.gpu_idle_cleanup.release_gpu_memory_now", return_value=True
    ) as release:
        yield release


def _pause_after(count, run_id):
    """librosa.get_duration that presses Pause once `count` songs are measured."""
    measured = []

    def get_duration(path):
        measured.append(path.split("/")[-2])
        if len(measured) == count:
            _press("pause", run_id)
        return 200.0

    return measured, patch("librosa.get_duration", side_effect=get_duration)


class TestPause:
    def test_pause_finishes_the_song_and_stops_before_the_next(self, songs, released):
        run_id = _new_run()
        measured, duration = _pause_after(2, run_id)

        with duration:
            batch_backfill_duration(mode="missing", run_id=run_id)

        run = _fetch_run(run_id)
        assert measured == songs[:2]
        assert (run.status, run.done) == ("paused", 2)
        assert run.finished_at is None
        released.assert_called_once()

    def test_resume_carries_on_after_the_songs_it_handled(self, songs, released):
        run_id = _new_run()
        measured, duration = _pause_after(2, run_id)
        with duration:
            batch_backfill_duration(mode="missing", run_id=run_id)

        assert _press("unpause", run_id) is True  # needs its task queued again
        assert _status(run_id) == "queued"
        with duration, patch("app.jobs.batch_tasks._select") as select:
            batch_backfill_duration(mode="missing", run_id=run_id)

        select.assert_not_called()
        assert measured == songs
        run = _fetch_run(run_id)
        assert (run.status, run.done) == ("done", 5)

    def test_a_paused_run_does_not_resume_when_the_worker_starts(self, songs):
        run_id = _new_run(status="paused", item_ids=SONGS)

        with patch("app.jobs.celery_app.celery.send_task") as send_task:
            assert resume_interrupted_runs(["enrichment"]) == 0

        send_task.assert_not_called()
        assert _status(run_id) == "paused"

    def test_a_pausing_run_whose_worker_restarted_is_paused(self, songs):
        run_id = _new_run(status="pausing", item_ids=SONGS)

        with patch("app.jobs.celery_app.celery.send_task") as send_task:
            resume_interrupted_runs(["enrichment"])

        send_task.assert_not_called()
        assert _status(run_id) == "paused"

    def test_a_pausing_run_stopped_by_a_shutdown_stays_paused(self, songs):
        run_id = _new_run(status="pausing")

        with SessionLocal() as session:
            BatchRunRepository(session).interrupt(run_id)

        assert _status(run_id) == "paused"

    def test_a_task_starting_on_a_paused_run_stops_straight_away(self, songs, released):
        # Paused while queued; the revoke missed and the task started anyway.
        run_id = _new_run(status="paused")

        with patch("librosa.get_duration") as get_duration:
            batch_backfill_duration(mode="missing", run_id=run_id)

        get_duration.assert_not_called()
        assert _status(run_id) == "paused"

    def test_progress_while_pausing_does_not_mark_it_running(self, songs):
        run_id = _new_run(status="pausing")

        with SessionLocal() as session:
            BatchRunRepository(session).advance(run_id, ok=True)

        assert _status(run_id) == "pausing"

    def test_resume_while_still_pausing_needs_no_new_task(self, songs):
        run_id = _new_run(status="pausing")

        assert _press("unpause", run_id) is False
        assert _status(run_id) == "running"

    def test_a_quiet_pausing_run_reads_as_paused(self, songs):
        run_id = _new_run(status="pausing", updated_at=utc_now() - STALE_AFTER * 2)

        with SessionLocal() as session:
            BatchRunRepository(session).interrupt_stale()

        assert _status(run_id) == "paused"

    def test_pausing_a_queued_or_interrupted_run_pauses_it_now(self, songs):
        queued = _new_run()
        interrupted = _new_run(kind="loudness", status="interrupted")

        _press("pause", queued)
        _press("pause", interrupted)

        assert (_status(queued), _status(interrupted)) == ("paused", "paused")

    def test_a_paused_run_still_blocks_a_second_run(self, songs):
        _new_run(status="paused", updated_at=utc_now() - timedelta(days=1))

        with SessionLocal() as session:
            assert BatchRunRepository(session).active("duration") is not None
