"""
WebSocket Performance Controls endpoint for Open Karaoke Studio

Handles real-time performance controls synchronization including:
- Vocal/instrumental volume controls
- Lyrics controls and playback state
- Multi-device synchronization for karaoke performances
"""

import json

from fastapi import WebSocket, WebSocketDisconnect

from .connection_manager import SessionConnectionManager

# Global performance state for real-time controls
global_performance_state = {
    # Synchronized state - these values are shared across all devices
    "vocal_volume": 0,
    "instrumental_volume": 1,
    "lyrics_size": "medium",
    "lyrics_offset": 0,
    # Playback state - ALSO synchronized (contrary to my earlier comment)
    "current_time": 0,
    "duration": 0,
    "is_playing": False,
    "current_song_id": None,
    "is_ready": False,
}


async def websocket_performance_endpoint(
    websocket: WebSocket, manager: SessionConnectionManager
):
    """
    WebSocket endpoint for real-time performance controls synchronization.
    Handles vocal/instrumental volume, lyrics controls, and playback state.
    Based on the Flask-SocketIO performance_controls_ws.py implementation.
    """
    await manager.connect(websocket)
    performance_room = "global_performance_controls"
    await manager.join_room(websocket, performance_room)

    print(f"Performance controls client connected: {id(websocket)}")

    try:
        # Send current performance state to new connection
        await websocket.send_text(
            json.dumps({"type": "performance_state", "state": global_performance_state})
        )

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")

            if message_type == "join_performance":
                # Client explicitly joined performance controls
                await websocket.send_text(
                    json.dumps(
                        {"type": "performance_state", "state": global_performance_state}
                    )
                )
                print(f"Client {id(websocket)} joined performance controls")

            elif message_type == "update_performance_control":
                # Update a specific control (vocal_volume, instrumental_volume, etc.)
                control_name = message.get("control")
                value = message.get("value")

                if not control_name or value is None:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "message": "Invalid control update request",
                            }
                        )
                    )
                    continue

                if control_name not in global_performance_state:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "message": f"Unsupported control: {control_name}",
                            }
                        )
                    )
                    continue

                # Update global state
                global_performance_state[control_name] = value
                print(f"🎛️ Updated {control_name}={value} for performance controls")
                print(f"🌍 Global state: {global_performance_state}")

                # Broadcast to all clients except sender
                await manager.broadcast_to_room(
                    performance_room,
                    {
                        "type": "control_updated",
                        "control": control_name,
                        "value": value,
                    },
                    exclude=websocket,
                )

            elif message_type == "update_player_state":
                # Update player state - this IS synchronized across all devices
                is_playing = message.get("isPlaying")
                current_time = message.get("currentTime")
                duration = message.get("duration")

                if is_playing is not None:
                    global_performance_state["is_playing"] = is_playing
                if current_time is not None:
                    global_performance_state["current_time"] = current_time
                if duration is not None:
                    global_performance_state["duration"] = duration

                # Send updated state back to sender only (like Flask version)
                await websocket.send_text(
                    json.dumps(
                        {"type": "performance_state", "state": global_performance_state}
                    )
                )

                print(
                    f"Updated player state: is_playing={is_playing}, currentTime={current_time}, duration={duration}"
                )

            elif message_type == "reset_player_state":
                # Reset player state AND broadcast event (like Flask version)
                global_performance_state["current_time"] = 0
                global_performance_state["is_playing"] = False

                # Broadcast reset event to all clients except sender
                await manager.broadcast_to_room(
                    performance_room, {"type": "reset_player_state"}, exclude=websocket
                )

                print(f"Reset player state from client {id(websocket)}")

            elif message_type == "playback_play":
                # Play command: Update state AND broadcast event (matching Flask exactly)
                global_performance_state["is_playing"] = True

                # Broadcast play command to all clients including sender
                await manager.broadcast_to_room(
                    performance_room, {"type": "playback_play"}
                )

                # Also broadcast updated state to all clients including sender
                await manager.broadcast_to_room(
                    performance_room,
                    {"type": "performance_state", "state": global_performance_state},
                )

                print(f"Play command from client {id(websocket)}")

            elif message_type == "playback_pause":
                # Pause command: Update state AND broadcast event (matching Flask exactly)
                global_performance_state["is_playing"] = False

                # Broadcast pause command to all clients including sender
                await manager.broadcast_to_room(
                    performance_room, {"type": "playback_pause"}
                )

                # Also broadcast updated state to all clients including sender
                await manager.broadcast_to_room(
                    performance_room,
                    {"type": "performance_state", "state": global_performance_state},
                )

                print(f"Pause command from client {id(websocket)}")

            elif message_type == "seek_to":
                # Seek command: Update current_time state AND broadcast event
                seek_time = message.get("time", 0)
                global_performance_state["current_time"] = seek_time

                await manager.broadcast_to_room(
                    performance_room, {"type": "seek_to", "time": seek_time}
                )

                # Also broadcast updated state
                await manager.broadcast_to_room(
                    performance_room,
                    {"type": "performance_state", "state": global_performance_state},
                )

                print(f"Seek command to {seek_time}s from client {id(websocket)}")

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
        print(f"Performance controls client disconnected: {id(websocket)}")


def get_performance_state():
    """Get current performance state for external access."""
    return global_performance_state.copy()


def update_performance_state(updates: dict):
    """Update performance state from external sources."""
    global global_performance_state
    for key, value in updates.items():
        if key in global_performance_state:
            global_performance_state[key] = value
