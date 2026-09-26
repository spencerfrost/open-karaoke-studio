"""
Shared FastAPI dependencies for Open Karaoke Studio.
"""

import logging
from dataclasses import dataclass
from typing import Generator, Optional

from app.db.database import SessionLocal
from app.db.models import KaraokeSession, SessionDevice, User
from app.services.auth_service import verify_token
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error("Database session error: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


def _resolve_user(token: str, db: Session) -> User:
    """Validate a JWT and return the matching User, or raise 401."""
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate JWT token from Authorization header. Returns the User."""
    return _resolve_user(credentials.credentials, db)


async def require_host(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the current user to be a host or admin."""
    if not (current_user.is_host or current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Host or admin access required",
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the current user to be an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def _resolve_session_member(
    session_id: str, device_id: str, db: Session
) -> SessionDevice:
    """Return the active SessionDevice for a live session, or raise 403."""
    device = (
        db.query(SessionDevice)
        .join(KaraokeSession, KaraokeSession.session_id == SessionDevice.session_id)
        .filter(
            SessionDevice.device_id == device_id,
            SessionDevice.session_id == session_id,
            SessionDevice.is_active.is_(True),
            KaraokeSession.is_active.is_(True),
        )
        .first()
    )
    if device is None or device.session.is_expired():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of an active session",
        )
    return device


async def require_session_member(
    x_session_id: str = Header(..., alias="X-Session-ID"),
    x_device_id: str = Header(..., alias="X-Device-ID"),
    db: Session = Depends(get_db),
) -> SessionDevice:
    """Require a valid session-member credential (device minted at session join)."""
    return _resolve_session_member(x_session_id, x_device_id, db)


@dataclass
class RequesterContext:
    """Who is making the request: an account holder (user) or a session device."""

    user: Optional[User] = None
    device: Optional[SessionDevice] = None
    session_id: Optional[str] = None


async def require_host_or_session_member(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    db: Session = Depends(get_db),
) -> RequesterContext:
    """Allow any logged-in account OR an anonymous member of a live session.

    Any valid account outranks an anonymous session guest, so the JWT path
    accepts all account tiers (performer accounts will rely on this).
    """
    if credentials is not None:
        user = _resolve_user(credentials.credentials, db)
        return RequesterContext(user=user)

    if x_session_id and x_device_id:
        device = _resolve_session_member(x_session_id, x_device_id, db)
        return RequesterContext(device=device, session_id=device.session_id)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Login or active session membership required",
    )
