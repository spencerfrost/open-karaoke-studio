"""
Fail the jobs a dead Celery worker left behind.

A worker that crashes mid-task (a native segfault in CUDA code takes the whole
process down, with no Python exception) leaves its job row "processing"
forever: the task was already taken off the queue, so nothing will ever run it
again. When a worker starts, any job it would have been running can't still be
running, so it is failed here.

Only started jobs. A pending job's message is still in the broker (or comes
back to it), so it will run once a worker picks it up.
"""

import logging
from typing import Iterable, Optional

from app.db.models import JobStatus, JobStep
from app.repositories.job_repository import JobRepository
from app.repositories.song_repository import SongRepository
from app.utils.clock import utc_now

logger = logging.getLogger(__name__)

# Which job steps run on which queue; mirrors task_routes in jobs/celery_app.
# None is a main pipeline job from before jobs carried a step.
QUEUE_STEPS: dict[str, set[Optional[JobStep]]] = {
    "audio": {JobStep.DOWNLOAD, JobStep.SEPARATE, None},
    "lyrics": {JobStep.ALIGN},
}

STARTED_STATUSES = {JobStatus.DOWNLOADING, JobStatus.PROCESSING}
INTERRUPTED_ERROR = "The worker stopped while running this job."
INTERRUPTED_SONG_MESSAGE = "Processing was interrupted (the worker restarted)."


def fail_interrupted_jobs(queues: Iterable[str]) -> int:
    """Fail started jobs on `queues`. Returns how many.

    A failed download or separation leaves the song unplayable, so the song is
    marked as errored too. A failed alignment only loses the word timings: the
    song plays with the lyrics it already has, the same as any failed alignment.
    """
    steps: set[Optional[JobStep]] = set()
    for queue in queues:
        steps |= QUEUE_STEPS.get(queue, set())
    if not steps:
        return 0

    repo = JobRepository()
    now = utc_now()
    failed = 0
    for job in repo.get_in_flight_jobs():
        if job.status not in STARTED_STATUSES or job.step not in steps:
            continue
        job.status = JobStatus.FAILED
        job.error = INTERRUPTED_ERROR
        job.completed_at = now
        repo.update(job)
        if job.song_id and job.step != JobStep.ALIGN:
            from app.db.database import get_db_session

            with get_db_session() as session:
                SongRepository(session).update(
                    job.song_id,
                    status="error",
                    error_message=INTERRUPTED_SONG_MESSAGE,
                )
        failed += 1
    if failed:
        logger.warning("Failed %d jobs interrupted by a worker restart.", failed)
    return failed
