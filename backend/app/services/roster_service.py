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


def mark_active(performer: SessionPerformer) -> None:
    """Any sign of life restores a seat and clears its auto-pass count.

    Unit 4's handoff screen deactivates a seat after two turns nobody stepped up
    for; the counterpart rule is that it comes back the instant that person does
    anything. Queueing, being resolved by name, claiming a turn and a song
    starting all route through here so the rule lives in one place rather than
    being remembered at four call sites.
    """
    performer.is_active = True
    performer.consecutive_passes = 0


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
        mark_active(existing)
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
