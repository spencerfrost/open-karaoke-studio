"""Tests for enqueue_song_alignment: which queue a run goes on, and one run per song."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.db.models import DbJob, DbSong, JobStatus
from app.jobs._shared import _get_lyrics_job_id
from app.jobs.lyrics_dispatch import (
    alignment_is_still_wanted,
    enqueue_song_alignment,
    requeue_paused_alignments,
    take_queued_alignments_off,
)
from app.jobs.lyrics_tasks import align_song_lyrics
from app.repositories.job_repository import JobRepository

SONG = SimpleNamespace(id="song-1", title="Bohemian Rhapsody", artist="Queen")


@pytest.fixture
def mock_celery(db):  # noqa: ARG001 - db gives each test a clean jobs table
    # The task's id is made up before it's sent, so the job row can carry it.
    task_ids = iter(f"task-{n}" for n in range(1, 10))
    with (
        patch("app.jobs.lyrics_dispatch.celery") as celery,
        patch("app.jobs.lyrics_dispatch.uuid", side_effect=lambda: next(task_ids)),
    ):
        yield celery


def _job():
    job = JobRepository().get_by_id(_get_lyrics_job_id(SONG.id))
    assert job is not None
    return job


def test_a_run_someone_is_waiting_on_goes_on_the_lyrics_queue(mock_celery):
    result = enqueue_song_alignment(SONG, include_remote=True)

    assert result["dispatched"] is True
    assert mock_celery.send_task.call_args.kwargs["queue"] == "lyrics"
    assert _job().status == JobStatus.PENDING
    assert _job().task_id == "task-1"


def test_a_library_run_goes_on_the_backfill_queue(mock_celery):
    enqueue_song_alignment(SONG, include_remote=True, background=True)

    assert mock_celery.send_task.call_args.kwargs["queue"] == "lyrics_backfill"


def test_a_waiting_run_replaces_a_queued_library_run(mock_celery):
    enqueue_song_alignment(SONG, include_remote=True, background=True)

    result = enqueue_song_alignment(SONG, include_remote=False)

    assert result["dispatched"] is True
    mock_celery.control.revoke.assert_called_once_with("task-1")
    assert mock_celery.send_task.call_args.kwargs["queue"] == "lyrics"
    assert mock_celery.send_task.call_args.kwargs["kwargs"]["include_remote"] is False
    assert _job().task_id == "task-2"


def test_a_library_run_leaves_a_queued_run_alone(mock_celery):
    enqueue_song_alignment(SONG, include_remote=True)

    result = enqueue_song_alignment(SONG, include_remote=True, background=True)

    assert result["dispatched"] is False
    mock_celery.control.revoke.assert_not_called()
    assert mock_celery.send_task.call_count == 1


def test_a_run_already_going_is_never_replaced(mock_celery):
    enqueue_song_alignment(SONG, include_remote=True, background=True)
    job = _job()
    job.status = JobStatus.PROCESSING
    JobRepository().update(job)

    result = enqueue_song_alignment(SONG, include_remote=False)

    assert result["dispatched"] is False
    mock_celery.control.revoke.assert_not_called()
    assert mock_celery.send_task.call_count == 1


def test_a_failed_revoke_still_queues_the_new_run(mock_celery):
    enqueue_song_alignment(SONG, include_remote=True, background=True)
    mock_celery.control.revoke.side_effect = ConnectionError("broker down")

    result = enqueue_song_alignment(SONG, include_remote=False)

    assert result["dispatched"] is True
    assert mock_celery.send_task.call_args.kwargs["queue"] == "lyrics"


def test_the_job_row_names_the_task_before_it_is_sent(mock_celery):
    seen = []
    mock_celery.send_task.side_effect = lambda *_a, **kwargs: seen.append(
        (_job().task_id, kwargs["task_id"])
    )

    enqueue_song_alignment(SONG, include_remote=True)

    assert seen == [("task-1", "task-1")]


def test_a_run_that_cannot_be_sent_leaves_no_job_behind(mock_celery):
    mock_celery.send_task.side_effect = ConnectionError("broker down")

    with pytest.raises(ConnectionError):
        enqueue_song_alignment(SONG, include_remote=True)

    assert JobRepository().get_by_id(_get_lyrics_job_id(SONG.id)) is None


class TestStillWanted:
    """A task checks its job row, because a revoke can miss a worker."""

    def test_the_task_its_job_row_names_runs(self, mock_celery):
        enqueue_song_alignment(SONG, include_remote=True, background=True)

        assert alignment_is_still_wanted(SONG.id, "task-1") is True

    def test_a_task_taken_off_the_queue_does_not_run(self, mock_celery):
        enqueue_song_alignment(SONG, include_remote=True, background=True)
        take_queued_alignments_off([_get_lyrics_job_id(SONG.id)], ["task-1"])

        assert alignment_is_still_wanted(SONG.id, "task-1") is False

    def test_a_task_replaced_by_a_newer_run_does_not_run(self, mock_celery):
        enqueue_song_alignment(SONG, include_remote=True, background=True)
        enqueue_song_alignment(SONG, include_remote=False)

        assert alignment_is_still_wanted(SONG.id, "task-1") is False
        assert alignment_is_still_wanted(SONG.id, "task-2") is True

    def test_a_job_row_with_no_task_belongs_to_whichever_task_comes(self, db):
        # A new song's pipeline writes the row, then sends the task.
        db.add(
            DbJob(
                id=_get_lyrics_job_id(SONG.id),
                filename="lyrics-alignment",
                status=JobStatus.PENDING.value,
                song_id=SONG.id,
            )
        )
        db.commit()

        assert alignment_is_still_wanted(SONG.id, "any-task") is True

    def test_a_task_called_directly_always_runs(self, db):
        assert alignment_is_still_wanted(SONG.id, None) is True

    def test_an_unwanted_task_aligns_nothing(self, db):
        with patch("app.jobs.lyrics_tasks._align_song_lyrics") as align:
            result = align_song_lyrics.apply(args=[SONG.id], task_id="gone").get()

        assert result == {"status": "skipped", "song_id": SONG.id}
        align.assert_not_called()


def test_taking_a_runs_songs_off_leaves_a_job_someone_else_queued(mock_celery):
    # The library run queued it as task-1; then someone asked for it by hand.
    enqueue_song_alignment(SONG, include_remote=True, background=True)
    enqueue_song_alignment(SONG, include_remote=False)
    mock_celery.control.revoke.reset_mock()

    taken_off = take_queued_alignments_off([_get_lyrics_job_id(SONG.id)], ["task-1"])

    assert taken_off == []
    assert _job().task_id == "task-2"
    mock_celery.control.revoke.assert_not_called()


class TestRequeuePaused:
    @pytest.fixture
    def songs(self, db):
        db.add_all([DbSong(id=song_id, title=song_id) for song_id in ("a", "b", "c")])
        db.commit()

    def test_songs_are_queued_again_in_the_order_they_waited_in(
        self, mock_celery, songs
    ):
        task_ids = requeue_paused_alignments(["c", "a", "b"], include_remote=False)

        assert task_ids == ["task-1", "task-2", "task-3"]
        assert [
            call.kwargs["args"] for call in mock_celery.send_task.call_args_list
        ] == [
            ["c"],
            ["a"],
            ["b"],
        ]
        assert all(
            call.kwargs["queue"] == "lyrics_backfill"
            for call in mock_celery.send_task.call_args_list
        )

    def test_a_failure_part_way_takes_the_queued_ones_back_off(
        self, mock_celery, songs, db
    ):
        mock_celery.send_task.side_effect = [None, ConnectionError("broker down")]

        with pytest.raises(ConnectionError):
            requeue_paused_alignments(["a", "b", "c"], include_remote=False)

        assert db.query(DbJob).count() == 0
        mock_celery.control.revoke.assert_called_once_with(["task-1"])
