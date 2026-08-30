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
        existing.is_active = True
        if device_id and not existing.device_id:
            existing.device_id = device_id
        return ResolvedPerformer(existing, created=False)

    seat = (
        db.query(func.count(SessionPerformer.id))
        .filter(SessionPerformer.session_id == session_id)
        .scalar()
        or 0
    )

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
