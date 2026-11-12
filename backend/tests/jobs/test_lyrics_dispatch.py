"""Tests for enqueue_song_alignment: which queue a run goes on, and one run per song."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.db.models import JobStatus
from app.jobs._shared import _get_lyrics_job_id
from app.jobs.lyrics_dispatch import enqueue_song_alignment
from app.repositories.job_repository import JobRepository

SONG = SimpleNamespace(id="song-1", title="Bohemian Rhapsody", artist="Queen")


@pytest.fixture
def mock_celery(db):  # noqa: ARG001 - db gives each test a clean jobs table
    with patch("app.jobs.lyrics_dispatch.celery") as celery:
        task_ids = iter(f"task-{n}" for n in range(1, 10))
        celery.send_task.side_effect = lambda *_args, **_kwargs: SimpleNamespace(
            id=next(task_ids)
        )
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
