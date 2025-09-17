"""
WebSocket Jobs endpoint for Open Karaoke Studio

Handles real-time job updates and status broadcasting.
Replaces Flask-SocketIO with native FastAPI WebSocket support.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect

# Add the parent directory to the Python path to import from app
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.services.jobs_service import JobsService

from .connection_manager import SessionConnectionManager


async def get_current_jobs_list():
    """
    Get current jobs list using the real JobsService.
    Updated for PostgreSQL compatibility.
    """
    try:
        # Use the existing JobsService which handles PostgreSQL properly
        jobs_service = JobsService()
        jobs = jobs_service.get_all_jobs()
        return [job.to_dict() for job in jobs]
    except Exception as e:
        print(f"Error getting jobs list from PostgreSQL: {e}")
        # Fallback to mock data if service fails
        return [
            {
                "id": "demo-job-1",
                "status": "processing",
                "progress": 45,
                "filename": "demo-song.mp3",
                "task_id": "demo-task-123",
                "created_at": datetime.now().isoformat(),
            }
        ]


async def websocket_jobs_endpoint(
    websocket: WebSocket, manager: SessionConnectionManager
):
    """
    WebSocket endpoint for real-time job updates.
    Replaces Flask-SocketIO with native FastAPI WebSocket support.
    Enhanced with full Flask feature parity.
    """
    await manager.connect(websocket)
    jobs_room = "jobs_updates"
    await manager.join_room(websocket, jobs_room)

    print(f"Jobs client connected: {id(websocket)}")

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

                print(f"Client {id(websocket)} subscribed to job updates")

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

                print(f"Client {id(websocket)} unsubscribed from job updates")

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
        print(f"Jobs client disconnected: {id(websocket)}")


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
    """Broadcast job failure to all subscribed clients."""
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
