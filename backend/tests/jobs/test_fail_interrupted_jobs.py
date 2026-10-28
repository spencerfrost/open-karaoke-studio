"""Tests for fail_interrupted_jobs, which fails the jobs a dead worker held."""

from datetime import timedelta

from app.db.models import Job, JobStatus, JobStep
from app.repositories.job_repository import JobRepository
from app.utils.cleanup_jobs import (
    INTERRUPTED_ERROR,
    INTERRUPTED_SONG_MESSAGE,
    fail_interrupted_jobs,
)
from app.utils.clock import utc_now


def _add_job(job_id, status, step=None, song_id=None):
    JobRepository().create(
        Job(
            id=job_id,
            filename=f"{job_id}.mp3",
            status=status,
            step=step,
            song_id=song_id,
            created_at=utc_now(),
        )
    )


def test_fails_started_jobs_and_their_songs(add_song, fetch_song):
    add_song("song-1", status="processing")
    _add_job("separating", JobStatus.PROCESSING, JobStep.SEPARATE, "song-1")
    _add_job("downloading", JobStatus.DOWNLOADING, JobStep.DOWNLOAD)

    assert fail_interrupted_jobs(["audio"]) == 2

    jobs = JobRepository()
    for job_id in ("separating", "downloading"):
        job = jobs.get_job(job_id)
        assert job.status == JobStatus.FAILED
        assert job.error == INTERRUPTED_ERROR
        assert abs(job.completed_at - utc_now()) < timedelta(minutes=1)
    song = fetch_song("song-1")
    assert song.status == "error"
    assert song.error_message == INTERRUPTED_SONG_MESSAGE


def test_leaves_pending_jobs_for_the_broker():
    _add_job("waiting", JobStatus.PENDING, JobStep.ALIGN)

    assert fail_interrupted_jobs(["lyrics"]) == 0
    assert JobRepository().get_job("waiting").status == JobStatus.PENDING


def test_only_touches_the_restarted_workers_queues():
    _add_job("separating", JobStatus.PROCESSING, JobStep.SEPARATE)
    _add_job("aligning", JobStatus.PROCESSING, JobStep.ALIGN)

    assert fail_interrupted_jobs(["lyrics"]) == 1
    jobs = JobRepository()
    assert jobs.get_job("aligning").status == JobStatus.FAILED
    assert jobs.get_job("separating").status == JobStatus.PROCESSING
    assert fail_interrupted_jobs(["enrichment"]) == 0


def test_failed_alignment_leaves_the_song_playable(add_song, fetch_song):
    add_song("song-1", status="processed")
    _add_job("aligning", JobStatus.PROCESSING, JobStep.ALIGN, "song-1")

    fail_interrupted_jobs(["lyrics"])

    assert fetch_song("song-1").status == "processed"


def test_leaves_finished_jobs_alone(add_song, fetch_song):
    add_song("song-1", status="processed")
    _add_job("done", JobStatus.COMPLETED, JobStep.SEPARATE, "song-1")
    _add_job("failed", JobStatus.FAILED, JobStep.ALIGN)
    _add_job("cancelled", JobStatus.CANCELLED)

    assert fail_interrupted_jobs(["audio", "enrichment", "lyrics"]) == 0

    jobs = JobRepository()
    assert jobs.get_job("done").status == JobStatus.COMPLETED
    assert jobs.get_job("failed").status == JobStatus.FAILED
    assert jobs.get_job("cancelled").status == JobStatus.CANCELLED
    assert fetch_song("song-1").status == "processed"
