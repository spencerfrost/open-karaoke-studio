"""Shared helpers and state for job tasks."""

import hashlib
from datetime import datetime
from typing import Optional

from app.db.models import Job, JobStatus
from app.repositories import JobRepository
from app.services.lyrics_timing import log_lyrics_event

LYRICS_JOB_ENGINE_TYPE = "lyrics_alignment"

# Keep a single repository instance shared by task modules.
job_repository = JobRepository()


def _get_lyrics_job_id(song_id: str) -> str:
    return f"lyrics-align:{song_id}"


def _make_alignment_cache_key(
    *,
    source_type: str,
    content: str,
    language: str,
    alignment_mode: str,
) -> tuple[str, str, str, str]:
    return (
        source_type,
        alignment_mode,
        language,
        hashlib.sha1(content.encode("utf-8")).hexdigest(),
    )


def _create_lyrics_alignment_job(
    song_id: str,
    title: Optional[str] = None,
    artist: Optional[str] = None,
    task_id: Optional[str] = None,
    status_message: str = "Queued lyrics alignment",
) -> str:
    lyrics_job_id = _get_lyrics_job_id(song_id)
    lyrics_job = Job(
        id=lyrics_job_id,
        filename="lyrics-alignment",
        status=JobStatus.PENDING,
        progress=0,
        status_message=status_message,
        task_id=task_id,
        song_id=song_id,
        title=title,
        artist=artist,
        engine_type=LYRICS_JOB_ENGINE_TYPE,
    )
    job_repository.create(lyrics_job)
    log_lyrics_event(
        song_id,
        "lyrics_job_queued",
        lyrics_job_id=lyrics_job_id,
        title=title,
        artist=artist,
        queued_at=lyrics_job.created_at,
    )
    return lyrics_job_id


def _update_lyrics_alignment_job(
    song_id: str,
    *,
    status: JobStatus,
    progress: int,
    message: str,
    error: Optional[str] = None,
) -> None:
    lyrics_job_id = _get_lyrics_job_id(song_id)
    lyrics_job = job_repository.get_by_id(lyrics_job_id)
    if not lyrics_job:
        lyrics_job = Job(
            id=lyrics_job_id,
            filename="lyrics-alignment",
            status=status,
            progress=progress,
            status_message=message,
            song_id=song_id,
            error=error,
            engine_type=LYRICS_JOB_ENGINE_TYPE,
        )
    else:
        lyrics_job.status = status
        lyrics_job.progress = progress
        lyrics_job.status_message = message
        lyrics_job.error = error

    if status == JobStatus.PROCESSING and lyrics_job.started_at is None:
        lyrics_job.started_at = datetime.now()
    if status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
        lyrics_job.completed_at = datetime.now()

    job_repository.update(lyrics_job)


def _complete_lyrics_alignment_job(
    song_id: str,
    *,
    status: JobStatus,
    message: str,
    error: Optional[str] = None,
) -> None:
    _update_lyrics_alignment_job(
        song_id,
        status=status,
        progress=100,
        message=message,
        error=error,
    )
    job_repository.delete_job(_get_lyrics_job_id(song_id))
