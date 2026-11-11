"""Tests for stopping batch runs between songs at worker shutdown, and resuming them.

The duration backfill stands in for every song-by-song task: they share
run.begin and run.each. Rows are real; librosa and Celery dispatch are mocked.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.db.database import SessionLocal
from app.db.models import BatchRun
from app.jobs import _batch_runs
from app.jobs._batch_runs import resume_interrupted_runs, worker_stopping
from app.jobs.batch_tasks import batch_backfill_duration
from app.repositories.batch_run_repository import (
    STALE_AFTER,
    STALE_MESSAGE,
    WAITING_ON_KEY,
    BatchRunRepository,
)
from app.utils.clock import utc_now

SONGS = ["a", "b", "c", "d", "e"]


def _new_run(kind="duration", mode="missing", **fields):
    with SessionLocal() as session:
        run = BatchRunRepository(session).create(kind, mode)
        for name, value in fields.items():
            setattr(run, name, value)
        session.commit()
        return run.id


def _fetch_run(run_id):
    with SessionLocal() as session:
        run = session.get(BatchRun, run_id)
        run.item_ids  # Load the deferred column before the session closes.
        return run


@pytest.fixture
def songs(add_song, library):
    for song_id in SONGS:
        add_song(song_id)
        (library / song_id).mkdir()
        (library / song_id / "original.mp3").write_bytes(b"fake")
    return SONGS


@pytest.fixture
def measured():
    """Song ids in the order librosa was asked about them."""
    order = []

    def get_duration(path):
        order.append(path.split("/")[-2])
        return 200.0

    with patch("librosa.get_duration", side_effect=get_duration):
        yield order


def _stop_after(count, measured):
    """worker_stopping that turns true once `count` songs have been measured."""
    return patch.object(
        _batch_runs, "worker_stopping", side_effect=lambda: len(measured) >= count
    )


class TestStopAndResume:
    def test_shutdown_stops_between_songs_and_marks_the_run_interrupted(
        self, songs, measured
    ):
        run_id = _new_run()

        with _stop_after(2, measured):
            batch_backfill_duration(mode="missing", run_id=run_id)

        run = _fetch_run(run_id)
        assert measured == songs[:2]
        assert (run.status, run.total, run.done, run.failed) == ("interrupted", 5, 2, 0)
        assert run.item_ids == songs
        assert run.finished_at is None

    def test_resumed_run_carries_on_after_the_songs_it_handled(self, songs, measured):
        run_id = _new_run()
        with _stop_after(2, measured):
            batch_backfill_duration(mode="missing", run_id=run_id)

        # Resuming uses the saved ids: a fresh selection would differ, since the
        # first two songs aren't missing a duration any more.
        with patch("app.jobs.batch_tasks._select") as select:
            result = batch_backfill_duration(mode="missing", run_id=run_id)

        select.assert_not_called()
        assert measured == songs
        assert result["processed"] == 3
        run = _fetch_run(run_id)
        assert (run.status, run.total, run.done, run.failed) == ("done", 5, 5, 0)

    def test_skipped_and_failed_songs_count_towards_where_it_resumes(
        self, songs, library
    ):
        run_id = _new_run()
        (library / "a" / "original.mp3").unlink()  # Skipped: counted as done.
        measured = []

        def get_duration(path):
            song_id = path.split("/")[-2]
            measured.append(song_id)
            if song_id == "b":
                raise RuntimeError("not an mp3")
            return 200.0

        with patch("librosa.get_duration", side_effect=get_duration):
            # a skipped, b failed, c measured; then the worker stops.
            with _stop_after(2, measured):
                batch_backfill_duration(mode="missing", run_id=run_id)
            run = _fetch_run(run_id)
            assert (run.status, run.done, run.failed) == ("interrupted", 2, 1)

            batch_backfill_duration(mode="missing", run_id=run_id)

        assert measured == ["b", "c", "d", "e"]
        run = _fetch_run(run_id)
        assert (run.status, run.done, run.failed) == ("done", 4, 1)

    def test_a_cancelled_interrupted_run_does_not_resume(self, songs, measured):
        run_id = _new_run()
        with _stop_after(2, measured):
            batch_backfill_duration(mode="missing", run_id=run_id)
        with SessionLocal() as session:
            repo = BatchRunRepository(session)
            repo.cancel(repo.get(run_id))

        batch_backfill_duration(mode="missing", run_id=run_id)

        assert measured == songs[:2]
        assert _fetch_run(run_id).status == "cancelled"

    def test_without_a_run_id_it_still_stops(self, songs, measured):
        with _stop_after(1, measured):
            result = batch_backfill_duration(mode="missing")

        assert measured == songs[:1]
        assert result["processed"] == 1


class TestWorkerStopping:
    @pytest.fixture
    def state(self):
        from celery.worker import state

        saved = (state.should_stop, state.should_terminate)
        yield state
        state.should_stop, state.should_terminate = saved

    def test_not_stopping(self, state):
        state.should_stop = state.should_terminate = None
        assert worker_stopping() is False

    def test_warm_shutdown_sets_exit_code_zero(self, state):
        state.should_stop, state.should_terminate = 0, None
        assert worker_stopping() is True

    def test_cold_shutdown(self, state):
        state.should_stop, state.should_terminate = None, True
        assert worker_stopping() is True


class TestResumeInterruptedRuns:
    @pytest.fixture
    def send_task(self):
        task = MagicMock(id="task-new")
        with patch(
            "app.jobs.celery_app.celery.send_task", return_value=task
        ) as send_task:
            yield send_task

    def test_requeues_interrupted_and_orphaned_running_runs(self, send_task):
        interrupted = _new_run("loudness", "all", status="interrupted", done=3)
        orphaned = _new_run("singing_map", "missing", status="running")
        _new_run("vocal_range", "all")  # Queued: its message is still in Redis.
        _new_run("duration", "missing", status="done")
        _new_run(
            "lyrics_alignment",
            "retime",
            status="running",
            report={WAITING_ON_KEY: ["job-1"]},
        )

        assert resume_interrupted_runs(["enrichment"]) == 2

        assert [c.args[0] for c in send_task.mock_calls] == [
            "batch_backfill_loudness",
            "batch_backfill_singing_map",
        ]
        assert send_task.mock_calls[0].kwargs == {
            "kwargs": {"mode": "all", "run_id": interrupted}
        }
        for run_id in (interrupted, orphaned):
            run = _fetch_run(run_id)
            assert (run.status, run.celery_task_id) == ("interrupted", "task-new")

    def test_other_workers_resume_nothing(self, send_task):
        _new_run("loudness", "all", status="interrupted")

        assert resume_interrupted_runs(["audio"]) == 0
        assert resume_interrupted_runs(["lyrics", "lyrics_backfill"]) == 0
        send_task.assert_not_called()


class TestStaleRuns:
    def test_a_quiet_running_run_becomes_interrupted(self, db):
        run_id = _new_run(
            status="running", updated_at=utc_now() - STALE_AFTER - timedelta(minutes=1)
        )

        assert BatchRunRepository(db).interrupt_stale() == 1

        run = _fetch_run(run_id)
        assert (run.status, run.error) == ("interrupted", STALE_MESSAGE)

    def test_a_handed_off_run_is_left_alone(self, db):
        run_id = _new_run(
            "lyrics_alignment",
            "retime",
            status="running",
            report={WAITING_ON_KEY: ["job-1"]},
            updated_at=utc_now() - STALE_AFTER - timedelta(minutes=1),
        )

        assert BatchRunRepository(db).interrupt_stale() == 0
        assert _fetch_run(run_id).status == "running"

    def test_progress_from_a_live_task_marks_it_running_again(self, db):
        run_id = _new_run(status="interrupted", error=STALE_MESSAGE)

        BatchRunRepository(db).advance(run_id, ok=True)

        run = _fetch_run(run_id)
        assert (run.status, run.error, run.done) == ("running", None, 1)
