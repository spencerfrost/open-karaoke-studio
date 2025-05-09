"""
WebSocket event handlers for real-time performance controls in Open Karaoke Studio.
This module provides functionality for synchronized control across multiple devices
for performance controls (vocal/instrumental volume, lyrics size, play/pause).
"""

import logging
from flask import request
from flask_socketio import emit, join_room, leave_room

logger = logging.getLogger(__name__)

GLOBAL_CONTROLS_ROOM = "global_performance_controls"

global_performance_state = {
    "vocal_volume": 0,
    "instrumental_volume": 1,
    "lyrics_size": "medium",
    "current_time": 0,
    "duration": 0,
    "isPlaying": False,
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
        if control_name not in global_performance_state:
            logger.warning(f"Ignored update for unsupported control: {control_name}")
            return
        global_performance_state[control_name] = value
        emit(
            "control_updated",
            {"control": control_name, "value": value},
            room=GLOBAL_CONTROLS_ROOM,
            include_self=False,
        )
        logger.info(f"Updated {control_name}={value} for global performance controls")

    @socketio.on("update_player_state")
    def handle_player_state_update(data):
        logger.info(f"Received player state update from {request.sid}: {data}")
        isPlaying = data.get("isPlaying")
        currentTime = data.get("currentTime")
        duration = data.get("duration")

        if isPlaying is not None:
            global_performance_state["isPlaying"] = isPlaying
        if currentTime is not None:
            global_performance_state["current_time"] = currentTime
        if duration is not None:
            global_performance_state["duration"] = duration
        emit("performance_state", global_performance_state, room=request.sid)

        logger.info(f"Updated player state: {global_performance_state}")

    @socketio.on("reset_player_state")
    def handle_reset_player_state(data=None):
        logger.info(f"Received 'reset_player_state' command from {request.sid}")
        global_performance_state["current_time"] = 0
        global_performance_state["isPlaying"] = False
        emit("reset_player_state", {}, room=GLOBAL_CONTROLS_ROOM, include_self=False)

    @socketio.on("toggle_playback")
    def handle_toggle_playback(data=None):
        logger.info(f"Received 'toggle_playback' command from {request.sid}")
        global_performance_state["isPlaying"] = not global_performance_state[
            "isPlaying"
        ]
        emit("toggle_playback", {}, room=GLOBAL_CONTROLS_ROOM, include_self=False)

    @socketio.on("playback_pause")
    def handle_playback_pause(data=None):
        logger.info(f"Received 'pause' command from {request.sid}")
        global_performance_state["isPlaying"] = False
        emit("playback_pause", {}, room=GLOBAL_CONTROLS_ROOM, include_self=False)

    logger.info("Performance controls WebSocket event handlers registered")
