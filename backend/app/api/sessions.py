"""
Sessions API endpoints for Open Karaoke Studio.

This module provides REST API endpoints for session management:
- Creating new sessions
- Joining sessions by code or ID
- Getting session information
- Leaving sessions
"""

import logging

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from ..db.database import SessionLocal
from ..db.models import KaraokeSession, SessionDevice

logger = logging.getLogger(__name__)

sessions_bp = Blueprint("sessions", __name__, url_prefix="/api/sessions")


@sessions_bp.route("", methods=["POST"])
def create_session():
    """Create a new karaoke session."""
    try:
        data = request.get_json() or {}
        device_type = data.get("device_type", "stage")
        display_name = data.get("display_name")  # Optional display name for host

        if device_type not in SessionDevice.DEVICE_TYPES:
            return jsonify({"error": "Invalid device type"}), 400

        # Generate a unique device ID for REST API clients
        # This will be different from WebSocket device IDs (request.sid)
        import uuid
        device_id = f"rest_{uuid.uuid4().hex[:12]}"

        db = SessionLocal()

        # Try to create a unique session
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                session = KaraokeSession.create_new_session(
                    db, host_device_id=device_id
                )
                db.add(session)
                db.commit()

                # Create host device record
                host_device = SessionDevice(
                    session_id=session.session_id,
                    device_id=device_id,
                    device_type=device_type,
                    user_agent=request.headers.get("User-Agent"),
                    display_name=display_name,  # Store the host's display name
                )
                db.add(host_device)
                db.commit()

                logger.info(
                    "Created session %s with code %s for host %s",
                    session.session_id,
                    session.display_code,
                    device_id,
                )

                result = {
                    "session_id": session.session_id,
                    "display_code": session.display_code,
                    "device_id": device_id,  # Return device ID for client to use
                    "is_host": True,
                    "device_type": device_type,
                    "device_count": 1,
                    "connected_devices": [{
                        "device_id": host_device.device_id,
                        "device_type": host_device.device_type,
                        "joined_at": host_device.joined_at.isoformat(),
                        "is_self": True,
                        "display_name": host_device.display_name,  # Include display name
                    }],
                    "created_at": session.created_at.isoformat(),
                    "expires_at": session.expires_at.isoformat(),
                    "is_active": session.is_active,
                }

                db.close()
                return jsonify(result), 201

            except IntegrityError:
                db.rollback()
                if attempt == max_attempts - 1:
                    raise
                continue

        db.close()
        return jsonify({"error": "Failed to create unique session"}), 500

    except Exception as e:
        logger.error("Failed to create session: %s", str(e))
        if 'db' in locals():
            db.close()
        return jsonify({"error": "Failed to create session"}), 500


@sessions_bp.route("/join-by-code", methods=["POST"])
def join_session_by_code():
    """Join a session using a 4-character display code."""
    try:
        data = request.get_json() or {}
        display_code = data.get("code", "").upper().strip()
        device_type = data.get("device_type", "performer")
        display_name = data.get("display_name")  # New parameter for user's name

        if not display_code or len(display_code) != 4:
            return jsonify({"error": "Invalid display code"}), 400

        if device_type not in SessionDevice.DEVICE_TYPES:
            return jsonify({"error": "Invalid device type"}), 400

        # Generate a unique device ID for REST API clients
        import uuid
        device_id = f"rest_{uuid.uuid4().hex[:12]}"

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
            db.close()
            return jsonify({"error": "Session not found or expired"}), 404

        if session.is_expired():
            db.close()
            return jsonify({"error": "Session has expired"}), 410

        # Create device record
        device = SessionDevice(
            session_id=session.session_id,
            device_id=device_id,
            device_type=device_type,
            user_agent=request.headers.get("User-Agent"),
            display_name=display_name,  # Store the user's display name
        )
        db.add(device)
        db.commit()

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
                "is_self": d.device_id == device_id,
                "display_name": d.display_name,  # Include display name in response
            }
            for d in active_devices
        ]

        logger.info(
            "Device %s joined session %s as %s",
            device_id,
            session.session_id,
            device_type,
        )

        result = {
            "session_id": session.session_id,
            "display_code": session.display_code,
            "device_id": device_id,  # Return device ID for client to use
            "is_host": device_id == session.host_device_id,
            "device_type": device_type,
            "device_count": len(connected_devices),
            "connected_devices": connected_devices,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "is_active": session.is_active,
        }

        db.close()
        return jsonify(result), 200

    except Exception as e:
        logger.error("Failed to join session: %s", str(e))
        if 'db' in locals():
            db.close()
        return jsonify({"error": "Failed to join session"}), 500


@sessions_bp.route("/join-by-id", methods=["POST"])
def join_session_by_id():
    """Join a session using the session ID."""
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id", "").strip()
        device_type = data.get("device_type", "performer")
        display_name = data.get("display_name")  # New parameter for user's name

        if not session_id:
            return jsonify({"error": "Session ID required"}), 400

        if device_type not in SessionDevice.DEVICE_TYPES:
            return jsonify({"error": "Invalid device type"}), 400

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
            db.close()
            return jsonify({"error": "Session not found"}), 404

        if session.is_expired():
            db.close()
            return jsonify({"error": "Session has expired"}), 410

        # Check if device is already in session
        existing_device = (
            db.query(SessionDevice)
            .filter(
                SessionDevice.session_id == session.session_id,
                SessionDevice.device_id == (request.remote_addr or "unknown"),
                SessionDevice.is_active == True,
            )
            .first()
        )

        if existing_device:
            db.close()
            return jsonify({"error": "Already joined this session"}), 409

        # Create device record
        device = SessionDevice(
            session_id=session.session_id,
            device_id=request.remote_addr or "unknown",
            device_type=device_type,
            user_agent=request.headers.get("User-Agent"),
            display_name=display_name,  # Store the user's display name
        )
        db.add(device)
        db.commit()

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
                "is_self": d.device_id == (request.remote_addr or "unknown"),
                "display_name": d.display_name,  # Include display name in response
            }
            for d in active_devices
        ]

        logger.info(
            "Device %s joined session %s as %s",
            request.remote_addr,
            session.session_id,
            device_type,
        )

        result = {
            "session_id": session.session_id,
            "display_code": session.display_code,
            "is_host": (request.remote_addr or "unknown") == session.host_device_id,
            "device_type": device_type,
            "device_count": len(connected_devices),
            "connected_devices": connected_devices,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "is_active": session.is_active,
        }

        db.close()
        return jsonify(result), 200

    except Exception as e:
        logger.error("Failed to join session by ID: %s", str(e))
        if 'db' in locals():
            db.close()
        return jsonify({"error": "Failed to join session"}), 500


@sessions_bp.route("/<session_id>/info", methods=["GET"])
def get_session_info(session_id):
    """Get information about a specific session."""
    try:
        db = SessionLocal()

        # Find session
        session = (
            db.query(KaraokeSession)
            .filter(
                KaraokeSession.session_id == session_id,
                KaraokeSession.is_active == True,
            )
            .first()
        )

        if not session:
            db.close()
            return jsonify({"error": "Session not found"}), 404

        if session.is_expired():
            db.close()
            return jsonify({"error": "Session has expired"}), 410

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
                "is_self": d.device_id == (request.remote_addr or "unknown"),
                "display_name": d.display_name,  # Include display name in response
            }
            for d in active_devices
        ]

        result = {
            "session_id": session.session_id,
            "display_code": session.display_code,
            "is_host": (request.remote_addr or "unknown") == session.host_device_id,
            "device_count": len(connected_devices),
            "connected_devices": connected_devices,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "is_active": session.is_active,
        }

        db.close()
        return jsonify(result), 200

    except Exception as e:
        logger.error("Failed to get session info: %s", str(e))
        if 'db' in locals():
            db.close()
        return jsonify({"error": "Failed to get session info"}), 500


@sessions_bp.route("/<session_id>/leave", methods=["POST"])
def leave_session(session_id):
    """Leave a specific session."""
    try:
        db = SessionLocal()

        # Find the device in the session
        device = (
            db.query(SessionDevice)
            .filter(
                SessionDevice.session_id == session_id,
                SessionDevice.device_id == (request.remote_addr or "unknown"),
                SessionDevice.is_active == True,
            )
            .first()
        )

        if not device:
            db.close()
            return jsonify({"error": "Not in this session"}), 404

        # Mark device as inactive
        device.is_active = False
        db.commit()

        # Check if this was the host
        session = (
            db.query(KaraokeSession)
            .filter(KaraokeSession.session_id == session_id)
            .first()
        )

        if session and (request.remote_addr or "unknown") == session.host_device_id:
            # If host is leaving, mark session as inactive
            session.is_active = False
            db.commit()
            logger.info("Session %s ended - host left", session_id)

        logger.info(
            "Device %s left session %s",
            request.remote_addr,
            session_id,
        )

        db.close()
        return jsonify({"message": "Left session successfully"}), 200

    except Exception as e:
        logger.error("Failed to leave session: %s", str(e))
        if 'db' in locals():
            db.close()
        return jsonify({"error": "Failed to leave session"}), 500