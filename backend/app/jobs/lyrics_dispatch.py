"""Queue lyrics alignment for a song, at most one run at a time."""

from typing import Optional

from app.db.models import JobStatus
from app.repositories import JobRepository

from ._shared import _create_lyrics_alignment_job, _get_lyrics_job_id
from .celery_app import celery

_IN_FLIGHT_STATUSES = {JobStatus.PENDING, JobStatus.DOWNLOADING, JobStatus.PROCESSING}


def enqueue_song_alignment(
    song,
    *,
    include_remote: bool,
    source: Optional[str] = None,
    language: Optional[str] = None,
) -> dict:
    """Queue align_song_lyrics for `song`, unless a run for it is already queued or running."""
    job_repository = JobRepository()
    job_id = _get_lyrics_job_id(song.id)
    existing_job = job_repository.get_by_id(job_id)

    if existing_job and existing_job.status in _IN_FLIGHT_STATUSES:
        return {
            "jobId": existing_job.id,
            "taskId": existing_job.task_id,
            "songId": song.id,
            "status": existing_job.status.value,
            "dispatched": False,
            "includeRemote": include_remote,
            "source": source,
            "language": language,
            "message": "Lyrics alignment already in progress.",
        }

    task = celery.send_task(
        "align_song_lyrics",
        args=[song.id],
        kwargs={
            "include_remote": include_remote,
            "source": source,
            "language": language,
        },
    )
    _create_lyrics_alignment_job(
        song.id,
        title=song.title,
        artist=song.artist,
        task_id=task.id,
        status_message="Queued lyrics alignment",
    )

    return {
        "jobId": job_id,
        "taskId": task.id,
        "songId": song.id,
        "status": JobStatus.PENDING.value,
        "dispatched": True,
        "includeRemote": include_remote,
        "source": source,
        "language": language,
        "message": "Lyrics alignment queued.",
    }


def realign_hand_picked_lyrics(song) -> Optional[dict]:
    """Time the lyrics a person just saved, once the song's vocals exist.

    Only the stored lyrics are used (the song is hand-picked), so nothing
    fetched replaces them. A run already going notices the change and starts
    again by itself.
    """
    from app.services.file_service import FileService

    if not (song.plain_lyrics or song.synced_lyrics):
        return None
    if not FileService().get_vocals_path(song.id, ".mp3").exists():
        return None
    return enqueue_song_alignment(song, include_remote=False)
