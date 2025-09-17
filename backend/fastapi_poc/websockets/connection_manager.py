"""
WebSocket Connection Manager for Open Karaoke Studio

Handles WebSocket connections, session management, and room-based broadcasting
for the FastAPI WebSocket implementation.
"""

import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import WebSocket


class SessionConnectionManager:
    """Enhanced WebSocket connection manager with session support."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.rooms: Dict[str, List[WebSocket]] = {}
        self.device_sessions: Dict[str, str] = {}  # device_id -> session_id
        self.sessions: Dict[str, Dict] = {}  # session_id -> session_data

    async def connect(self, websocket: WebSocket, device_id: Optional[str] = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if device_id:
            # Store device_id in our mapping instead of on the websocket object
            self.device_sessions[f"ws_{id(websocket)}"] = device_id

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # Remove from all rooms
        for room_connections in self.rooms.values():
            if websocket in room_connections:
                room_connections.remove(websocket)

        # Remove from device sessions if exists
        ws_key = f"ws_{id(websocket)}"
        device_id = None
        for dev_id, session_id in list(self.device_sessions.items()):
            if dev_id == ws_key:
                device_id = session_id
                break

        if device_id:
            # Find the actual device_id in sessions
            for session in self.sessions.values():
                if device_id in session["connected_devices"]:
                    self.leave_session(device_id, session["session_id"])
                    break

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_text(json.dumps(message))

    async def broadcast_to_room(
        self, room: str, message: dict, exclude: Optional[WebSocket] = None
    ):
        if room in self.rooms:
            room_size = len(self.rooms[room])
            print(f"🔊 Broadcasting to room '{room}' with {room_size} clients")
            disconnected = []
            for connection in self.rooms[room]:
                if connection == exclude:
                    print(f"  ⏭️ Skipping sender {id(connection)}")
                    continue  # Skip the excluded connection
                try:
                    await connection.send_text(json.dumps(message))
                    print(f"  ✅ Sent to client {id(connection)}")
                except Exception as e:
                    print(f"  ❌ Failed to send to client {id(connection)}: {e}")
                    # Handle disconnected clients
                    disconnected.append(connection)

            # Clean up disconnected clients
            for conn in disconnected:
                self.rooms[room].remove(conn)
        else:
            print(f"🚫 Room '{room}' not found!")

    async def join_room(self, websocket: WebSocket, room: str):
        if room not in self.rooms:
            self.rooms[room] = []
        if websocket not in self.rooms[room]:
            self.rooms[room].append(websocket)
            print(
                f"🏠 Client {id(websocket)} joined room '{room}' (now {len(self.rooms[room])} clients)"
            )
        else:
            print(f"🔄 Client {id(websocket)} already in room '{room}'")

    async def leave_room(self, websocket: WebSocket, room: str):
        if room in self.rooms and websocket in self.rooms[room]:
            self.rooms[room].remove(websocket)

    def generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return secrets.token_urlsafe(24)

    def generate_display_code(self) -> str:
        """Generate a 4-character display code."""
        # Use uppercase letters and numbers, excluding confusing characters (0, O, 1, I)
        chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
        return "".join(secrets.choice(chars) for _ in range(4))

    def create_session(self, host_device_id: str) -> Dict:
        """Create a new karaoke session."""
        session_id = self.generate_session_id()
        display_code = self.generate_display_code()

        # Ensure display code is unique
        max_attempts = 10
        attempt = 0
        while (
            any(s.get("display_code") == display_code for s in self.sessions.values())
            and attempt < max_attempts
        ):
            display_code = self.generate_display_code()
            attempt += 1

        session_data = {
            "session_id": session_id,
            "display_code": display_code,
            "host_device_id": host_device_id,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24),
            "is_active": True,
            "connected_devices": {},
        }

        self.sessions[session_id] = session_data
        return session_data

    def find_session_by_code(self, display_code: str) -> Optional[Dict]:
        """Find session by display code."""
        for session in self.sessions.values():
            if session.get("display_code") == display_code and session.get("is_active"):
                return session
        return None

    def find_session_by_id(self, session_id: str) -> Optional[Dict]:
        """Find session by ID."""
        return (
            self.sessions.get(session_id)
            if self.sessions.get(session_id, {}).get("is_active")
            else None
        )

    def join_session(self, session_id: str, device_id: str, device_type: str) -> bool:
        """Add device to session."""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        session["connected_devices"][device_id] = {
            "device_id": device_id,
            "device_type": device_type,
            "joined_at": datetime.now(),
            "is_active": True,
        }

        self.device_sessions[device_id] = session_id
        return True

    def leave_session(self, device_id: str, session_id: Optional[str] = None):
        """Remove device from session."""
        if not session_id and device_id in self.device_sessions:
            session_id = self.device_sessions[device_id]

        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            if device_id in session["connected_devices"]:
                session["connected_devices"][device_id]["is_active"] = False

            # If host leaves, mark session inactive
            if device_id == session["host_device_id"]:
                session["is_active"] = False

        if device_id in self.device_sessions:
            del self.device_sessions[device_id]

    def get_session_for_device(self, device_id: str) -> Optional[Dict]:
        """Get session data for a device."""
        if device_id in self.device_sessions:
            session_id = self.device_sessions[device_id]
            return self.sessions.get(session_id)
        return None

    def get_session_room_name(self, session_id: str, room_type: str = "main") -> str:
        """Generate session-specific room names."""
        if room_type == "main":
            return f"session_{session_id}"
        return f"session_{session_id}_{room_type}"
