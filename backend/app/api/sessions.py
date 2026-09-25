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
from datetime import datetime, timedelta
from typing import Generator, List, Literal, Optional

from app.api.dependencies import (
    RequesterContext,
    _resolve_user,
    get_current_user,
    optional_security,
    require_host,
    require_host_or_session_member,
    require_session_member,
)
from app.db.database import SessionLocal
from app.db.models import KaraokeSession, SessionDevice, SessionPerformer, User
from app.limiter import limiter
from app.services.roster_service import (
    resolve_or_create_performer,
    resolve_or_create_performer_verbose,
)
from app.services.session_service import deactivate_session
from app.services.turn_service import claim_turn, compute_turn, pass_turn
from app.ws.connection_manager import SessionConnectionManager
from app.ws.queue import broadcast_queue_update, broadcast_roster_update
from app.ws.session_specific import session_termination_tasks
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
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
    queue_order_mode: str


class SessionCreateRequest(BaseModel):
    """Request model for creating a session"""

    device_type: str = Field(
        default="stage", description="Type of device (stage, performer, audience)"
    )
    display_name: Optional[str] = Field(None, description="Display name for the host")
    device_id: Optional[str] = Field(
        None,
        description="Existing device id to reuse, so remounting does not inflate the device count",
    )
    # Setup collected by the stage's create-session screen. All three are
    # creation-time only: a request that resumes a live session ignores them.
    # See docs/plans/2026-08-30-create-session-screen.md.
    duration_hours: Optional[float] = Field(
        None, description="Override tonight's session length"
    )
    performer_names: Optional[List[str]] = Field(
        None, description="Pre-seed the roster"
    )
    queue_order_mode: Optional[Literal["append", "rotation"]] = Field(
        None,
        description="Override tonight's rotation mode; unset keeps the column default (rotation)",
    )
    include_host_in_roster: bool = Field(
        True,
        description="Seat the host's own name on the roster; false means they run the night without taking turns",
    )
    # The create screen sends "reject" so a live session it did not know about
    # surfaces as a 409 instead of silently swallowing the setup above; the host
    # then picks "resume" or "replace". Other callers keep the old get-or-create.
    on_existing: Literal["resume", "replace", "reject"] = Field(
        "resume",
        description=(
            "What to do if the host already has a live session: resume it (setup "
            "fields ignored), replace it (end it and create a new one), or reject "
            "with 409"
        ),
    )


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


class PerformerResponse(BaseModel):
    """Response model for a roster entry"""

    id: int
    name: str
    seat: int
    is_active: bool


class PerformerCreateRequest(BaseModel):
    """Request model for adding a name to the roster without queueing anything"""

    name: str = Field(..., min_length=1, max_length=100, description="Performer name")


class ExpectedTurnRequest(BaseModel):
    """Base for requests that act on the current turn.

    `expected_performer_id` is the whole concurrency story for the handoff
    screen: it is checked against the turn the server computes, and a mismatch
    is a 409 that changes nothing. First write wins, so a phone and the TV
    acting at the same moment settle on one outcome instead of both landing.
    """

    expected_performer_id: Optional[int] = Field(
        None, description="The performer the caller believes holds the turn"
    )


class TurnClaimRequest(ExpectedTurnRequest):
    """Request model for handing the turn to someone else.

    Either an existing roster entry (`performer_id`) or a new name from the
    picker's "Someone else…" field, which is resolved the same way every other
    roster entry point resolves one.
    """

    performer_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=100)


class QueueOrderModeUpdateRequest(BaseModel):
    """Request model for switching a session's queue ordering mode"""

    mode: str = Field(..., description="'append' or 'rotation'")


class QueueOrderModeResponse(BaseModel):
    """Response model for the current queue ordering mode"""

    queue_order_mode: str


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


def get_session_manager(request: Request) -> SessionConnectionManager:
    """Get the shared SessionConnectionManager from app state."""
    return request.app.state.session_manager


def require_roster_access(
    session_id: str,
    requester: RequesterContext = Depends(require_host_or_session_member),
) -> str:
    """The session id this caller may read or add roster entries for.

    Mirrors karaoke_queue.py's require_queue_access: an account holder may
    address any session, an anonymous session guest is confined to the
    session their device credential names.
    """
    if requester.user is None and requester.session_id != session_id:
        raise HTTPException(status_code=403, detail="Not a member of that session")
    return session_id


# ============================================================================
# Helpers
# ============================================================================


def deactivate_expired_sessions(db: Session) -> int:
    """
    Mark sessions whose expiry has passed as inactive.

    Sessions are normally retired when the host disconnects, but a session whose host
    never disconnects cleanly stays flagged active long past its expiry. Those rows are
    invisible to users yet still match "active session" queries, so they are reconciled
    here. Returns the number of rows updated.
    """
    updated = (
        db.query(KaraokeSession)
        .filter(
            KaraokeSession.is_active.is_(True),
            KaraokeSession.expires_at <= datetime.utcnow(),
        )
        .update({KaraokeSession.is_active: False}, synchronize_session=False)
    )

    if updated:
        db.commit()
        logger.info("Deactivated %d expired session(s)", updated)

    return updated


async def _retire_session(request: Request, db: Session, session_id: str) -> None:
    """End a session the way the host's End button does.

    Deactivates the row and its devices, tells every connected device the session is
    over, and cancels any pending grace-period termination so the session is not
    ended a second time when the host's now-closed socket times out.
    """
    deactivate_session(db, session_id)

    manager = getattr(request.app.state, "session_manager", None)
    if manager is not None:
        await manager.force_close_session_connections(
            session_id, reason="Session ended by host"
        )

    pending = session_termination_tasks.pop(session_id, None)
    if pending is not None:
        pending.cancel()


def purge_stale_sessions(db: Session, older_than_days: int = 7) -> int:
    """
    Hard-delete long-dead sessions, releasing their display codes.

    Sessions are retired by deactivation so their queue survives, but `session_id` doubles
    as the unique 4-character `display_code`, so retained rows hold their code out of
    circulation forever. Rows that have been inactive for `older_than_days` are past any
    use and are deleted outright (cascading to their queue items and playback state).
    Returns the number of sessions removed.
    """
    cutoff = datetime.utcnow() - timedelta(days=older_than_days)

    stale = (
        db.query(KaraokeSession)
        .filter(
            KaraokeSession.is_active.is_(False),
            KaraokeSession.created_at <= cutoff,
        )
        .all()
    )

    for session in stale:
        db.delete(session)

    if stale:
        db.commit()
        logger.info("Purged %d stale session(s), releasing their codes", len(stale))

    return len(stale)


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
    # Same shape as get_or_create_my_session: filter expiry in SQL and take the newest,
    # so a stale row cannot mask a live session and make this report "no session".
    session = (
        db.query(KaraokeSession)
        .filter(
            KaraokeSession.host_user_id == current_user.id,
            KaraokeSession.is_active.is_(True),
            KaraokeSession.expires_at > datetime.utcnow(),
        )
        .order_by(KaraokeSession.created_at.desc())
        .first()
    )

    if not session:
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
        queue_order_mode=session.queue_order_mode,
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

    # Retire any sessions whose expiry has passed but that are still flagged active, so a
    # stale row cannot be picked below and cause a duplicate session to be created.
    deactivate_expired_sessions(db)

    # Retired sessions keep their row - and therefore their display code - so long-dead
    # ones are cleared here to return those codes to circulation.
    purge_stale_sessions(db)

    # Check for an existing live session. Expiry is filtered in SQL and the newest session
    # wins - an unordered .first() could otherwise return a stale row, fail the expiry check,
    # and orphan a live session that still has performers in it.
    existing = (
        db.query(KaraokeSession)
        .filter(
            KaraokeSession.host_user_id == current_user.id,
            KaraokeSession.is_active.is_(True),
            KaraokeSession.expires_at > datetime.utcnow(),
        )
        .order_by(KaraokeSession.created_at.desc())
        .first()
    )

    if existing and session_data.on_existing == "reject":
        raise HTTPException(
            status_code=409,
            detail={
                "message": "You already have a session running",
                "session_id": existing.session_id,
                "display_code": existing.display_code,
                "created_at": existing.created_at.isoformat(),
            },
        )

    if existing and session_data.on_existing == "replace":
        await _retire_session(request, db, existing.session_id)
        logger.info(
            "Host %s replaced session %s with a new one",
            current_user.username,
            existing.session_id,
        )
        existing = None

    if existing:
        device_type = session_data.device_type
        display_name = session_data.display_name or current_user.display_name

        # Reuse the caller's device row if it is already in this session. Without this every
        # remount inserts another row and inflates device_count and the device list.
        device = (
            db.query(SessionDevice)
            .filter(
                SessionDevice.session_id == existing.session_id,
                SessionDevice.device_id == session_data.device_id,
                SessionDevice.is_active.is_(True),
            )
            .first()
            if session_data.device_id
            else None
        )

        if device:
            device.device_type = device_type
            device.user_agent = user_agent
            device.display_name = display_name
        else:
            device = SessionDevice(
                session_id=existing.session_id,
                device_id=f"rest_{uuid.uuid4().hex[:12]}",
                device_type=device_type,
                user_agent=user_agent,
                display_name=display_name,
            )
            db.add(device)

        # No roster write here. Whether the host sings was decided when the
        # session was created; seating them on every resume would undo an
        # opt-out the moment the stage remounted or a second device joined.

        db.commit()
        device_id = device.device_id

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
            queue_order_mode=existing.queue_order_mode,
        )

    # Get host settings for session duration. A duration_hours in the request is a
    # one-off override for tonight and deliberately does not touch the stored
    # default. Checked with `is not None` rather than `or` so an explicit 0 is not
    # silently swapped for the default.
    host_settings = (
        db.query(HostSettings).filter(HostSettings.user_id == current_user.id).first()
    )
    host_default_hours = host_settings.session_duration_hours if host_settings else 8
    duration_hours = (
        session_data.duration_hours
        if session_data.duration_hours is not None
        else host_default_hours
    )

    # Create a new session
    device_id = f"rest_{uuid.uuid4().hex[:12]}"
    device_type = session_data.device_type

    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            session = KaraokeSession.create_new_session(
                db,
                host_device_id=device_id,
                duration_hours=duration_hours,
                queue_order_mode=session_data.queue_order_mode,
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

            # The host is a singer by default, but a host who is only running
            # the night can opt out on the create screen. Opting out skips the
            # roster row entirely; nothing else keys off it, and joining by name
            # later creates one the ordinary way.
            if session_data.include_host_in_roster and host_device.display_name:
                resolve_or_create_performer(
                    db,
                    session.session_id,
                    host_device.display_name,
                    device_id=host_device.device_id,
                )

            # Names the host pre-listed on the create screen. No device_id: these
            # are anonymous roster rows, identical to a walk-up who never picks up
            # a phone. resolve_or_create_performer dedupes by normalized name, so a
            # repeat (or the host's own name) is a no-op.
            for name in session_data.performer_names or []:
                if name and name.strip():
                    resolve_or_create_performer(db, session.session_id, name)

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
                queue_order_mode=session.queue_order_mode,
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
            # Record the owning user. Host authority on the session WebSocket is derived
            # from host_user_id, so a session created without it can never have a host.
            session.host_user_id = current_user.id
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
                queue_order_mode=session.queue_order_mode,
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

    if display_name:
        resolve_or_create_performer(
            db, session.session_id, display_name, device_id=device_id
        )

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
        queue_order_mode=session.queue_order_mode,
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

    if display_name:
        resolve_or_create_performer(
            db, session.session_id, display_name, device_id=client_host
        )

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
        queue_order_mode=session.queue_order_mode,
    )


@router.get("/{session_id}/info", response_model=SessionResponse)
async def get_session_info(
    session_id: str,
    request: Request,
    device_id: Optional[str] = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: Session = Depends(get_db),
):
    """
    Get information about a specific session.

    `is_host` comes from the bearer token when one is supplied, since ownership lives on
    `host_user_id` - the same source the session WebSocket uses. Anonymous callers fall
    back to comparing `host_device_id`, so pass `device_id` as a query parameter for that
    path (host_device_id is a 'rest_xxx' token, not an IP address).
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

    # Ownership lives on host_user_id; the device comparison is only for anonymous callers.
    if credentials is not None:
        is_host = _resolve_user(credentials.credentials, db).id == session.host_user_id
    else:
        is_host = client_identity == session.host_device_id

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
        is_host=is_host,
        device_count=len(connected_devices),
        connected_devices=connected_devices,
        created_at=session.created_at.isoformat(),
        expires_at=session.expires_at.isoformat(),
        is_active=session.is_active,
        queue_order_mode=session.queue_order_mode,
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
    session_id: str,
    device: SessionDevice = Depends(require_session_member),
    db: Session = Depends(get_db),
):
    """
    Leave a specific session - this device only, never ending the session itself.

    The device is resolved from the caller's X-Session-ID / X-Device-ID credential. An
    earlier version looked it up by request IP, which could never match the `rest_<hex>`
    device ids this API issues, so leaving always 404'd. Ending a session outright is
    `DELETE /{session_id}`, which only the owning host may call.
    """
    if device.session_id != session_id:
        raise HTTPException(status_code=403, detail="Not a member of this session")

    # require_session_member resolves the row through app.api.dependencies.get_db, which is
    # a different Session from this module's, so mutate the row this endpoint owns.
    db.query(SessionDevice).filter(
        SessionDevice.session_id == session_id,
        SessionDevice.device_id == device.device_id,
    ).update({SessionDevice.is_active: False}, synchronize_session=False)
    db.commit()

    logger.info("Device %s left session %s", device.device_id, session_id)

    return SessionLeaveResponse(message="Left session successfully")


@router.delete("/{session_id}", response_model=SessionLeaveResponse)
async def end_session(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_host),
):
    """
    End a session: deactivate it and all of its devices, and close its WebSocket room.

    The session row, its queue items and its playback state are all kept - a session is
    retired, never deleted, so its history survives and a stale row cannot take the queue
    down with it. `purge_stale_sessions` reclaims the row (and its code) later.
    """
    session = (
        db.query(KaraokeSession).filter(KaraokeSession.session_id == session_id).first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.host_user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only the session's host can end it"
        )

    await _retire_session(request, db, session_id)

    logger.info("Host %s ended session %s", current_user.username, session_id)

    return SessionLeaveResponse(message="Session ended")


@router.get("/{session_id}/performers", response_model=List[PerformerResponse])
async def list_performers(
    session_id: str = Depends(require_roster_access),
    db: Session = Depends(get_db),
):
    """List the session's roster - everyone who has joined, been picked, or been
    added by name, whether or not they have a device attached."""
    performers = (
        db.query(SessionPerformer)
        .filter(
            SessionPerformer.session_id == session_id,
            SessionPerformer.is_active.is_(True),
        )
        .order_by(SessionPerformer.seat)
        .all()
    )
    return [
        PerformerResponse(id=p.id, name=p.name, seat=p.seat, is_active=p.is_active)
        for p in performers
    ]


@router.post(
    "/{session_id}/performers", response_model=PerformerResponse, status_code=201
)
async def add_performer(
    performer_data: PerformerCreateRequest,
    session_id: str = Depends(require_roster_access),
    db: Session = Depends(get_db),
    manager: SessionConnectionManager = Depends(get_session_manager),
):
    """Add a name to the roster without queueing anything - for pre-adding someone
    who isn't touching a screen right now. Dedupes against an existing entry the
    same way every other roster entry point does."""
    session = (
        db.query(KaraokeSession)
        .filter(
            KaraokeSession.session_id == session_id,
            KaraokeSession.is_active.is_(True),
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or inactive")

    try:
        performer, created = resolve_or_create_performer_verbose(
            db, session_id, performer_data.name
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db.commit()

    if created:
        await broadcast_roster_update(manager, session_id, performer.name)

    return PerformerResponse(
        id=performer.id,
        name=performer.name,
        seat=performer.seat,
        is_active=performer.is_active,
    )


# ============================================================================
# The turn - unit 4's handoff screen
# ============================================================================
#
# All three run under require_roster_access rather than host auth. The handoff
# screen is the part guests operate: someone walks up to the TV between songs
# and says who they are or steps aside. Requiring the host to be standing there
# would defeat the feature. Session-level *settings* stay host-only - see
# set_queue_order_mode below.


def _active_session_or_404(db: Session, session_id: str) -> KaraokeSession:
    session = (
        db.query(KaraokeSession)
        .filter(
            KaraokeSession.session_id == session_id,
            KaraokeSession.is_active.is_(True),
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or inactive")
    return session


def _check_expected(turn, expected_performer_id: Optional[int]) -> None:
    """Reject an action aimed at a turn that has already moved on.

    The loser of a race - two devices, or a timer that fired against a screen
    someone had already acted on - gets a 409 and mutates nothing.
    """
    if expected_performer_id is None:
        return
    holder = turn.performer.id if turn.performer else None
    if holder != expected_performer_id:
        raise HTTPException(status_code=409, detail="The turn has already moved on")


@router.post("/{session_id}/turn/claim", response_model=PerformerResponse)
async def claim_current_turn(
    body: TurnClaimRequest,
    session_id: str = Depends(require_roster_access),
    db: Session = Depends(get_db),
    manager: SessionConnectionManager = Depends(get_session_manager),
):
    """Hand the turn to someone else - the screen's "That's not me".

    Whoever held it is passed forward invisibly. The person stepping up only
    says who they are; they never adjudicate somebody else's turn in front of
    the room.
    """
    session = _active_session_or_404(db, session_id)
    turn = compute_turn(db, session_id)
    _check_expected(turn, body.expected_performer_id)

    if body.performer_id is not None:
        claimant = (
            db.query(SessionPerformer)
            .filter(
                SessionPerformer.id == body.performer_id,
                SessionPerformer.session_id == session_id,
            )
            .first()
        )
        if claimant is None:
            raise HTTPException(status_code=404, detail="Performer not found")
        created = False
    elif body.name:
        try:
            claimant, created = resolve_or_create_performer_verbose(
                db, session_id, body.name
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail="performer_id or name is required")

    claim_turn(db, session, turn, claimant)
    db.commit()

    if created:
        await broadcast_roster_update(manager, session_id, claimant.name)
    await broadcast_queue_update(manager, session_id)

    return PerformerResponse(
        id=claimant.id,
        name=claimant.name,
        seat=claimant.seat,
        is_active=claimant.is_active,
    )


@router.post(
    "/{session_id}/performers/{performer_id}/deactivate",
    response_model=PerformerResponse,
)
async def deactivate_performer(
    performer_id: int,
    session_id: str = Depends(require_roster_access),
    db: Session = Depends(get_db),
    manager: SessionConnectionManager = Depends(get_session_manager),
):
    """Step out of the rotation - the screen's "Skip me for now".

    Deliberate and self-service, unlike the automatic pass. The seat stops being
    offered until this person queues something, claims a turn, or joins again -
    any of which routes through `roster_service.mark_active`.

    If they are holding the turn right now, pass it forward too, so the button
    does something visible even for someone with songs already queued.
    """
    session = _active_session_or_404(db, session_id)
    performer = (
        db.query(SessionPerformer)
        .filter(
            SessionPerformer.id == performer_id,
            SessionPerformer.session_id == session_id,
        )
        .first()
    )
    if performer is None:
        raise HTTPException(status_code=404, detail="Performer not found")

    turn = compute_turn(db, session_id)
    if turn.performer is not None and turn.performer.id == performer.id:
        pass_turn(session, turn)

    performer.is_active = False
    db.commit()

    await broadcast_queue_update(manager, session_id)
    return PerformerResponse(
        id=performer.id,
        name=performer.name,
        seat=performer.seat,
        is_active=performer.is_active,
    )


@router.patch("/{session_id}/queue-order-mode", response_model=QueueOrderModeResponse)
async def set_queue_order_mode(
    session_id: str,
    mode_data: QueueOrderModeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_host),
):
    """Switch a session between append and rotation queue ordering.

    Deliberately not exposed on the stage/TV screen - it's the Settings-page
    control described in docs/plans/2026-08-29-roster-and-rotation.md's open
    decisions, so a performer glancing at the TV never sees host controls.
    """
    if mode_data.mode not in ("append", "rotation"):
        raise HTTPException(
            status_code=400, detail="mode must be 'append' or 'rotation'"
        )

    session = (
        db.query(KaraokeSession)
        .filter(
            KaraokeSession.session_id == session_id,
            KaraokeSession.is_active.is_(True),
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or inactive")
    if session.host_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not your session")

    session.queue_order_mode = mode_data.mode
    db.commit()

    return QueueOrderModeResponse(queue_order_mode=session.queue_order_mode)
