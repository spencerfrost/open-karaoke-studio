"""Queue lyrics alignment for a song, at most one run at a time.

Alignment has two queues on the same worker. `lyrics` is for runs someone is
waiting on: a new song, a fix a person asked for. `lyrics_backfill` is for
library-wide runs, and the worker only takes from it when `lyrics` is empty.
"""

import logging
from typing import Optional

from app.db.models import JobStatus
from app.repositories import JobRepository

from ._shared import _create_lyrics_alignment_job, _get_lyrics_job_id
from .celery_app import celery

logger = logging.getLogger(__name__)

LYRICS_QUEUE = "lyrics"
LYRICS_BACKFILL_QUEUE = "lyrics_backfill"

_IN_FLIGHT_STATUSES = {JobStatus.PENDING, JobStatus.DOWNLOADING, JobStatus.PROCESSING}


def enqueue_song_alignment(
    song,
    *,
    include_remote: bool,
    source: Optional[str] = None,
    language: Optional[str] = None,
    background: bool = False,
) -> dict:
    """Queue align_song_lyrics for `song`, unless a run for it is already queued or running.

    `background` runs go on the low-priority queue. A run someone is waiting on
    that finds the song still queued replaces the queued run, which may be
    sitting behind a whole library run.
    """
    job_repository = JobRepository()
    job_id = _get_lyrics_job_id(song.id)
    existing_job = job_repository.get_by_id(job_id)

    if (
        not background
        and existing_job
        and existing_job.status == JobStatus.PENDING
        and existing_job.task_id
    ):
        # Not started yet, so revoking it loses nothing. A worker that misses
        # the revoke just runs the song a second time.
        try:
            celery.control.revoke(existing_job.task_id)
        except Exception:
            logger.warning(
                "Couldn't revoke queued alignment %s for song %s",
                existing_job.task_id,
                song.id,
                exc_info=True,
            )
        existing_job = None

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
        queue=LYRICS_BACKFILL_QUEUE if background else LYRICS_QUEUE,
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


def cancel_queued_alignments(job_ids: list[str]) -> int:
    """Take the alignments still waiting on the queue off it; returns how many.

    Each waiting job's task is revoked and its row removed, so the song reads
    as not aligning. A job already running is left to finish. A revoke a
    worker misses only means that song is aligned anyway.
    """
    return len(take_queued_alignments_off(job_ids))


def take_queued_alignments_off(job_ids: list[str]) -> list[str]:
    """cancel_queued_alignments, returning the songs taken off, in queue order,
    so a paused run can queue them again."""
    from app.db.database import get_db_session
    from app.db.models import DbJob

    with get_db_session() as session:
        waiting = (
            session.query(DbJob)
            .filter(DbJob.id.in_(job_ids), DbJob.status == JobStatus.PENDING.value)
            .all()
        )
        order = {job_id: i for i, job_id in enumerate(job_ids)}
        waiting.sort(key=lambda job: order.get(job.id, len(order)))
        song_ids = [job.song_id for job in waiting if job.song_id]
        task_ids = [job.task_id for job in waiting if job.task_id]
        for job in waiting:
            session.delete(job)
        session.commit()
    if task_ids:
        try:
            celery.control.revoke(task_ids)
        except Exception:
            logger.warning(
                "Couldn't revoke %d queued alignments", len(task_ids), exc_info=True
            )
    logger.info("Took %d queued lyrics alignments off the queue", len(waiting))
    return song_ids


@celery.task(name="release_gpu_memory")
def release_gpu_memory(reason: str = "requested") -> bool:
    """Give back the GPU memory of the worker that runs this. Queued on the
    lyrics queue when an alignment run pauses, so it runs right after the song
    aligning now, on the worker that aligned it."""
    from app.services.gpu_idle_cleanup import release_gpu_memory_now

    return release_gpu_memory_now(reason)
