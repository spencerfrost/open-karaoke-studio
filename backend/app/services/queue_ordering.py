"""
Queue ordering service - the single place play order is computed.

`build_queue_state()` (REST) and `get_current_queue_state()` (WebSocket) both
call `get_ordered_queue_items` instead of each hand-rolling their own
`ORDER BY`, since those two had already drifted once.

Rotation mode is a circle of performers and a pointer to whose turn it is (see
docs/plans/2026-09-25-rotation-circle.md). This module is the read side of it:
who is in the circle, who holds the turn, and the play order that follows.
Everything that *moves* the pointer lives in turn_service, which builds on
these.
"""

import logging
from typing import Dict, List, Optional

from app.db.models import (
    DbSong,
    KaraokeQueueItem,
    KaraokeSession,
    SessionPerformer,
    SessionPlaybackState,
)
from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)


def get_circle(db: Session, session: KaraokeSession) -> List[SessionPerformer]:
    """Active performers in seat order - one lap, lowest seat to highest."""
    return (
        db.query(SessionPerformer)
        .filter(
            SessionPerformer.session_id == session.session_id,
            SessionPerformer.is_active.is_(True),
        )
        .order_by(SessionPerformer.seat, SessionPerformer.id)
        .all()
    )


def holder_in(
    db: Session, session: KaraokeSession, circle: List[SessionPerformer]
) -> Optional[SessionPerformer]:
    """Who holds the turn, given the circle. Read-only.

    The pointer's performer, else the lowest active seat - which covers a new
    session, one created before the pointer existed, and a pointer whose row
    was deleted. A pointer left on someone who is no longer active (remove
    moves it, so this is defensive) resolves to the next seat after theirs.
    """
    if not circle:
        return None

    pointer = session.turn_performer_id
    if pointer is None:
        return circle[0]

    for performer in circle:
        if performer.id == pointer:
            return performer

    pointed = db.get(SessionPerformer, pointer)
    if pointed is not None:
        for performer in circle:
            if performer.seat > pointed.seat:
                return performer
    return circle[0]


def current_holder(db: Session, session: KaraokeSession) -> Optional[SessionPerformer]:
    """Whose turn the pointer says it is. Read-only."""
    return holder_in(db, session, get_circle(db, session))


def _current_item_id(db: Session, session_id: str) -> Optional[int]:
    return (
        db.query(SessionPlaybackState.current_queue_item_id)
        .filter(SessionPlaybackState.session_id == session_id)
        .scalar()
    )


def project_upcoming(
    circle: List[SessionPerformer],
    holder: Optional[SessionPerformer],
    bumped_item_id: Optional[int],
    pending: List[KaraokeQueueItem],
) -> List[KaraokeQueueItem]:
    """Rotation-mode play order for the songs that have not started yet.

    Walk the circle from the holder, lap by lap, taking each person's k-th song
    on the k-th pass. Someone with nothing queued still has their turn - it is
    just not a song, so it is not in this list (the turn says `empty_seat`).
    A bumped song goes first. The walk steps over borrowed turns exactly the way
    `turn_service.advance_pointer` spends them, on a copy, so reading the queue
    never writes.

    Pure: it touches no database. Songs of anyone outside the circle - removed
    for the night - are hidden, not deleted. Rows with no performer at all
    (from before the roster) go at the end in insert order.
    """
    songs: Dict[int, List[KaraokeQueueItem]] = {p.id: [] for p in circle}
    orphans: List[KaraokeQueueItem] = []
    bumped: Optional[KaraokeQueueItem] = None

    for item in sorted(pending, key=lambda i: i.id):
        if bumped_item_id is not None and item.id == bumped_item_id:
            bumped = item
        elif item.performer_id is None:
            orphans.append(item)
        elif item.performer_id in songs:
            songs[item.performer_id].append(item)

    if bumped is not None and bumped.performer_id not in songs:
        # A bump on someone outside the circle is hidden with the rest of
        # their songs; an orphan bump still plays first.
        if bumped.performer_id is not None:
            bumped = None

    ordered: List[KaraokeQueueItem] = []
    if bumped is not None:
        ordered.append(bumped)
    if not circle:
        return ordered + orphans

    borrowed = {p.id: p.turns_borrowed for p in circle}
    index = circle.index(holder) if holder in circle else 0
    # The pointer has already arrived at the holder, so their turn is not
    # stepped over; every later arrival is.
    arrived = True

    if bumped is not None and bumped.performer_id is not None:
        if holder is not None and bumped.performer_id == holder.id:
            # The holder's own song, bumped, is their real turn: the walk
            # continues from the next seat.
            index += 1
            arrived = False
        else:
            borrowed[bumped.performer_id] += 1

    remaining = sum(len(queue) for queue in songs.values())
    while remaining:
        performer = circle[index % len(circle)]
        index += 1
        if not arrived and borrowed[performer.id] > 0:
            borrowed[performer.id] -= 1
            continue
        arrived = False
        queue = songs[performer.id]
        if queue:
            ordered.append(queue.pop(0))
            remaining -= 1

    return ordered + orphans


def get_ordered_queue_items(db: Session, session_id: str) -> List[KaraokeQueueItem]:
    """A session's queue items in play order, per its `queue_order_mode`.

    Rotation: the item playing now (if any), then `project_upcoming`.
    Append: (position, id) - the host's manual drag order.

    The playing item is included so callers can find it by id; both queue
    payload builders split it back out as `current`.
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

    if mode != "rotation":
        return query.order_by(KaraokeQueueItem.position, KaraokeQueueItem.id).all()

    items = query.all()
    current_id = _current_item_id(db, session_id)
    current = [item for item in items if item.id == current_id]
    pending = [item for item in items if item.id != current_id]

    circle = get_circle(db, session)
    holder = holder_in(db, session, circle)
    return current + project_upcoming(circle, holder, session.bumped_item_id, pending)
