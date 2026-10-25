"""
Presence for Open Karaoke Studio - whose phone is open right now.

Each device on `/ws/session/{session_id}` reports whether its page is on screen.
The stage uses that to tell the current singer to take their phone out, and the
phone uses the turn to open its own controls when it comes back.

What goes out is keyed by **performer**, not device. Session device ids are the
credential behind the `X-Device-ID` header, so a room-wide broadcast must never
carry them; the stage only needs to ask "is this singer's phone open?", and the
singer is what the queue and turn already name.
"""

import logging
from typing import List, Optional

from app.db.database import get_db_session
from app.db.models import SessionPerformer

from .connection_manager import SessionConnectionManager

logger = logging.getLogger(__name__)


def find_linked_performer_id(session_id: str, device_id: str) -> Optional[int]:
    """The roster seat this device is linked to, or None.

    None for a device that never gave a name - the stage, usually. Membership
    itself is already settled: the socket proved it with its opening
    `authenticate` message.
    """
    with get_db_session() as db:
        return (
            db.query(SessionPerformer.id)
            .filter(
                SessionPerformer.session_id == session_id,
                SessionPerformer.device_id == device_id,
            )
            .order_by(SessionPerformer.id)
            .limit(1)
            .scalar()
        )


def build_performer_presence(
    manager: SessionConnectionManager, session_id: str
) -> List[dict]:
    """Presence for every roster seat that has a phone linked to it.

    A seat with no `device_id` (a walk-up the host typed in) is left out: there
    is no phone to ask them to open, so the stage has nothing to prompt.
    """
    with get_db_session() as db:
        linked = (
            db.query(SessionPerformer.id, SessionPerformer.device_id)
            .filter(
                SessionPerformer.session_id == session_id,
                SessionPerformer.device_id.isnot(None),
            )
            .order_by(SessionPerformer.id)
            .all()
        )

    performers = []
    for performer_id, device_id in linked:
        presence = manager.get_device_presence(session_id, device_id)
        performers.append(
            {
                "performerId": performer_id,
                "connected": presence.connected,
                "visible": presence.visible,
                "onControls": presence.on_controls,
            }
        )
    return performers


async def broadcast_presence_update(
    manager: SessionConnectionManager, session_id: str
) -> None:
    """Tell the whole session whose phones are open."""
    try:
        performers = build_performer_presence(manager, session_id)
    except Exception as e:
        logger.error(
            "Failed to build presence for session %s: %s", session_id, e, exc_info=True
        )
        return

    await manager.broadcast_to_room(
        manager.get_session_room_name(session_id),
        {"type": "presence_updated", "performers": performers},
    )
