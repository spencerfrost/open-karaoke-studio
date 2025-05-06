"""
WebSocket event handlers for real-time performance controls in Open Karaoke Studio.
This module provides functionality for synchronized control across multiple devices
for performance controls (vocal/instrumental volume, lyrics size, etc).
"""

from flask import request
from flask_socketio import emit, join_room, leave_room
import logging

logger = logging.getLogger(__name__)

# Global room name for performance controls
GLOBAL_CONTROLS_ROOM = "global_performance_controls"

# Global state for performance controls
global_performance_state = {
    "vocal_volume": 50,
    "instrumental_volume": 100,
    "lyrics_size": "medium",
}


def register_handlers(socketio):
    """Register WebSocket event handlers for performance controls."""

    @socketio.on("connect")
    def handle_connect():
        logger.info(f"Client connected: {request.sid}")

    @socketio.on("disconnect")
    def handle_disconnect():
        logger.info(f"Client disconnected: {request.sid}")

    @socketio.on("join_performance")
    def handle_join_performance(data=None):
        join_room(GLOBAL_CONTROLS_ROOM)
        logger.info(f"Client {request.sid} joined global performance controls")
        emit("performance_state", global_performance_state, room=request.sid)

    @socketio.on("leave_performance")
    def handle_leave_performance(data=None):
        leave_room(GLOBAL_CONTROLS_ROOM)
        logger.info(f"Client {request.sid} left global performance controls")

    @socketio.on("update_performance_control")
    def handle_update_control(data):
        control_name = data.get("control")
        value = data.get("value")
        if not all([control_name, value is not None]):
            logger.error(f"Invalid control update request: {data}")
            return
        global_performance_state[control_name] = value
        emit(
            "control_updated",
            {"control": control_name, "value": value},
            room=GLOBAL_CONTROLS_ROOM,
            include_self=False,
        )
        logger.info(f"Updated {control_name}={value} for global performance controls")

    logger.info("Performance controls WebSocket event handlers registered")
