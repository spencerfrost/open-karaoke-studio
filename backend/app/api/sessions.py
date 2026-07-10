"""
Sessions API endpoints for Open Karaoke Studio FastAPI backend.

This module provides REST API endpoints for session management:
- Creating new sessions
- Joining sessions by code or ID
- Getting session information
- Validating sessions
- Leaving sessions
"""

import logging
import uuid
from datetime import datetime
from typing import Generator, List, Optional

from app.api.dependencies import get_current_user, require_host
from app.db.database import SessionLocal
from app.db.models import KaraokeSession, SessionDevice, User
from app.limiter import limiter
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# ============================================================================
# Pydantic Models
# ============================================================================


class DeviceInfo(BaseModel):
    """Connected device information"""

    device_id: str
    device_type: str
    joined_at: str
    is_self: bool
    display_name: Optional[str] = None


class SessionResponse(BaseModel):
    """Response model for session operations"""

    session_id: str
    display_code: str
    device_id: Optional[str] = None
    is_host: bool
    device_type: Optional[str] = None
    device_count: int
    connected_devices: List[DeviceInfo]
    created_at: str
    expires_at: str
    is_active: bool


class SessionCreateRequest(BaseModel):
    """Request model for creating a session"""

    device_type: str = Field(
        default="stage", description="Type of device (stage, performer, audience)"
    )
    display_name: Optional[str] = Field(None, description="Display name for the host")


class SessionJoinByCodeRequest(BaseModel):
    """Request model for joining by display code"""

    code: str = Field(
        ..., min_length=4, max_length=4, description="4-character session code"
    )
    device_type: str = Field(default="performer", description="Type of device")
    display_name: Optional[str] = Field(None, description="Display name for the user")


class SessionJoinByIdRequest(BaseModel):
    """Request model for joining by session ID"""

    session_id: str = Field(..., description="Session ID to join")
    device_type: str = Field(default="performer", description="Type of device")
    display_name: Optional[str] = Field(None, description="Display name for the user")


class SessionValidationResponse(BaseModel):
    """Response model for session validation"""

    valid: bool
    session_id: Optional[str] = None
    display_code: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[str] = None
    created_at: Optional[str] = None
    error: Optional[str] = None


class SessionLeaveResponse(BaseModel):
    """Response model for leaving a session"""

    message: str


# ============================================================================
# Dependencies
# ============================================================================


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error("Database session error: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/my", response_model=Optional[SessionResponse])
async def get_my_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_host),
):
    """
    Get the host's current active session, or null if none exists.
    """
    session = (
        db.query(KaraokeSession)
        .filter(
            KaraokeSession.host_user_id == current_user.id,
            KaraokeSession.is_active.is_(True),
        )
        .first()
    )

    if not session or session.is_expired():
        return None

    active_devices = (
        db.query(SessionDevice)
        .filter(
            SessionDevice.session_id == session.session_id,
            SessionDevice.is_active.is_(True),
        )
        .all()
    )

    return SessionResponse(
        session_id=session.session_id,
        display_code=session.display_code,
        is_host=True,
        device_count=len(active_devices),
        connected_devices=[
            DeviceInfo(
                device_id=d.device_id,
                device_type=d.device_type,
                joined_at=d.joined_at.isoformat(),
                is_self=False,
                display_name=d.display_name,
            )
            for d in active_devices
        ],
        created_at=session.created_at.isoformat(),
        expires_at=session.expires_at.isoformat(),
        is_active=session.is_active,
    )


@router.post("/my", response_model=SessionResponse, status_code=201)
async def get_or_create_my_session(
    request: Request,
    session_data: SessionCreateRequest = SessionCreateRequest(),
    user_agent: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_host),
):
    """
    Get the host's existing active session or create a new one.
    All devices logged in as the same host auto-join this session.
    """
    from app.db.models import HostSettings

    # Check for existing active session
    existing = (
        db.query(KaraokeSession)
        .filter(
            KaraokeSession.host_user_id == current_user.id,
            KaraokeSession.is_active.is_(True),
        )
        .first()
    )

    if existing and not existing.is_expired():
        # Register this device in the existing session
        device_id = f"rest_{uuid.uuid4().hex[:12]}"
        device_type = session_data.device_type
        device = SessionDevice(
            session_id=existing.session_id,
            device_id=device_id,
            device_type=device_type,
            user_agent=user_agent,
            display_name=session_data.display_name or current_user.display_name,
        )
        db.add(device)
        db.commit()

        active_devices = (
            db.query(SessionDevice)
            .filter(
                SessionDevice.session_id == existing.session_id,
                SessionDevice.is_active.is_(True),
            )
            .all()
        )

        return SessionResponse(
            session_id=existing.session_id,
            display_code=existing.display_code,
            device_id=device_id,
            is_host=True,
            device_type=device_type,
            device_count=len(active_devices),
            connected_devices=[
                DeviceInfo(
                    device_id=d.device_id,
                    device_type=d.device_type,
                    joined_at=d.joined_at.isoformat(),
                    is_self=d.device_id == device_id,
                    display_name=d.display_name,
                )
                for d in active_devices
            ],
            created_at=existing.created_at.isoformat(),
            expires_at=existing.expires_at.isoformat(),
            is_active=existing.is_active,
        )

    # Get host settings for session duration
    host_settings = (
        db.query(HostSettings).filter(HostSettings.user_id == current_user.id).first()
    )
    duration_hours = host_settings.session_duration_hours if host_settings else 8

    # Create a new session
    device_id = f"rest_{uuid.uuid4().hex[:12]}"
    device_type = session_data.device_type

    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            session = KaraokeSession.create_new_session(
                db, host_device_id=device_id, duration_hours=duration_hours
            )
            session.host_user_id = current_user.id
            db.add(session)
            db.commit()

            host_device = SessionDevice(
                session_id=session.session_id,
                device_id=device_id,
                device_type=device_type,
                user_agent=user_agent,
                display_name=session_data.display_name or current_user.display_name,
            )
            db.add(host_device)
            db.commit()

            logger.info(
                "Host user %s created session %s",
                current_user.username,
                session.session_id,
            )

            return SessionResponse(
                session_id=session.session_id,
                display_code=session.display_code,
                device_id=device_id,
                is_host=True,
                device_type=device_type,
                device_count=1,
                connected_devices=[
                    DeviceInfo(
                        device_id=host_device.device_id,
                        device_type=host_device.device_type,
                        joined_at=host_device.joined_at.isoformat(),
                        is_self=True,
                        display_name=host_device.display_name,
                    )
                ],
                created_at=session.created_at.isoformat(),
                expires_at=session.expires_at.isoformat(),
                is_active=session.is_active,
            )

        except IntegrityError:
            db.rollback()
            if attempt == max_attempts - 1:
                raise HTTPException(
                    status_code=500, detail="Failed to create unique session"
                )
            continue

    raise HTTPException(status_code=500, detail="Failed to create session")


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    request: Request,
    session_data: SessionCreateRequest = SessionCreateRequest(),
    user_agent: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new karaoke session.
    """
    device_type = session_data.device_type
    display_name = session_data.display_name

    if device_type not in SessionDevice.DEVICE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid device type")

    # Generate a unique device ID for REST API clients
    device_id = f"rest_{uuid.uuid4().hex[:12]}"

    # Try to create a unique session
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            session = KaraokeSession.create_new_session(db, host_device_id=device_id)
            db.add(session)
            db.commit()

            # Create host device record
            host_device = SessionDevice(
                session_id=session.session_id,
                device_id=device_id,
                device_type=device_type,
                user_agent=user_agent,
                display_name=display_name,
            )
            db.add(host_device)
            db.commit()

            logger.info(
                "Created session %s with code %s for host %s",
                session.session_id,
                session.display_code,
                device_id,
            )

            return SessionResponse(
                session_id=session.session_id,
                display_code=session.display_code,
                device_id=device_id,
                is_host=True,
                device_type=device_type,
                device_count=1,
                connected_devices=[
                    DeviceInfo(
                        device_id=host_device.device_id,
                        device_type=host_device.device_type,
                        joined_at=host_device.joined_at.isoformat(),
                        is_self=True,
                        display_name=host_device.display_name,
                    )
                ],
                created_at=session.created_at.isoformat(),
                expires_at=session.expires_at.isoformat(),
                is_active=session.is_active,
            )

        except IntegrityError:
            db.rollback()
            if attempt == max_attempts - 1:
                raise HTTPException(
                    status_code=500, detail="Failed to create unique session"
                )
            continue

    raise HTTPException(status_code=500, detail="Failed to create session")


@router.post("/join-by-code", response_model=SessionResponse)
@limiter.limit("10/minute")
async def join_session_by_code(
    request: Request,
    join_data: SessionJoinByCodeRequest,
    user_agent: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Join a session using a 4-character display code.
    """
    display_code = join_data.code.upper().strip()
    device_type = join_data.device_type
    display_name = join_data.display_name

    if len(display_code) != 4:
        raise HTTPException(status_code=400, detail="Invalid display code")

    if device_type not in SessionDevice.DEVICE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid device type")

    # Generate a unique device ID
    device_id = f"rest_{uuid.uuid4().hex[:12]}"

    # Find session by display code
    session = (
        db.query(KaraokeSession)
        .filter(
            KaraokeSession.display_code == display_code,
            KaraokeSession.is_active.is_(True),
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    if session.is_expired():
        raise HTTPException(status_code=410, detail="Session has expired")

    # Create device record
    device = SessionDevice(
        session_id=session.session_id,
        device_id=device_id,
        device_type=device_type,
        user_agent=user_agent,
        display_name=display_name,
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
        DeviceInfo(
            device_id=d.device_id,
            device_type=d.device_type,
            joined_at=d.joined_at.isoformat(),
            is_self=d.device_id == device_id,
            display_name=d.display_name,
        )
        for d in active_devices
    ]

    logger.info(
        "Device %s joined session %s as %s",
        device_id,
        session.session_id,
        device_type,
    )

    return SessionResponse(
        session_id=session.session_id,
        display_code=session.display_code,
        device_id=device_id,
        is_host=device_id == session.host_device_id,
        device_type=device_type,
        device_count=len(connected_devices),
        connected_devices=connected_devices,
        created_at=session.created_at.isoformat(),
        expires_at=session.expires_at.isoformat(),
        is_active=session.is_active,
    )


@router.post("/join-by-id", response_model=SessionResponse)
@limiter.limit("10/minute")
async def join_session_by_id(
    request: Request,
    join_data: SessionJoinByIdRequest,
    user_agent: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Join a session using the session ID.
    """
    session_id = join_data.session_id.strip()
    device_type = join_data.device_type
    display_name = join_data.display_name

    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")

    if device_type not in SessionDevice.DEVICE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid device type")

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
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_expired():
        raise HTTPException(status_code=410, detail="Session has expired")

    # Generate device ID from request info
    client_host = request.client.host if request.client else "unknown"

    # Check if device is already in session
    existing_device = (
        db.query(SessionDevice)
        .filter(
            SessionDevice.session_id == session.session_id,
            SessionDevice.device_id == client_host,
            SessionDevice.is_active == True,
        )
        .first()
    )

    if existing_device:
        raise HTTPException(status_code=409, detail="Already joined this session")

    # Create device record
    device = SessionDevice(
        session_id=session.session_id,
        device_id=client_host,
        device_type=device_type,
        user_agent=user_agent,
        display_name=display_name,
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
        DeviceInfo(
            device_id=d.device_id,
            device_type=d.device_type,
            joined_at=d.joined_at.isoformat(),
            is_self=d.device_id == client_host,
            display_name=d.display_name,
        )
        for d in active_devices
    ]

    logger.info(
        "Device %s joined session %s as %s",
        client_host,
        session.session_id,
        device_type,
    )

    return SessionResponse(
        session_id=session.session_id,
        display_code=session.display_code,
        is_host=client_host == session.host_device_id,
        device_type=device_type,
        device_count=len(connected_devices),
        connected_devices=connected_devices,
        created_at=session.created_at.isoformat(),
        expires_at=session.expires_at.isoformat(),
        is_active=session.is_active,
    )


@router.get("/{session_id}/info", response_model=SessionResponse)
async def get_session_info(
    session_id: str,
    request: Request,
    device_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get information about a specific session.

    Pass `device_id` as a query parameter to correctly determine `is_host`
    for REST-created sessions (where host_device_id is a 'rest_xxx' token,
    not an IP address).
    """
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
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_expired():
        raise HTTPException(status_code=410, detail="Session has expired")

    # Use provided device_id for identity if supplied, otherwise fall back to IP
    client_identity = device_id or (
        request.client.host if request.client else "unknown"
    )

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
        DeviceInfo(
            device_id=d.device_id,
            device_type=d.device_type,
            joined_at=d.joined_at.isoformat(),
            is_self=d.device_id == client_identity,
            display_name=d.display_name,
        )
        for d in active_devices
    ]

    return SessionResponse(
        session_id=session.session_id,
        display_code=session.display_code,
        is_host=client_identity == session.host_device_id,
        device_count=len(connected_devices),
        connected_devices=connected_devices,
        created_at=session.created_at.isoformat(),
        expires_at=session.expires_at.isoformat(),
        is_active=session.is_active,
    )


@router.get("/{session_id}/validate", response_model=SessionValidationResponse)
async def validate_session(session_id: str, db: Session = Depends(get_db)):
    """
    Validate if a session exists and is active.
    Used by frontend to check session validity before connecting to WebSocket.
    """
    session = (
        db.query(KaraokeSession)
        .filter(
            KaraokeSession.session_id == session_id,
            KaraokeSession.is_active.is_(True),
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found or inactive",
        )

    # Check if session has expired
    if session.expires_at and session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Session has expired")

    return SessionValidationResponse(
        valid=True,
        session_id=session.session_id,
        display_code=session.display_code,
        is_active=session.is_active,
        expires_at=session.expires_at.isoformat() if session.expires_at else None,
        created_at=session.created_at.isoformat() if session.created_at else None,
    )


@router.post("/{session_id}/leave", response_model=SessionLeaveResponse)
async def leave_session(
    session_id: str, request: Request, db: Session = Depends(get_db)
):
    """
    Leave a specific session.
    """
    client_host = request.client.host if request.client else "unknown"

    # Find the device in the session
    device = (
        db.query(SessionDevice)
        .filter(
            SessionDevice.session_id == session_id,
            SessionDevice.device_id == client_host,
            SessionDevice.is_active == True,
        )
        .first()
    )

    if not device:
        raise HTTPException(status_code=404, detail="Not in this session")

    # Mark device as inactive
    device.is_active = False
    db.commit()

    # Check if this was the host
    session = (
        db.query(KaraokeSession).filter(KaraokeSession.session_id == session_id).first()
    )

    if session and client_host == session.host_device_id:
        # If host is leaving, mark session as inactive
        session.is_active = False
        db.commit()
        logger.info("Session %s ended - host left", session_id)

    logger.info("Device %s left session %s", client_host, session_id)

    return SessionLeaveResponse(message="Left session successfully")
