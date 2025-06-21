"""
Cleanup utility for stuck jobs on startup.
"""

from .repositories import JobRepository
from .db.models import JobStatus
from datetime import datetime
import logging

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
            cleaned += 1
    if cleaned:
        logger.info(f"Marked {cleaned} stuck jobs as failed on startup.")
