"""Queue lyrics alignment for a song, at most one run at a time.

Alignment has two queues on the same worker. `lyrics` is for runs someone is
waiting on: a new song, a fix a person asked for. `lyrics_backfill` is for
library-wide runs, and the worker only takes from it when `lyrics` is empty.
"""

import logging
from typing import Optional

from celery import uuid

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

    # The job row goes in first, carrying the task's id: the task only runs
    # while its row still names it (see alignment_is_still_wanted), and a free
    # worker can start it before this function returns.
    task_id = uuid()
    _create_lyrics_alignment_job(
        song.id,
        title=song.title,
        artist=song.artist,
        task_id=task_id,
        status_message="Queued lyrics alignment",
    )
    try:
        celery.send_task(
            "align_song_lyrics",
            args=[song.id],
            kwargs={
                "include_remote": include_remote,
                "source": source,
                "language": language,
            },
            queue=LYRICS_BACKFILL_QUEUE if background else LYRICS_QUEUE,
            task_id=task_id,
        )
    except Exception:
        # Nothing was queued, so the song mustn't read as aligning.
        job_repository.delete_job(job_id)
        raise

    return {
        "jobId": job_id,
        "taskId": task_id,
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


def alignment_is_still_wanted(song_id: str, task_id: Optional[str]) -> bool:
    """Whether the alignment task `task_id` should still run for `song_id`.

    Taking a queued alignment off the queue deletes its job row and revokes
    its task, but a revoke only lives in the memory of the workers running at
    that moment: a worker that was down, or restarts before it reaches the
    message, runs the task anyway. So the task checks its own job row. No row
    means it was taken off; a row naming another task means a newer run
    replaced it. A row with no task id (the one a new song's pipeline writes)
    belongs to whichever task comes. A task called directly has no id and
    always runs.
    """
    if not task_id:
        return True
    job = JobRepository().get_by_id(_get_lyrics_job_id(song_id))
    if job is None:
        return False
    return job.task_id is None or job.task_id == task_id


def cancel_queued_alignments(
    job_ids: list[str], task_ids: Optional[list[str]] = None
) -> int:
    """Take the alignments still waiting on the queue off it; returns how many.

    Each waiting job's task is revoked and its row removed, so the song reads
    as not aligning. A job already running is left to finish. A task whose
    revoke a worker misses finds its row gone and doesn't align
    (alignment_is_still_wanted).
    """
    return len(take_queued_alignments_off(job_ids, task_ids))


def take_queued_alignments_off(
    job_ids: list[str], task_ids: Optional[list[str]] = None
) -> list[str]:
    """cancel_queued_alignments, returning the songs taken off, in queue order,
    so a paused run can queue them again.

    `task_ids` are the tasks the run itself queued. A song's job id is the
    same whoever queued it, so with them a job that now belongs to another
    task (an alignment someone asked for by hand since) is left alone.
    """
    from app.db.database import get_db_session
    from app.db.models import DbJob

    with get_db_session() as session:
        query = session.query(DbJob).filter(
            DbJob.id.in_(job_ids), DbJob.status == JobStatus.PENDING.value
        )
        if task_ids is not None:
            query = query.filter(DbJob.task_id.in_(task_ids))
        waiting = query.all()
        order = {job_id: i for i, job_id in enumerate(job_ids)}
        waiting.sort(key=lambda job: order.get(job.id, len(order)))
        song_ids = [job.song_id for job in waiting if job.song_id]
        revoke_ids = [job.task_id for job in waiting if job.task_id]
        for job in waiting:
            session.delete(job)
        session.commit()
    if revoke_ids:
        try:
            celery.control.revoke(revoke_ids)
        except Exception:
            logger.warning(
                "Couldn't revoke %d queued alignments", len(revoke_ids), exc_info=True
            )
    logger.info("Took %d queued lyrics alignments off the queue", len(waiting))
    return song_ids


def pause_waiting_alignments(
    job_ids: list[str], task_ids: Optional[list[str]], reason: str
) -> list[str]:
    """Pause a run that waits on its songs' alignments: take the queued ones
    off the queue and ask the lyrics worker for its GPU memory back once the
    song it's on is done. Returns the songs taken off, in queue order."""
    song_ids = take_queued_alignments_off(job_ids, task_ids)
    try:
        celery.send_task("release_gpu_memory", kwargs={"reason": reason})
    except Exception:
        logger.warning("Couldn't queue the GPU memory release", exc_info=True)
    return song_ids


def requeue_paused_alignments(
    song_ids: list[str], *, include_remote: bool
) -> list[str]:
    """Queue a paused run's songs again, in the order they were waiting in.
    Returns the new tasks' ids. All or nothing: if one can't be queued, the
    ones queued before it come back off and the error is raised.

    A song already aligning again (someone asked for it meanwhile) is skipped.
    """
    from app.db.database import get_db_session
    from app.db.models import DbSong

    job_ids: list[str] = []
    task_ids: list[str] = []
    with get_db_session() as session:
        songs = {
            song.id: song
            for song in session.query(DbSong).filter(DbSong.id.in_(song_ids)).all()
        }
        try:
            for song_id in song_ids:
                song = songs.get(song_id)
                if song is None:
                    continue
                dispatch = enqueue_song_alignment(
                    song, include_remote=include_remote, background=True
                )
                if dispatch["dispatched"]:
                    job_ids.append(dispatch["jobId"])
                    task_ids.append(dispatch["taskId"])
        except Exception:
            take_queued_alignments_off(job_ids, task_ids)
            raise
    return task_ids


@celery.task(name="release_gpu_memory")
def release_gpu_memory(reason: str = "requested") -> bool:
    """Give back the GPU memory of the worker that runs this. Queued on the
    lyrics queue when an alignment run pauses, so it runs right after the song
    aligning now, on the worker that aligned it."""
    from app.services.gpu_idle_cleanup import release_gpu_memory_now

    return release_gpu_memory_now(reason)
