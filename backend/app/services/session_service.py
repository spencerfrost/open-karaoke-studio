"""
Session lifecycle helpers shared by the REST API and the session WebSocket.

A session is retired by deactivation, never by deletion: the row, its queue items and its
playback state all survive so a host whose device dropped can reopen and resume, and so a
session's history stays intact. Stale rows are reclaimed later by
`purge_stale_sessions` in `app.api.sessions`.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import KaraokeSession, SessionDevice

logger = logging.getLogger(__name__)


def deactivate_session(db: Session, session_id: str) -> bool:
    """
    Mark a session and all of its devices inactive, keeping every row.

    Returns True if a session row was found and deactivated.
    """
    session = (
        db.query(KaraokeSession).filter(KaraokeSession.session_id == session_id).first()
    )

    if session is None:
        return False

    session.is_active = False
    db.query(SessionDevice).filter(
        SessionDevice.session_id == session_id,
        SessionDevice.is_active.is_(True),
    ).update({SessionDevice.is_active: False}, synchronize_session=False)
    db.commit()

    logger.info("Session %s deactivated (row and queue retained)", session_id)
    return True


def find_session_member(
    db: Session, session_id: str, device_id: str
) -> Optional[SessionDevice]:
    """
    Return the active SessionDevice for `device_id` in a live, unexpired session, or None.

    The device id is the session-member credential: it is minted by join-by-code (rate
    limited) and session creation, never derived from the session id. A missing session and
    a missing device both return None, so callers can't tell a wrong code from a wrong device.
    """
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
        return None
    return device
