"""
Queue ordering service - the single place play order is computed and sorted.

`build_queue_state()` (REST) and `get_current_queue_state()` (WebSocket) both
call `get_ordered_queue_items` instead of each hand-rolling their own
`ORDER BY`, since those two had already drifted once. See
docs/plans/2026-08-29-roster-and-rotation.md, Stage 3b.
"""

import logging
from datetime import datetime
from typing import List, Optional

from app.db.models import (
    DbSong,
    KaraokeQueueItem,
    KaraokeSession,
    SessionPerformer,
    SessionPlaybackState,
)
from app.services import roster_service
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)


def compute_lap(
    db: Session, session: KaraokeSession, performer: SessionPerformer
) -> int:
    """The lap a newly-inserted item for `performer` belongs to.

    Their Nth pending song is their Nth turn from wherever the rotation has
    reached for them: `max(laps_taken, current_lap)` is that starting point -
    the later of the turns they have already sung and the lap the room is on.
    The `max` is what stops a late joiner (laps_taken 0, room at lap 4) from
    jumping the whole queue, and stops someone who has already sung this lap
    from queueing into it a second time.

    **Inserts never advance the rotation** - `current_lap` moves in `advance_to`,
    at play time, and nowhere else. Advancing it here instead means one person
    queueing five songs drags the room's frontier to lap 4, and the next person
    to add starts at lap 4 rather than being interleaved from lap 0.
    """
    current_item_id = (
        db.query(SessionPlaybackState.current_queue_item_id)
        .filter(SessionPlaybackState.session_id == session.session_id)
        .scalar()
    )

    # The item being sung right now is no longer pending - counting it would
    # push this performer's next song one lap further out than it belongs.
    pending = db.query(func.count(KaraokeQueueItem.id)).filter(
        KaraokeQueueItem.session_id == session.session_id,
        KaraokeQueueItem.performer_id == performer.id,
    )
    if current_item_id is not None:
        pending = pending.filter(KaraokeQueueItem.id != current_item_id)

    already_queued = pending.scalar() or 0
    return max(performer.laps_taken, session.current_lap) + already_queued


def advance_to(session: KaraokeSession, item: KaraokeQueueItem) -> None:
    """Record that playback has reached `item`, moving the rotation with it.

    `current_lap` is the lap a walk-up joins at; `laps_taken` is the turn count
    that keeps a performer who has already sung this lap out of it. Both move
    here, when a song actually starts - never on insert.
    """
    session.current_lap = max(session.current_lap, item.lap)
    if item.performer is not None:
        item.performer.laps_taken = max(item.performer.laps_taken, item.lap + 1)
        # Singing is the loudest sign of life there is: it clears any auto-pass
        # count the handoff screen ran up while this person was away from the TV.
        roster_service.mark_active(item.performer)


def enter_rotation(performer: SessionPerformer) -> None:
    """Stamp when `performer` joined the circle, the first time they queue.

    Written once and never moved, so their place in each lap is fixed for the
    night: whoever queued first stays ahead of whoever queued after them.
    """
    if performer.first_queued_at is None:
        performer.first_queued_at = datetime.utcnow()


def get_ordered_queue_items(db: Session, session_id: str) -> List[KaraokeQueueItem]:
    """All of a session's queue items, sorted per its `queue_order_mode`.

    Rotation: (lap, first_queued_at, id) - a pure sort, no row is ever mutated
    to produce it. The tie inside a lap goes to whoever entered the rotation
    first, *not* to the lower seat: seats are handed out on join, so the host
    holds seat 0 and would otherwise open every single lap.
    Append: (position, id) - today's manually-reordered behaviour.
    """
    session = (
        db.query(KaraokeSession).filter(KaraokeSession.session_id == session_id).first()
    )
    mode = session.queue_order_mode if session else "append"

    query = (
        db.query(KaraokeQueueItem)
        .options(
            joinedload(KaraokeQueueItem.song).joinedload(DbSong.album_rel),
            joinedload(KaraokeQueueItem.performer),
        )
        .filter(KaraokeQueueItem.session_id == session_id)
    )

    if mode == "rotation":
        items = query.all()
        items.sort(
            key=lambda item: (
                item.lap,
                (
                    item.performer.first_queued_at
                    if item.performer is not None
                    and item.performer.first_queued_at is not None
                    else datetime.max
                ),
                item.id,
            )
        )
        return items

    return query.order_by(KaraokeQueueItem.position, KaraokeQueueItem.id).all()


def bump_to_next(
    db: Session, session_id: str, item_id: int
) -> Optional[KaraokeQueueItem]:
    """Rewrite one item's `lap` so it sorts first among this session's pending items.

    Rotation mode only - free drag reorder already covers append mode. This is
    the one deliberate exception to "lap is written once and never recomputed":
    a human asked for it. Returns None if the item does not exist in this session.
    """
    item = (
        db.query(KaraokeQueueItem)
        .filter(
            KaraokeQueueItem.id == item_id,
            KaraokeQueueItem.session_id == session_id,
        )
        .first()
    )
    if item is None:
        return None

    min_lap = (
        db.query(func.min(KaraokeQueueItem.lap))
        .filter(
            KaraokeQueueItem.session_id == session_id,
            KaraokeQueueItem.id != item_id,
        )
        .scalar()
    )
    item.lap = (min_lap - 1) if min_lap is not None else 0
    return item
