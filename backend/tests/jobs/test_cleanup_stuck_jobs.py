"""Tests for cleanup_stuck_jobs, which fails jobs left unfinished by a restart."""

from datetime import timedelta

from app.db.models import Job, JobStatus
from app.repositories.job_repository import JobRepository
from app.utils.cleanup_jobs import cleanup_stuck_jobs
from app.utils.clock import utc_now


def _add_job(job_id, status, song_id=None):
    JobRepository().create(
        Job(
            id=job_id,
            filename=f"{job_id}.mp3",
            status=status,
            song_id=song_id,
            created_at=utc_now(),
        )
    )


def test_fails_unfinished_jobs_and_their_songs(add_song, fetch_song):
    add_song("song-1", status="processing")
    _add_job("processing", JobStatus.PROCESSING, song_id="song-1")
    _add_job("pending", JobStatus.PENDING)

    cleanup_stuck_jobs()

    jobs = JobRepository()
    for job_id in ("processing", "pending"):
        job = jobs.get_job(job_id)
        assert job.status == JobStatus.FAILED
        assert job.error == "Job was stuck in non-terminal state on startup."
        assert abs(job.completed_at - utc_now()) < timedelta(minutes=1)
    song = fetch_song("song-1")
    assert song.status == "error"
    assert song.error_message == "Processing was interrupted (server restarted)."


def test_leaves_finished_jobs_alone(add_song, fetch_song):
    add_song("song-1", status="processed")
    _add_job("done", JobStatus.COMPLETED, song_id="song-1")
    _add_job("failed", JobStatus.FAILED)
    _add_job("cancelled", JobStatus.CANCELLED)

    cleanup_stuck_jobs()

    jobs = JobRepository()
    assert jobs.get_job("done").status == JobStatus.COMPLETED
    assert jobs.get_job("failed").status == JobStatus.FAILED
    assert jobs.get_job("cancelled").status == JobStatus.CANCELLED
    assert fetch_song("song-1").status == "processed"
