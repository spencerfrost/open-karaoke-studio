"""
Demo account pool: handing out pool accounts and download quota enforcement.

A pool of `is_demo` host accounts backs POST /api/demo/start. Each start picks
a free pool account and eagerly starts that account's karaoke session, so
concurrent visitors never share a session and the (short) session clock starts
straight away. No credential is published: the endpoint issues the token.
"""

import logging
import uuid
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import RequesterContext
from app.db.models import DbJob, HostSettings, JobStatus, KaraokeSession, User
from app.utils.clock import utc_now

logger = logging.getLogger(__name__)

DEMO_SESSION_DOWNLOAD_LIMIT = 3
DEMO_DAILY_DOWNLOAD_LIMIT = 20
# Attempts that delivered nothing must not burn quota. Failure rows persist now
# (they back the in-app retry UI) rather than being deleted, so counting every
# row would let one bad link cost a visitor a third of their session allowance.
UNCOUNTED_JOB_STATUSES = (JobStatus.FAILED.value, JobStatus.CANCELLED.value)
DEMO_TOKEN_EXPIRE_MINUTES = 30
DEMO_SESSION_FALLBACK_DURATION_HOURS = 0.25


def demo_enabled(db: Session) -> bool:
    """Whether this server offers the live demo: any pool account is seeded."""
    return db.query(User.id).filter(User.is_demo.is_(True)).first() is not None


def start_demo(db: Session) -> User:
    """Hand a visitor a free demo pool account with its session started.

    Raises 503 when no pool account is free (or none is seeded, which reads
    the same to a visitor: there's no seat for them right now).
    """
    user = _acquire_pool_account(db)
    if user is None:
        logger.info("Demo start rejected: no free pool account")
        raise HTTPException(
            status_code=503,
            detail="The demo is busy right now — try again in a few minutes.",
        )
    logger.info("Demo started on pool account %s", user.username)
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

    now = utc_now()
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
                KaraokeSession.expires_at > utc_now(),
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
            detail="Your demo session has ended — press Try it live to start a new one.",
        )

    session_count = (
        db.query(func.count(DbJob.id))
        .filter(
            DbJob.session_id == session_id,
            DbJob.status.notin_(UNCOUNTED_JOB_STATUSES),
        )
        .scalar()
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

    cutoff = utc_now() - timedelta(hours=24)
    daily_count = (
        db.query(func.count(DbJob.id))
        .join(KaraokeSession, KaraokeSession.session_id == DbJob.session_id)
        .join(User, User.id == KaraokeSession.host_user_id)
        .filter(
            User.is_demo.is_(True),
            DbJob.created_at >= cutoff,
            DbJob.status.notin_(UNCOUNTED_JOB_STATUSES),
        )
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
