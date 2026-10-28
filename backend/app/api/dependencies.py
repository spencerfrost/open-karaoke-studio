"""
Shared FastAPI dependencies for Open Karaoke Studio.
"""

import logging
from dataclasses import dataclass
from typing import Generator, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import KaraokeSession, SessionDevice, User
from app.services.auth_service import verify_token
from app.services.session_service import find_session_member

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
    device = find_session_member(db, session_id, device_id)
    if device is None:
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
    """Who is making the request: an account holder, a session device, or both.

    A signed-in phone that joined a session sends both credentials, and both are
    kept: the account says who they are, the device says which session they're in.
    """

    user: Optional[User] = None
    device: Optional[SessionDevice] = None
    session_id: Optional[str] = None


async def require_host_or_session_member(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    db: Session = Depends(get_db),
) -> RequesterContext:
    """Allow any logged-in account OR a member of a live session.

    An expired or invalid token doesn't lock out a caller who also holds a valid
    session credential - they continue as that session's guest. With no session
    credential to fall back on, the token's 401 stands so the client can sign out.
    """
    user = None
    token_error = None
    if credentials is not None:
        try:
            user = _resolve_user(credentials.credentials, db)
        except HTTPException as e:
            token_error = e

    device = None
    if x_session_id and x_device_id:
        device = find_session_member(db, x_session_id, x_device_id)

    if user is None and device is None:
        if token_error is not None:
            raise token_error
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Login or active session membership required",
        )

    return RequesterContext(
        user=user,
        device=device,
        session_id=device.session_id if device else None,
    )


def ensure_session_access(
    requester: RequesterContext, session_id: str, db: Session
) -> None:
    """Raise 403 unless the requester may act inside `session_id`.

    Allowed: a member device of that session, the account that hosts it, or an
    admin. Holding *an* account is not enough - registration and the demo hand
    out accounts to anyone, and an account that could address any session would
    be a way around the rate-limited join-by-code. A missing session and someone
    else's session get the same 403, so this can't be used to find live codes.
    """
    if requester.session_id == session_id:
        return
    user = requester.user
    if user is not None:
        if user.is_admin:
            return
        host_user_id = (
            db.query(KaraokeSession.host_user_id)
            .filter(KaraokeSession.session_id == session_id)
            .scalar()
        )
        if host_user_id is not None and host_user_id == user.id:
            return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of that session"
    )
