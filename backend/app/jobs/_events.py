"""Event bridge for translating job events into job status broadcasts."""

from app.db.models import Job, JobStatus
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)
_subscriptions_initialized = False


def broadcast_job_event(job, was_created: bool = False):
    """Broadcast a job event via WebSocket if available."""
    # WebSocket broadcasting has been migrated to FastAPI.
    # Job events are now handled by the FastAPI WebSocket server.
    # Frontend polls the database via REST API for job status updates.
    pass


def handle_job_event(event):
    """Handle emitted job events from the internal event system."""
    try:
        from app.utils.events import JobEvent

        if isinstance(event, JobEvent):
            job_data = event.job_data
            job = Job(
                id=job_data["id"],
                filename=job_data.get("filename", ""),
                status=JobStatus(job_data["status"]),
                title=job_data.get("title"),
                artist=job_data.get("artist"),
                status_message=job_data.get("message"),
                progress=job_data.get("progress", 0),
                error=job_data.get("error"),
                task_id=job_data.get("task_id"),
                song_id=job_data.get("song_id"),
                created_at=job_data.get("created_at"),
                started_at=job_data.get("started_at"),
                completed_at=job_data.get("completed_at"),
            )

            broadcast_job_event(job, event.was_created)

    except Exception as e:
        logger.error("Error handling job event: %s", e, exc_info=True)


def setup_event_subscriptions() -> None:
    """Set up event subscriptions for the jobs package."""
    global _subscriptions_initialized
    if _subscriptions_initialized:
        return

    try:
        from app.utils.events import subscribe_to_job_events

        subscribe_to_job_events(handle_job_event)
        _subscriptions_initialized = True
        logger.info("Jobs module subscribed to job events")
    except Exception as e:
        logger.error("Failed to set up job event subscriptions: %s", e)
