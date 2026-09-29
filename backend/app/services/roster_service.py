"""
Roster service - the one place a name becomes a SessionPerformer.

Every entry point that turns a typed or spoken name into a roster row (phone
join, the stage picker, a pre-seeded session) goes through
resolve_or_create_performer so matching is consistent and no two rows exist
for the same person in the same session.
"""

import logging
from typing import NamedTuple, Optional

from app.db.models import SessionPerformer
from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ResolvedPerformer(NamedTuple):
    performer: SessionPerformer
    created: bool


def next_seat(db: Session, session_id: str) -> int:
    """The seat after the highest one - the end of the current lap.

    Counts inactive rows too: a removed person keeps their seat so an undo can
    put them back in it, and nobody else may be handed the same number.
    """
    highest = (
        db.query(func.max(SessionPerformer.seat))
        .filter(SessionPerformer.session_id == session_id)
        .scalar()
    )
    return 0 if highest is None else highest + 1


def mark_active(db: Session, performer: SessionPerformer) -> None:
    """Bring someone back from "Remove from rotation" by joining again.

    Anything other than the handoff screen's Undo - queueing a song under their
    name, joining from a phone, the host typing it - is a rejoin, and a rejoin
    goes to the end of the circle like any other join. Undo keeps the old seat
    instead; see turn_service.restore.
    """
    if performer.is_active:
        return
    performer.is_active = True
    performer.seat = next_seat(db, performer.session_id)
    # A fresh seat is a fresh start: turns borrowed before they left were
    # already paid for by the laps they missed.
    performer.turns_borrowed = 0


def resolve_or_create_performer(
    db: Session,
    session_id: str,
    name: str,
    device_id: Optional[str] = None,
) -> SessionPerformer:
    """Find the roster entry matching `name` in this session, or create one.

    Matching is case/whitespace-insensitive (`lower(trim(name))`); the first
    casing used for a name is what displays thereafter. Callers that need to
    know whether a new row was created (e.g. to broadcast it) should use
    `resolve_or_create_performer_verbose` instead.
    """
    return resolve_or_create_performer_verbose(
        db, session_id, name, device_id=device_id
    ).performer


def resolve_or_create_performer_verbose(
    db: Session,
    session_id: str,
    name: str,
    device_id: Optional[str] = None,
) -> ResolvedPerformer:
    """Same as `resolve_or_create_performer`, but reports whether the row is new."""
    normalized = name.strip().lower()
    if not normalized:
        raise ValueError("Performer name cannot be empty")

    existing = (
        db.query(SessionPerformer)
        .filter(
            SessionPerformer.session_id == session_id,
            SessionPerformer.normalized_name == normalized,
        )
        .first()
    )
    if existing:
        mark_active(db, existing)
        if device_id and not existing.device_id:
            existing.device_id = device_id
        return ResolvedPerformer(existing, created=False)

    seat = next_seat(db, session_id)

    performer = SessionPerformer(
        session_id=session_id,
        name=name.strip(),
        normalized_name=normalized,
        seat=seat,
        device_id=device_id,
    )
    db.add(performer)
    db.flush()
    logger.info(
        "Created roster entry %r for session %s (seat %d)",
        performer.name,
        session_id,
        seat,
    )
    return ResolvedPerformer(performer, created=True)
