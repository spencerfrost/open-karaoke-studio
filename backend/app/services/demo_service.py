"""
Demo account pool: alias login resolution and download quota enforcement.

A pool of `is_demo` host accounts sits behind one published alias credential
(DEMO_LOGIN_USERNAME / DEMO_LOGIN_PASSWORD env vars; feature disabled when
unset). Alias logins are resolved to a free pool account and eagerly start
that account's karaoke session, so concurrent visitors never share a session
and the (short) session clock starts at login.
"""

import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from app.api.dependencies import RequesterContext
from app.db.models import DbJob, HostSettings, KaraokeSession, User
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

DEMO_SESSION_DOWNLOAD_LIMIT = 3
DEMO_DAILY_DOWNLOAD_LIMIT = 20
DEMO_TOKEN_EXPIRE_MINUTES = 30
DEMO_SESSION_FALLBACK_DURATION_HOURS = 0.25


def resolve_demo_login(db: Session, username: str, password: str) -> Optional[User]:
    """Resolve alias credentials to a free demo pool account.

    Returns None when the demo feature is disabled or the credentials don't
    match the alias (the caller falls through to normal login — pool accounts'
    own passwords keep working). Raises 503 when every pool account is busy.
    """
    alias_username = os.environ.get("DEMO_LOGIN_USERNAME")
    alias_password = os.environ.get("DEMO_LOGIN_PASSWORD")
    if not alias_username or not alias_password:
        return None
    if username != alias_username or not secrets.compare_digest(
        password, alias_password
    ):
        return None

    user = _acquire_pool_account(db)
    if user is None:
        logger.info("Demo alias login rejected: all pool accounts busy")
        raise HTTPException(
            status_code=503,
            detail="The demo is busy right now — try again in a few minutes.",
        )
    logger.info("Demo alias login resolved to pool account %s", user.username)
    return user


def _acquire_pool_account(db: Session) -> Optional[User]:
    """Pick a demo account with no live session and start its session."""
    pool = (
        db.query(User)
        .filter(User.is_demo.is_(True))
        .order_by(User.id)
        .with_for_update()
        .all()
    )
    if not pool:
        return None

    now = datetime.utcnow()
    busy_rows = (
        db.query(KaraokeSession.host_user_id)
        .filter(
            KaraokeSession.host_user_id.in_([u.id for u in pool]),
            KaraokeSession.is_active.is_(True),
            KaraokeSession.expires_at > now,
        )
        .all()
    )
    busy = {row[0] for row in busy_rows}

    for user in pool:
        if user.id not in busy:
            _start_demo_session(db, user)
            return user
    return None


def _start_demo_session(db: Session, user: User) -> KaraokeSession:
    """Eagerly create the pool account's karaoke session (starts its clock).

    The frontend's later POST /sessions/my reuses this session and registers
    the visitor's device into it; the placeholder host_device_id is never
    matched against.
    """
    host_settings = (
        db.query(HostSettings).filter(HostSettings.user_id == user.id).first()
    )
    duration_hours = (
        host_settings.session_duration_hours
        if host_settings
        else DEMO_SESSION_FALLBACK_DURATION_HOURS
    )

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            session = KaraokeSession.create_new_session(
                db,
                host_device_id=f"demo_{uuid.uuid4().hex[:12]}",
                duration_hours=duration_hours,
            )
            session.host_user_id = user.id
            db.add(session)
            db.commit()
            return session
        except IntegrityError:
            db.rollback()
            if attempt == max_attempts - 1:
                raise HTTPException(
                    status_code=500, detail="Failed to create demo session"
                )
    raise HTTPException(status_code=500, detail="Failed to create demo session")


def enforce_demo_download_quota(
    db: Session, requester: RequesterContext
) -> tuple[Optional[str], Optional[int]]:
    """Enforce demo download quotas; return (session_id, user_id) attribution.

    Attribution is resolved for every requester (demo or not) so jobs can be
    tied back to the session/account that started them. Quota counting only
    happens when the resolved session's host — or the requester — is a demo
    account; everyone else is untouched.
    """
    user = requester.user
    user_id = user.id if user else None

    session: Optional[KaraokeSession] = None
    if requester.session_id:
        # Anonymous session guest — membership already verified upstream.
        session = (
            db.query(KaraokeSession)
            .filter(KaraokeSession.session_id == requester.session_id)
            .first()
        )
    elif user is not None:
        # Account holder — attribute to their active session, if any.
        session = (
            db.query(KaraokeSession)
            .filter(
                KaraokeSession.host_user_id == user.id,
                KaraokeSession.is_active.is_(True),
                KaraokeSession.expires_at > datetime.utcnow(),
            )
            .first()
        )

    host: Optional[User] = None
    if session is not None and session.host_user_id is not None:
        host = db.get(User, session.host_user_id)
    session_id = session.session_id if session else None

    demo_request = (host is not None and host.is_demo) or (
        user is not None and user.is_demo
    )
    if not demo_request:
        return session_id, user_id

    if session is None:
        # Demo JWT with no live session (expired or never started).
        raise HTTPException(
            status_code=403,
            detail="Your demo session has ended — log in again to start a new one.",
        )

    session_count = (
        db.query(func.count(DbJob.id)).filter(DbJob.session_id == session_id).scalar()
        or 0
    )
    if session_count >= DEMO_SESSION_DOWNLOAD_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Demo limit: {DEMO_SESSION_DOWNLOAD_LIMIT} new songs per session. "
                "You can still queue anything already in the library."
            ),
        )

    cutoff = datetime.utcnow() - timedelta(hours=24)
    daily_count = (
        db.query(func.count(DbJob.id))
        .join(KaraokeSession, KaraokeSession.session_id == DbJob.session_id)
        .join(User, User.id == KaraokeSession.host_user_id)
        .filter(User.is_demo.is_(True), DbJob.created_at >= cutoff)
        .scalar()
        or 0
    )
    if daily_count >= DEMO_DAILY_DOWNLOAD_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=(
                "The demo's daily download budget is used up — "
                "existing library songs still work."
            ),
        )

    return session_id, user_id
