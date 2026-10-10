"""Enrichment and maintenance Celery tasks."""

from celery.utils.log import get_task_logger

from .celery_app import celery

logger = get_task_logger(__name__)


@celery.task(bind=True, name="cleanup_old_jobs")
def cleanup_old_jobs(self):
    """Periodically clean up old job records and temporary files."""
    logger.debug("Running job cleanup task")
    # Implement cleanup logic here
