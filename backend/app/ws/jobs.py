"""
WebSocket Jobs endpoint for Open Karaoke Studio

Handles real-time job updates and status broadcasting.
Replaces Flask-SocketIO with native FastAPI WebSocket support.
"""

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.db.database import get_db_session
from app.db.models import User
from app.services.auth_service import verify_token
from app.services.jobs_service import JobsService
from app.services.session_service import find_session_member

from .connection_manager import SessionConnectionManager

logger = logging.getLogger(__name__)

AUTH_TIMEOUT_SECONDS = 10


def _credentials_valid(message: dict) -> bool:
    """Whether an `authenticate` message proves an account or a session membership.

    The same two credentials REST accepts (require_host_or_session_member): any
    valid account token, or a session id + the device id minted when that device
    joined a live session.
    """
    with get_db_session() as db:
        token = message.get("token")
        if isinstance(token, str) and token:
            payload = verify_token(token)
            user_id = payload.get("sub") if payload else None
            if user_id is not None and db.get(User, int(user_id)) is not None:
                return True

        session_id = message.get("session_id")
        device_id = message.get("device_id")
        if (
            isinstance(session_id, str)
            and session_id
            and isinstance(device_id, str)
            and device_id
        ):
            return find_session_member(db, session_id, device_id) is not None

    return False


async def _authenticate_connection(websocket: WebSocket) -> bool:
    """Read the opening `authenticate` message and check its credentials."""
    try:
        raw = await asyncio.wait_for(
            websocket.receive_text(), timeout=AUTH_TIMEOUT_SECONDS
        )
        message = json.loads(raw)
    except (asyncio.TimeoutError, json.JSONDecodeError):
        return False

    if not isinstance(message, dict) or message.get("type") != "authenticate":
        return False

    return await asyncio.to_thread(_credentials_valid, message)


async def get_current_jobs_list():
    """Get currently in-flight song jobs (pending, downloading, processing).

    Only jobs tied to a song go out. Other job rows (a session's playlist export)
    carry the session's join code in their id and title, and every session's
    members share this feed.
    """
    try:
        jobs_service = JobsService()
        jobs = await asyncio.to_thread(jobs_service.get_in_flight_jobs)
        return [job.to_dict() for job in jobs if job.song_id]
    except Exception as e:
        logger.error("Error getting in-flight jobs list: %s", e)
        return []


async def websocket_jobs_endpoint(
    websocket: WebSocket, manager: SessionConnectionManager
):
    """
    WebSocket endpoint for real-time job updates.

    The first message must be `authenticate`, carrying an account `token` or a
    session member's `session_id` + `device_id`. Until it passes, the socket is
    not in the room and receives nothing; a failure gets `auth_failed` and a
    1008 close.
    """
    await websocket.accept()

    try:
        authenticated = await _authenticate_connection(websocket)
    except WebSocketDisconnect:
        return

    if not authenticated:
        await websocket.send_text(
            json.dumps({"type": "auth_failed", "reason": "not_authenticated"})
        )
        await websocket.close(code=1008, reason="Login or session membership required")
        return

    manager.register(websocket)
    jobs_room = "jobs_updates"
    await manager.join_room(websocket, jobs_room)

    logger.debug("Jobs client connected: %d", id(websocket))

    try:
        # Send connection confirmation
        await websocket.send_text(
            json.dumps({"type": "connected", "status": "connected"})
        )

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")

            if message_type == "subscribe_to_jobs":
                # Client explicitly subscribed to job updates
                await websocket.send_text(
                    json.dumps(
                        {"type": "subscribed", "status": "subscribed to job updates"}
                    )
                )

                # Send current jobs list to the newly subscribed client
                # In real implementation, this would call JobsService
                await websocket.send_text(
                    json.dumps(
                        {"type": "jobs_list", "jobs": await get_current_jobs_list()}
                    )
                )

                logger.debug("Client %d subscribed to job updates", id(websocket))

            elif message_type == "unsubscribe_from_jobs":
                # Client unsubscribed from job updates
                await manager.leave_room(websocket, jobs_room)
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "unsubscribed",
                            "status": "unsubscribed from job updates",
                        }
                    )
                )

                logger.debug("Client %d unsubscribed from job updates", id(websocket))

            elif message_type == "request_jobs_list":
                # Send current jobs list on demand
                await websocket.send_text(
                    json.dumps(
                        {"type": "jobs_list", "jobs": await get_current_jobs_list()}
                    )
                )

            else:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                        }
                    )
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.debug("Jobs client disconnected: %d", id(websocket))


# Job broadcasting functions for Celery integration
async def broadcast_job_update(manager: SessionConnectionManager, job_data: dict):
    """Broadcast job update to all subscribed clients."""
    await manager.broadcast_to_room(
        "jobs_updates", {"type": "job_updated", "job": job_data}
    )


async def broadcast_job_created(manager: SessionConnectionManager, job_data: dict):
    """Broadcast new job creation to all subscribed clients."""
    await manager.broadcast_to_room(
        "jobs_updates", {"type": "job_created", "job": job_data}
    )


async def broadcast_job_completed(manager: SessionConnectionManager, job_data: dict):
    """Broadcast job completion to all subscribed clients."""
    await manager.broadcast_to_room(
        "jobs_updates", {"type": "job_completed", "job": job_data}
    )


async def broadcast_job_failed(manager: SessionConnectionManager, job_data: dict):
    """Broadcast job failure to all subscribed clients.

    NOTE: this has no production callers. Job failures happen inside the
    Celery worker process, which cannot reach this API-process-only
    `manager`. Failure state instead reaches clients via the periodic
    in-flight jobs list (see `get_current_jobs_list`) dropping the job and
    the frontend's `useJobsWebSocket` invalidating the song query.
    """
    await manager.broadcast_to_room(
        "jobs_updates", {"type": "job_failed", "job": job_data}
    )


async def broadcast_job_cancelled(manager: SessionConnectionManager, job_data: dict):
    """Broadcast job cancellation to all subscribed clients."""
    await manager.broadcast_to_room(
        "jobs_updates", {"type": "job_cancelled", "job": job_data}
    )


async def broadcast_all_jobs(manager: SessionConnectionManager, jobs_data: list):
    """Broadcast complete jobs list to all subscribed clients."""
    await manager.broadcast_to_room(
        "jobs_updates", {"type": "jobs_list", "jobs": jobs_data}
    )
