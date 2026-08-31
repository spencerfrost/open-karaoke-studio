"""Turn service - whose turn it is, and the three ways that changes.

The handoff screen between songs answers one question: *whose turn is it, and do
they have a song?* This is the only place that question is answered. The screen
renders what `compute_turn` returns; it never decides.

**The turn is derived, not stored.** There is no `current_turn` column. It is a
pure function of the queue sort (`queue_ordering.get_ordered_queue_items`) plus
the roster, so it cannot go stale against the order that actually drives
playback - which a stored pointer would, every time a lap is rewritten.

"The queue is empty" is therefore not a state. It is one reading of the same
question: it is Sarah's turn with nothing in her slot.

See docs/plans/2026-08-29-handoff-screen.md.
"""

import logging
from datetime import datetime
from typing import List, NamedTuple, Optional

from app.db.models import (
    KaraokeQueueItem,
    KaraokeSession,
    SessionPerformer,
    SessionPlaybackState,
)
from app.services import queue_ordering
from app.services.roster_service import mark_active
from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Nobody has a song queued, but the circle still knows who is up.
KIND_EMPTY_SEAT = "empty_seat"
# The turn belongs to a queued item.
KIND_QUEUED = "queued"
# Nobody is up: an empty roster, or append mode with an empty queue.
KIND_OPEN = "open"

# Two turns nobody stepped up for and the seat stops being offered. Any sign of
# life restores it - see `SessionPerformer.consecutive_passes`.
MAX_CONSECUTIVE_PASSES = 2


class Turn(NamedTuple):
    """Who is up next, what they are singing, and the circle behind them."""

    kind: str
    performer: Optional[SessionPerformer]
    item: Optional[KaraokeQueueItem]
    # Active performers in rotation order. Empty in append mode, where there is
    # no circle to draw.
    circle: List[SessionPerformer]

    @property
    def display_name(self) -> Optional[str]:
        """The name to put on screen.

        Falls back to the queue row's `singer_name` for items that predate the
        roster and never got a `performer_id` backfilled.
        """
        if self.performer is not None:
            return self.performer.name
        if self.item is not None:
            return self.item.singer_name
        return None


def _due_lap(performer: SessionPerformer, current_lap: int) -> int:
    """The lap this performer's next turn belongs to.

    The same `max(laps_taken, current_lap)` that `queue_ordering.compute_lap`
    uses to place a new item, and for the same reason: somebody who joined an
    hour ago and never queued still has `laps_taken` 0, and without the max they
    would out-rank every pending song for the rest of the night.
    """
    return max(performer.laps_taken, current_lap)


def get_circle(db: Session, session: KaraokeSession) -> List[SessionPerformer]:
    """Active performers in rotation order.

    Deliberately the same sort shape as
    `queue_ordering.get_ordered_queue_items` - the due lap stands in for `lap`,
    `seat` for `id` - so the circle and the queue rank people the same way.
    Nobody who has never queued jumps ahead: `first_queued_at` is null for them,
    which sorts last inside a lap, exactly as it does in the queue.
    """
    performers = (
        db.query(SessionPerformer)
        .filter(
            SessionPerformer.session_id == session.session_id,
            SessionPerformer.is_active.is_(True),
        )
        .all()
    )
    return sorted(
        performers,
        key=lambda p: (
            _due_lap(p, session.current_lap),
            p.first_queued_at or datetime.max,
            p.seat,
        ),
    )


def compute_turn(db: Session, session_id: str) -> Turn:
    """Whose turn it is right now.

    There are two candidates and one rule: **the turn goes to the head of the
    queue, unless someone in the circle is due earlier than anything queued.**
    Both are measured on the same axis - a lap number - so they cannot disagree:
    the queue candidate is its head item's `lap`, the circle candidate is that
    person's due lap.

    That second clause is what makes an empty slot a state rather than a
    component. Sarah walks up two laps into the night having queued nothing; she
    is due at lap 2 and the only pending song is Spencer's at lap 3, so it is her
    turn, with nothing in it. The screen asks her to pick instead of announcing
    that the queue is finished - and it is also how a claimed turn survives
    someone else already having a song in the list.

    Neither the person who just sang nor a late joiner needs a special case:
    `advance_to` pushed the first past the lap they sang, and `_due_lap` floors
    the second at where the room actually is.
    """
    session = (
        db.query(KaraokeSession).filter(KaraokeSession.session_id == session_id).first()
    )
    if session is None:
        return Turn(KIND_OPEN, None, None, [])

    # Append mode has no circle to ask - order is whatever the host dragged it
    # into, and an empty queue there really is just an empty queue.
    is_rotation = session.queue_order_mode == "rotation"
    circle = get_circle(db, session) if is_rotation else []

    current_item_id = (
        db.query(SessionPlaybackState.current_queue_item_id)
        .filter(SessionPlaybackState.session_id == session_id)
        .scalar()
    )
    ordered = queue_ordering.get_ordered_queue_items(db, session_id)
    upcoming = [item for item in ordered if item.id != current_item_id]
    head = upcoming[0] if upcoming else None

    if circle:
        due = circle[0]
        if head is None or _due_lap(due, session.current_lap) < head.lap:
            return Turn(KIND_EMPTY_SEAT, due, None, circle)

    if head is not None:
        return Turn(KIND_QUEUED, head.performer, head, circle)

    return Turn(KIND_OPEN, None, None, circle)


def serialize_turn(turn: Turn) -> dict:
    """The turn as it goes over REST and the WebSocket.

    Carries the item's *id* rather than the item, because the item body is
    already in `upcoming[0]` of the same payload. A third copy of the song
    serializer is exactly the drift that `build_queue_state` and
    `get_current_queue_state` are already known for.
    """
    return {
        "kind": turn.kind,
        "performerId": turn.performer.id if turn.performer else None,
        "performerName": turn.display_name,
        "itemId": turn.item.id if turn.item else None,
        "circle": [{"id": p.id, "name": p.name} for p in turn.circle],
    }


def pass_turn(session: KaraokeSession, turn: Turn) -> None:
    """Move the current turn one lap forward. Nobody adjudicates it.

    A full lap rather than back to the front: an immutable low `lap` would sort
    them first again immediately, so the room would offer the mic to someone who
    has left - and pass them over - every three minutes for the rest of the
    night. One lap of breathing room, one integer write.

    The `laps_taken` write is what covers the empty-seat case, where there is no
    item to move.
    """
    performer = turn.performer
    if performer is None:
        return

    base = turn.item.lap if turn.item is not None else performer.laps_taken
    target = max(session.current_lap, base) + 1

    if turn.item is not None:
        # The one deliberate exception to "lap is written once": a human asked,
        # or a timer expired on their behalf. Inserts still never touch it.
        turn.item.lap = target

    performer.laps_taken = max(performer.laps_taken, target)
    performer.consecutive_passes += 1
    if performer.consecutive_passes >= MAX_CONSECUTIVE_PASSES:
        performer.is_active = False
        logger.info(
            "Deactivated %r in session %s after %d consecutive passes",
            performer.name,
            session.session_id,
            performer.consecutive_passes,
        )


def claim_turn(
    db: Session,
    session: KaraokeSession,
    turn: Turn,
    claimant: SessionPerformer,
) -> None:
    """Hand the turn to `claimant`, passing whoever held it forward one lap.

    This is "That's not me": someone walked up who is not the person on screen.
    The person passed over never gets adjudicated in front of the room - the pass
    is automatic and invisible, and the claimant only says who *they* are.
    """
    mark_active(claimant)
    if turn.performer is not None and turn.performer.id == claimant.id:
        # Already theirs. Idempotent so a race between two devices settles
        # rather than double-passing someone.
        return

    pass_turn(session, turn)

    item = (
        db.query(KaraokeQueueItem)
        .filter(
            KaraokeQueueItem.session_id == session.session_id,
            KaraokeQueueItem.performer_id == claimant.id,
        )
        .order_by(KaraokeQueueItem.lap, KaraokeQueueItem.id)
        .first()
    )
    if item is not None:
        queue_ordering.bump_to_next(db, session.session_id, item.id)
        return

    # No song to pull forward, so pull the person: one below the lowest turn
    # count in the circle puts them at its head. Mirrors `bump_to_next`, which
    # already produces values below the current minimum.
    lowest = (
        db.query(func.min(SessionPerformer.laps_taken))
        .filter(
            SessionPerformer.session_id == session.session_id,
            SessionPerformer.is_active.is_(True),
            SessionPerformer.id != claimant.id,
        )
        .scalar()
    )
    claimant.laps_taken = (lowest - 1) if lowest is not None else session.current_lap
