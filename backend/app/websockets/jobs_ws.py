"""
WebSocket handlers for jobs queue events.

This module provides real-time job status updates via WebSocket connections,
replacing the need for HTTP polling.
"""

from typing import Any, Dict

from flask import request
from flask_socketio import emit, join_room, leave_room

from .socketio import socketio


@socketio.on("connect", namespace="/jobs")
def handle_connect():
    """Handle client connection to the jobs namespace."""
    print("Client connected to jobs namespace")
    emit("connected", {"status": "connected"})


@socketio.on("disconnect", namespace="/jobs")
def handle_disconnect():
    """Handle client disconnection from the jobs namespace."""
    print("Client disconnected from jobs namespace")


@socketio.on("subscribe_to_jobs", namespace="/jobs")
def handle_subscribe_to_jobs():
    """Handle client subscription to job updates."""
    join_room("jobs_updates")
    emit("subscribed", {"status": "subscribed to job updates"})

    # Send the current jobs list to the newly subscribed client
    # Use lazy import to avoid circular dependency
    from ..services.jobs_service import JobsService

    jobs_service = JobsService()
    jobs = jobs_service.get_all_jobs()
    broadcast_all_jobs([job.to_dict() for job in jobs], room=request.sid)


@socketio.on("unsubscribe_from_jobs", namespace="/jobs")
def handle_unsubscribe_from_jobs():
    """Handle client unsubscription from job updates."""
    leave_room("jobs_updates")
    emit("unsubscribed", {"status": "unsubscribed from job updates"})


@socketio.on("request_jobs_list", namespace="/jobs")
def handle_request_jobs_list():
    """Handle client request for the current jobs list."""
    # Use lazy import to avoid circular dependency
    from ..services.jobs_service import JobsService

    jobs_service = JobsService()
    jobs = jobs_service.get_all_jobs()
    emit("jobs_list", {"jobs": [job.to_dict() for job in jobs]}, room=request.sid)


import logging

logger = logging.getLogger(__name__)


def broadcast_job_update(job_data: Dict[str, Any]):
    """
    Broadcast a job update to all subscribed clients.
    Args:
        job_data: Dictionary containing job information
    """
    try:
        if socketio is None:
            logger.warning("SocketIO not available for job_updated broadcast")
            return
        socketio.emit("job_updated", job_data, room="jobs_updates", namespace="/jobs")
    except Exception as e:
        logger.warning(f"Failed to broadcast job_updated: {e}")
        # Silently fail in worker context where socketio may not be available
        pass


def broadcast_job_created(job_data: Dict[str, Any]):
    """
    Broadcast a new job creation to all subscribed clients.
    Args:
        job_data: Dictionary containing job information
    """
    try:
        if socketio is None:
            logger.warning("SocketIO not available for job_created broadcast")
            return
        socketio.emit("job_created", job_data, room="jobs_updates", namespace="/jobs")
    except Exception as e:
        logger.warning(f"Failed to broadcast job_created: {e}")
        # Silently fail in worker context where socketio may not be available
        pass


def broadcast_job_completed(job_data: Dict[str, Any]):
    """
    Broadcast a job completion to all subscribed clients.

    Args:
        job_data: Dictionary containing job information
    """
    try:
        if socketio is None:
            logger.warning("SocketIO not available for job_completed broadcast")
            return
        socketio.emit("job_completed", job_data, room="jobs_updates", namespace="/jobs")
    except Exception as e:
        logger.warning(f"Failed to broadcast job_completed: {e}")
        # Silently fail in worker context where socketio may not be available
        pass


def broadcast_job_failed(job_data: Dict[str, Any]):
    """
    Broadcast a job failure to all subscribed clients.

    Args:
        job_data: Dictionary containing job information
    """
    try:
        if socketio is None:
            logger.warning("SocketIO not available for job_failed broadcast")
            return
        socketio.emit("job_failed", job_data, room="jobs_updates", namespace="/jobs")
    except Exception as e:
        logger.warning(f"Failed to broadcast job_failed: {e}")
        # Silently fail in worker context where socketio may not be available
        pass


def broadcast_job_cancelled(job_data: Dict[str, Any]):
    """
    Broadcast a job cancellation to all subscribed clients.

    Args:
        job_data: Dictionary containing job information
    """
    try:
        if socketio is None:
            logger.warning("SocketIO not available for job_cancelled broadcast")
            return
        socketio.emit("job_cancelled", job_data, room="jobs_updates", namespace="/jobs")
    except Exception as e:
        logger.warning(f"Failed to broadcast job_cancelled: {e}")
        # Silently fail in worker context where socketio may not be available
        pass


def broadcast_all_jobs(jobs_data: list, room: str = "jobs_updates"):
    """
    Broadcast the current list of all jobs to subscribed clients.

    Args:
        jobs_data: List of job dictionaries
        room: The room to broadcast to (defaults to all subscribers)
    """
    try:
        if socketio is None:
            return
        socketio.emit("jobs_list", {"jobs": jobs_data}, room=room, namespace="/jobs")
    except Exception:
        # Silently fail in worker context where socketio may not be available
        pass


# Subscribe to job events from the event system
def _handle_job_event(event) -> None:
    """Handle job events from the event system and broadcast via WebSocket."""
    try:
        job_data = event.data.get("job_data", {})
        was_created = event.data.get("was_created", False)
        job_id = job_data.get("id", "unknown")
        status = job_data.get("status", "unknown")

        # Only log at debug level for event receipt
        logger.debug(
            f"WebSocket handler received job event: {job_id} - created={was_created} - status={status}"
        )

        if was_created:
            broadcast_job_created(job_data)
        else:
            # Determine the appropriate broadcast based on job status
            if status == "completed":
                broadcast_job_completed(job_data)
            elif status == "failed":
                broadcast_job_failed(job_data)
            elif status == "cancelled":
                broadcast_job_cancelled(job_data)
            else:
                broadcast_job_update(job_data)
    except Exception as e:
        logger.warning(f"Failed to handle job event: {e}")


# Set up event subscription
def _setup_event_subscriptions():
    """Set up event subscriptions for job events."""
    try:
        from ..utils.events import subscribe_to_job_events

        subscribe_to_job_events(_handle_job_event)
        print("✅ Jobs WebSocket event subscriptions initialized")
        import logging

        logging.getLogger(__name__).info(
            "Jobs WebSocket event subscriptions initialized"
        )
    except Exception as e:
        import logging

        print(f"❌ Failed to set up job event subscriptions: {e}")
        logging.getLogger(__name__).warning(
            f"Failed to set up job event subscriptions: {e}"
        )


def initialize_jobs_websocket():
    """
    Initialize the jobs WebSocket handlers and event subscriptions.
    Should be called after Flask app and SocketIO are fully initialized.
    """
    print("🔌 Initializing Jobs WebSocket handlers...")
    _setup_event_subscriptions()


# Initialize event subscriptions when module is imported
_setup_event_subscriptions()
