"""
Session-based WebSocket handlers for Open Karaoke Studio.

This module provides session management functionality including:
- Session creation and joining
- Device management within sessions
- Session-specific room management
"""

import logging
from typing import Dict, List, Optional

from flask import request
from flask_socketio import emit, join_room, leave_room, rooms
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from ..db.database import SessionLocal
from ..db.models import KaraokeSession, SessionDevice
from .socketio import socketio

logger = logging.getLogger(__name__)

# In-memory session state for active sessions
active_sessions: Dict[str, Dict] = {}


def get_session_room_name(session_id: str, room_type: str = "main") -> str:
    """Generate session-specific room names."""
    if room_type == "main":
        return f"session_{session_id}"
    return f"session_{session_id}_{room_type}"


def register_session_handlers(socketio_instance):
    """Register session management WebSocket event handlers."""

    @socketio_instance.on("create_session")
    def handle_create_session(data=None):
        """Create a new karaoke session."""
        try:
            db = SessionLocal()
            
            # Try to create a unique session
            max_attempts = 10
            for attempt in range(max_attempts):
                try:
                    session = KaraokeSession.create_new_session(
                        host_device_id=request.sid
                    )
                    db.add(session)
                    db.commit()
                    
                    # Add session to active sessions
                    active_sessions[session.session_id] = {
                        "session_id": session.session_id,
                        "display_code": session.display_code,
                        "host_device_id": session.host_device_id,
                        "created_at": session.created_at.isoformat(),
                        "expires_at": session.expires_at.isoformat(),
                        "is_active": session.is_active,
                        "connected_devices": [],
                    }
                    
                    # Join the host to the session room
                    session_room = get_session_room_name(session.session_id)
                    join_room(session_room)
                    
                    # Create host device record
                    host_device = SessionDevice(
                        session_id=session.session_id,
                        device_id=request.sid,
                        device_type="stage",
                        user_agent=request.headers.get("User-Agent"),
                    )
                    db.add(host_device)
                    db.commit()
                    
                    # Update active sessions with host device
                    active_sessions[session.session_id]["connected_devices"].append({
                        "device_id": request.sid,
                        "device_type": "stage",
                        "joined_at": host_device.joined_at.isoformat(),
                        "is_active": True,
                    })
                    
                    logger.info(
                        "Created session %s with code %s for host %s",
                        session.session_id,
                        session.display_code,
                        request.sid,
                    )
                    
                    emit("session_created", {
                        "session_id": session.session_id,
                        "display_code": session.display_code,
                        "is_host": True,
                        "device_count": 1,
                        "expires_at": session.expires_at.isoformat(),
                    })
                    
                    db.close()
                    return
                    
                except IntegrityError:
                    db.rollback()
                    if attempt == max_attempts - 1:
                        raise
                    continue
                    
        except Exception as e:
            logger.error("Failed to create session: %s", str(e))
            emit("session_error", {"error": "Failed to create session"})
        finally:
            if 'db' in locals():
                db.close()

    @socketio_instance.on("join_session_by_code")
    def handle_join_session_by_code(data):
        """Join a session using a 4-character display code."""
        try:
            display_code = data.get("display_code", "").upper().strip()
            device_type = data.get("device_type", "performer")
            
            if not display_code or len(display_code) != 4:
                emit("session_error", {"error": "Invalid display code"})
                return
                
            if device_type not in SessionDevice.DEVICE_TYPES:
                emit("session_error", {"error": "Invalid device type"})
                return
            
            db = SessionLocal()
            
            # Find session by display code
            session = (
                db.query(KaraokeSession)
                .filter(
                    KaraokeSession.display_code == display_code,
                    KaraokeSession.is_active == True,
                )
                .first()
            )
            
            if not session:
                emit("session_error", {"error": "Session not found or expired"})
                db.close()
                return
                
            if session.is_expired():
                emit("session_error", {"error": "Session has expired"})
                db.close()
                return
            
            # Check if device is already in session
            existing_device = (
                db.query(SessionDevice)
                .filter(
                    SessionDevice.session_id == session.session_id,
                    SessionDevice.device_id == request.sid,
                    SessionDevice.is_active == True,
                )
                .first()
            )
            
            if existing_device:
                emit("session_error", {"error": "Already joined this session"})
                db.close()
                return
            
            # Join the session room
            session_room = get_session_room_name(session.session_id)
            join_room(session_room)
            
            # Create device record
            device = SessionDevice(
                session_id=session.session_id,
                device_id=request.sid,
                device_type=device_type,
                user_agent=request.headers.get("User-Agent"),
            )
            db.add(device)
            db.commit()
            
            # Update active sessions
            if session.session_id not in active_sessions:
                active_sessions[session.session_id] = {
                    "session_id": session.session_id,
                    "display_code": session.display_code,
                    "host_device_id": session.host_device_id,
                    "created_at": session.created_at.isoformat(),
                    "expires_at": session.expires_at.isoformat(),
                    "is_active": session.is_active,
                    "connected_devices": [],
                }
            
            active_sessions[session.session_id]["connected_devices"].append({
                "device_id": request.sid,
                "device_type": device_type,
                "joined_at": device.joined_at.isoformat(),
                "is_active": True,
            })
            
            device_count = len(active_sessions[session.session_id]["connected_devices"])
            
            logger.info(
                "Device %s joined session %s as %s",
                request.sid,
                session.session_id,
                device_type,
            )
            
            # Notify the joining device
            emit("session_joined", {
                "session_id": session.session_id,
                "display_code": session.display_code,
                "is_host": request.sid == session.host_device_id,
                "device_type": device_type,
                "device_count": device_count,
                "expires_at": session.expires_at.isoformat(),
            })
            
            # Notify other devices in the session about the new device
            emit("device_joined", {
                "device_id": request.sid,
                "device_type": device_type,
                "device_count": device_count,
            }, room=session_room, include_self=False)
            
            db.close()
            
        except Exception as e:
            logger.error("Failed to join session: %s", str(e))
            emit("session_error", {"error": "Failed to join session"})
            if 'db' in locals():
                db.close()

    @socketio_instance.on("join_session_by_id")
    def handle_join_session_by_id(data):
        """Join a session using the session ID (for deep links)."""
        try:
            session_id = data.get("session_id", "").strip()
            device_type = data.get("device_type", "performer")
            
            if not session_id:
                emit("session_error", {"error": "Session ID required"})
                return
                
            if device_type not in SessionDevice.DEVICE_TYPES:
                emit("session_error", {"error": "Invalid device type"})
                return
            
            db = SessionLocal()
            
            # Find session by ID
            session = (
                db.query(KaraokeSession)
                .filter(
                    KaraokeSession.session_id == session_id,
                    KaraokeSession.is_active == True,
                )
                .first()
            )
            
            if not session:
                emit("session_error", {"error": "Session not found"})
                db.close()
                return
                
            if session.is_expired():
                emit("session_error", {"error": "Session has expired"})
                db.close()
                return
            
            # Use the same logic as join_by_code
            # This is essentially the same process, just found by ID instead of code
            handle_join_session_by_code({
                "display_code": session.display_code,
                "device_type": device_type,
            })
            
        except Exception as e:
            logger.error("Failed to join session by ID: %s", str(e))
            emit("session_error", {"error": "Failed to join session"})
            if 'db' in locals():
                db.close()

    @socketio_instance.on("leave_session")
    def handle_leave_session(data=None):
        """Leave the current session."""
        try:
            db = SessionLocal()
            
            # Find the device's session
            device = (
                db.query(SessionDevice)
                .options(joinedload(SessionDevice.session))
                .filter(
                    SessionDevice.device_id == request.sid,
                    SessionDevice.is_active == True,
                )
                .first()
            )
            
            if not device:
                emit("session_error", {"error": "Not in any session"})
                db.close()
                return
            
            session = device.session
            session_room = get_session_room_name(session.session_id)
            
            # Mark device as inactive
            device.is_active = False
            db.commit()
            
            # Leave the session room
            leave_room(session_room)
            
            # Update active sessions
            if session.session_id in active_sessions:
                active_sessions[session.session_id]["connected_devices"] = [
                    d for d in active_sessions[session.session_id]["connected_devices"]
                    if d["device_id"] != request.sid
                ]
                
                device_count = len(active_sessions[session.session_id]["connected_devices"])
                
                # Notify other devices about device leaving
                emit("device_left", {
                    "device_id": request.sid,
                    "device_type": device.device_type,
                    "device_count": device_count,
                }, room=session_room)
                
                # If host is leaving, mark session as inactive
                if request.sid == session.host_device_id:
                    session.is_active = False
                    db.commit()
                    active_sessions[session.session_id]["is_active"] = False
                    
                    # Notify all remaining devices that session is ending
                    emit("session_ended", {
                        "reason": "Host disconnected"
                    }, room=session_room)
                    
                    logger.info("Session %s ended - host disconnected", session.session_id)
                
                # Clean up empty sessions
                if device_count == 0:
                    del active_sessions[session.session_id]
            
            logger.info(
                "Device %s left session %s",
                request.sid,
                session.session_id,
            )
            
            emit("session_left", {"session_id": session.session_id})
            db.close()
            
        except Exception as e:
            logger.error("Failed to leave session: %s", str(e))
            emit("session_error", {"error": "Failed to leave session"})
            if 'db' in locals():
                db.close()

    @socketio_instance.on("get_session_info")
    def handle_get_session_info(data=None):
        """Get information about the current session."""
        try:
            db = SessionLocal()
            
            # Find the device's session
            device = (
                db.query(SessionDevice)
                .options(joinedload(SessionDevice.session))
                .filter(
                    SessionDevice.device_id == request.sid,
                    SessionDevice.is_active == True,
                )
                .first()
            )
            
            if not device:
                emit("session_info", {"in_session": False})
                db.close()
                return
            
            session = device.session
            
            # Get all active devices in the session
            active_devices = (
                db.query(SessionDevice)
                .filter(
                    SessionDevice.session_id == session.session_id,
                    SessionDevice.is_active == True,
                )
                .all()
            )
            
            connected_devices = [
                {
                    "device_id": d.device_id,
                    "device_type": d.device_type,
                    "joined_at": d.joined_at.isoformat(),
                    "is_self": d.device_id == request.sid,
                }
                for d in active_devices
            ]
            
            emit("session_info", {
                "in_session": True,
                "session_id": session.session_id,
                "display_code": session.display_code,
                "is_host": request.sid == session.host_device_id,
                "device_type": device.device_type,
                "device_count": len(connected_devices),
                "connected_devices": connected_devices,
                "created_at": session.created_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "is_active": session.is_active,
            })
            
            db.close()
            
        except Exception as e:
            logger.error("Failed to get session info: %s", str(e))
            emit("session_error", {"error": "Failed to get session info"})
            if 'db' in locals():
                db.close()

    @socketio_instance.on("list_connected_devices")
    def handle_list_connected_devices(data=None):
        """List all devices connected to the current session."""
        try:
            db = SessionLocal()
            
            # Find the device's session
            device = (
                db.query(SessionDevice)
                .filter(
                    SessionDevice.device_id == request.sid,
                    SessionDevice.is_active == True,
                )
                .first()
            )
            
            if not device:
                emit("session_error", {"error": "Not in any session"})
                db.close()
                return
            
            # Get all active devices in the session
            active_devices = (
                db.query(SessionDevice)
                .filter(
                    SessionDevice.session_id == device.session_id,
                    SessionDevice.is_active == True,
                )
                .all()
            )
            
            connected_devices = [
                {
                    "device_id": d.device_id,
                    "device_type": d.device_type,
                    "joined_at": d.joined_at.isoformat(),
                    "is_self": d.device_id == request.sid,
                    "user_agent": d.user_agent,
                }
                for d in active_devices
            ]
            
            emit("connected_devices", {
                "devices": connected_devices,
                "device_count": len(connected_devices),
            })
            
            db.close()
            
        except Exception as e:
            logger.error("Failed to list connected devices: %s", str(e))
            emit("session_error", {"error": "Failed to list devices"})
            if 'db' in locals():
                db.close()

    @socketio_instance.on("disconnect")
    def handle_disconnect():
        """Handle device disconnection."""
        try:
            db = SessionLocal()
            
            # Find any active sessions for this device
            device = (
                db.query(SessionDevice)
                .options(joinedload(SessionDevice.session))
                .filter(
                    SessionDevice.device_id == request.sid,
                    SessionDevice.is_active == True,
                )
                .first()
            )
            
            if device:
                # Mark device as inactive but don't completely remove
                # This allows for reconnection
                device.is_active = False
                db.commit()
                
                session = device.session
                
                # Update active sessions
                if session.session_id in active_sessions:
                    active_sessions[session.session_id]["connected_devices"] = [
                        d for d in active_sessions[session.session_id]["connected_devices"]
                        if d["device_id"] != request.sid
                    ]
                    
                    device_count = len(active_sessions[session.session_id]["connected_devices"])
                    session_room = get_session_room_name(session.session_id)
                    
                    # Notify other devices about disconnection
                    emit("device_disconnected", {
                        "device_id": request.sid,
                        "device_type": device.device_type,
                        "device_count": device_count,
                    }, room=session_room)
                    
                    # If host disconnected, end the session
                    if request.sid == session.host_device_id:
                        session.is_active = False
                        db.commit()
                        active_sessions[session.session_id]["is_active"] = False
                        
                        emit("session_ended", {
                            "reason": "Host disconnected"
                        }, room=session_room)
                        
                        logger.info("Session %s ended - host disconnected", session.session_id)
                
                logger.info(
                    "Device %s disconnected from session %s",
                    request.sid,
                    session.session_id,
                )
            
            db.close()
            
        except Exception as e:
            logger.error("Error handling disconnect: %s", str(e))
            if 'db' in locals():
                db.close()

    logger.info("Session WebSocket event handlers registered")


def get_device_session_id(device_id: str) -> Optional[str]:
    """Get the session ID for a specific device."""
    for session_id, session_data in active_sessions.items():
        for device in session_data["connected_devices"]:
            if device["device_id"] == device_id and device["is_active"]:
                return session_id
    return None


def emit_to_session(session_id: str, event: str, data: dict, include_host: bool = True):
    """Emit an event to all devices in a session."""
    session_room = get_session_room_name(session_id)
    socketio.emit(event, data, room=session_room)


def emit_to_session_room(session_id: str, room_type: str, event: str, data: dict):
    """Emit an event to a specific session room (e.g., controls, queue)."""
    room_name = get_session_room_name(session_id, room_type)
    socketio.emit(event, data, room=room_name)