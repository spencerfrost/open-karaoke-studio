"""
WebSocket Session Management endpoint for Open Karaoke Studio

Handles session creation, joining, leaving, and real-time session updates.
Manages karaoke sessions with display codes and multi-device synchronization.
"""

import json
import secrets

from fastapi import WebSocket, WebSocketDisconnect

from .connection_manager import SessionConnectionManager


async def websocket_session_endpoint(
    websocket: WebSocket, manager: SessionConnectionManager
):
    """
    Session management WebSocket endpoint.
    Handles session creation, joining, leaving, and real-time session updates.
    """
    device_id = f"device_{secrets.token_urlsafe(8)}"
    await manager.connect(websocket, device_id)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")

            if message_type == "create_session":
                # Create new session
                session_data = manager.create_session(device_id)

                # Join the session room
                session_room = manager.get_session_room_name(session_data["session_id"])
                await manager.join_room(websocket, session_room)

                # Add host to session
                manager.join_session(session_data["session_id"], device_id, "stage")

                await manager.send_personal_message(
                    {
                        "type": "session_created",
                        "session_id": session_data["session_id"],
                        "display_code": session_data["display_code"],
                        "is_host": True,
                        "device_count": 1,
                        "expires_at": session_data["expires_at"].isoformat(),
                    },
                    websocket,
                )

            elif message_type == "join_session_by_code":
                display_code = message.get("display_code", "").upper().strip()
                device_type = message.get("device_type", "performer")

                if not display_code or len(display_code) != 4:
                    await manager.send_personal_message(
                        {"type": "session_error", "error": "Invalid display code"},
                        websocket,
                    )
                    continue

                session = manager.find_session_by_code(display_code)
                if not session:
                    await manager.send_personal_message(
                        {"type": "session_error", "error": "Session not found"},
                        websocket,
                    )
                    continue

                # Join the session
                session_room = manager.get_session_room_name(session["session_id"])
                await manager.join_room(websocket, session_room)

                manager.join_session(session["session_id"], device_id, device_type)

                device_count = len(
                    [d for d in session["connected_devices"].values() if d["is_active"]]
                )

                await manager.send_personal_message(
                    {
                        "type": "session_joined",
                        "session_id": session["session_id"],
                        "display_code": session["display_code"],
                        "is_host": device_id == session["host_device_id"],
                        "device_type": device_type,
                        "device_count": device_count,
                        "expires_at": session["expires_at"].isoformat(),
                    },
                    websocket,
                )

                # Notify other devices about new member
                await manager.broadcast_to_room(
                    session_room,
                    {
                        "type": "device_joined",
                        "device_id": device_id,
                        "device_type": device_type,
                        "device_count": device_count,
                    },
                )

            elif message_type == "join_session_by_id":
                session_id = message.get("session_id", "").strip()
                device_type = message.get("device_type", "performer")

                session = manager.find_session_by_id(session_id)
                if not session:
                    await manager.send_personal_message(
                        {"type": "session_error", "error": "Session not found"},
                        websocket,
                    )
                    continue

                # Same logic as join by code
                session_room = manager.get_session_room_name(session["session_id"])
                await manager.join_room(websocket, session_room)

                manager.join_session(session["session_id"], device_id, device_type)

                device_count = len(
                    [d for d in session["connected_devices"].values() if d["is_active"]]
                )

                await manager.send_personal_message(
                    {
                        "type": "session_joined",
                        "session_id": session["session_id"],
                        "display_code": session["display_code"],
                        "is_host": device_id == session["host_device_id"],
                        "device_type": device_type,
                        "device_count": device_count,
                        "expires_at": session["expires_at"].isoformat(),
                    },
                    websocket,
                )

                await manager.broadcast_to_room(
                    session_room,
                    {
                        "type": "device_joined",
                        "device_id": device_id,
                        "device_type": device_type,
                        "device_count": device_count,
                    },
                )

            elif message_type == "leave_session":
                session = manager.get_session_for_device(device_id)
                if session:
                    session_room = manager.get_session_room_name(session["session_id"])

                    manager.leave_session(device_id, session["session_id"])
                    await manager.leave_room(websocket, session_room)

                    device_count = len(
                        [
                            d
                            for d in session["connected_devices"].values()
                            if d["is_active"]
                        ]
                    )

                    await manager.send_personal_message(
                        {"type": "session_left", "session_id": session["session_id"]},
                        websocket,
                    )

                    # If host left, end session
                    if device_id == session["host_device_id"]:
                        await manager.broadcast_to_room(
                            session_room,
                            {"type": "session_ended", "reason": "Host disconnected"},
                        )
                    else:
                        await manager.broadcast_to_room(
                            session_room,
                            {
                                "type": "device_left",
                                "device_id": device_id,
                                "device_count": device_count,
                            },
                        )

            elif message_type == "get_session_info":
                session = manager.get_session_for_device(device_id)
                if session:
                    connected_devices = [
                        {
                            "device_id": d["device_id"],
                            "device_type": d["device_type"],
                            "joined_at": d["joined_at"].isoformat(),
                            "is_self": d["device_id"] == device_id,
                        }
                        for d in session["connected_devices"].values()
                        if d["is_active"]
                    ]

                    await manager.send_personal_message(
                        {
                            "type": "session_info",
                            "in_session": True,
                            "session_id": session["session_id"],
                            "display_code": session["display_code"],
                            "is_host": device_id == session["host_device_id"],
                            "device_count": len(connected_devices),
                            "connected_devices": connected_devices,
                            "created_at": session["created_at"].isoformat(),
                            "expires_at": session["expires_at"].isoformat(),
                            "is_active": session["is_active"],
                        },
                        websocket,
                    )
                else:
                    await manager.send_personal_message(
                        {"type": "session_info", "in_session": False}, websocket
                    )

    except WebSocketDisconnect:
        # Handle disconnection
        session = manager.get_session_for_device(device_id)
        if session:
            session_room = manager.get_session_room_name(session["session_id"])
            manager.leave_session(device_id, session["session_id"])

            # Notify remaining devices
            if device_id == session["host_device_id"]:
                await manager.broadcast_to_room(
                    session_room,
                    {"type": "session_ended", "reason": "Host disconnected"},
                )
            else:
                device_count = len(
                    [d for d in session["connected_devices"].values() if d["is_active"]]
                )
                await manager.broadcast_to_room(
                    session_room,
                    {
                        "type": "device_disconnected",
                        "device_id": device_id,
                        "device_count": device_count,
                    },
                )

        manager.disconnect(websocket)
        print(f"Device {device_id} disconnected from session WebSocket")
