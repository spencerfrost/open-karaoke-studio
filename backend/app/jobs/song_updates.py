"""Bring a song up to date when it's queued to sing.

A change to a processing step (a new alignment method, a new backfill) reaches
a song the next time someone queues it, so the library-wide runs on the admin
jobs page don't have to finish first.
"""

import logging

from .celery_app import celery
from .lyrics_dispatch import enqueue_song_alignment

logger = logging.getLogger(__name__)


def update_queued_song(song_id: str) -> list[str]:
    """Queue every step this song is behind on; returns the steps queued.

    The steps are the batch jobs with a per-song task, each for a song its
    "missing" run would include, plus word timing when the song's is from an
    older version of alignment. A song still being processed is skipped: its
    pipeline runs all of this.

    Never raises: the song is already in the queue, and it plays as it is.
    """
    try:
        return _update_queued_song(song_id)
    except Exception:
        logger.warning("Couldn't update queued song %s", song_id, exc_info=True)
        return []


def _update_queued_song(song_id: str) -> list[str]:
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository
    from app.services.batch_jobs import JOBS, song_needs
    from app.services.file_service import FileService
    from app.services.processing_versions import WORD_TIMING_VERSION, is_behind

    queued: list[str] = []
    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        if song is None or song.status != "processed":
            return queued

        for job in JOBS.values():
            if job.song_task and song_needs(session, job, song_id):
                celery.send_task("update_song_step", args=[job.kind, song_id])
                queued.append(job.kind)

        if (
            is_behind(song.word_timing_version, WORD_TIMING_VERSION)
            and FileService().get_vocals_path(song_id, ".mp3").exists()
        ):
            # A song with lyrics keeps its words and is only re-timed: nobody
            # wants different words minutes before singing them.
            has_lyrics = bool(song.synced_lyrics or song.plain_lyrics)
            dispatch = enqueue_song_alignment(song, include_remote=not has_lyrics)
            if dispatch["dispatched"]:
                queued.append("word_timing")

    if queued:
        logger.info("Queued song %s is behind on: %s", song_id, ", ".join(queued))
    return queued
