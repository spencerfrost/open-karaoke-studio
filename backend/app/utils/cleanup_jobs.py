"""
Cleanup utility for stuck jobs on startup.
"""

import logging
from datetime import datetime

from app.db.models import JobStatus
from app.repositories.job_repository import JobRepository

logger = logging.getLogger(__name__)


def cleanup_stuck_jobs():
    repo = JobRepository()
    jobs = repo.get_all_jobs()  # List[Job]
    terminal_statuses = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
    now = datetime.now()
    cleaned = 0
    for job in jobs:
        if job.status not in terminal_statuses:
            job.status = JobStatus.FAILED
            job.error = "Job was stuck in non-terminal state on startup."
            job.completed_at = now
            repo.update(job)
            repo.dismiss_job(job.id)
            cleaned += 1
    if cleaned:
        logger.info(f"Marked {cleaned} stuck jobs as failed on startup.")
