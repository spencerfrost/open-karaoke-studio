"""Turn service - whose turn it is, and everything that moves it.

Rotation is a fixed circle of seats and a pointer (`session.turn_performer_id`)
to whose turn it is. The pointer is stored, not derived: it is the only source
of truth for the turn, so nothing else can disagree with it. See
docs/plans/2026-09-25-rotation-circle.md.

`queue_ordering` is the read side - the circle, the holder, the play order.
This module answers the handoff screen's question (*whose turn is it, and do
they have a song?*) and owns every write that moves the pointer: a song
starting, skip, add performer, remove and undo. `compute_turn` runs on every
queue GET and broadcast, so it never writes.

"The queue is empty" is not a state. It is one reading of the same question:
it is Sarah's turn with nothing in her slot.
"""

import logging
from typing import List, NamedTuple, Optional

from app.db.models import (
    KaraokeQueueItem,
    KaraokeSession,
    SessionPerformer,
    SessionPlaybackState,
)
from app.services import queue_ordering
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# The pointer is on someone with nothing queued: they walk up and pick.
KIND_EMPTY_SEAT = "empty_seat"
# The turn belongs to a queued item.
KIND_QUEUED = "queued"
# Nobody is up: an empty roster, or append mode with an empty queue.
KIND_OPEN = "open"


class Turn(NamedTuple):
    """Who is up next, what they are singing, and the circle behind them."""

    kind: str
    performer: Optional[SessionPerformer]
    item: Optional[KaraokeQueueItem]
    # Active performers in seat order, starting at the holder. Empty in append
    # mode, where there is no circle to draw.
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


def _from_holder(
    circle: List[SessionPerformer], holder: Optional[SessionPerformer]
) -> List[SessionPerformer]:
    if holder is None or holder not in circle:
        return circle
    index = circle.index(holder)
    return circle[index:] + circle[:index]


def compute_turn(db: Session, session_id: str) -> Turn:
    """Whose turn it is right now.

    Rotation: a bumped song if there is one, else the pointer's performer - with
    their first song, or an empty seat if they have none. The screen names them
    and waits; nobody else's song jumps in.
    Append: the head of the queue, or open.
    """
    session = (
        db.query(KaraokeSession).filter(KaraokeSession.session_id == session_id).first()
    )
    if session is None:
        return Turn(KIND_OPEN, None, None, [])

    current_item_id = (
        db.query(SessionPlaybackState.current_queue_item_id)
        .filter(SessionPlaybackState.session_id == session_id)
        .scalar()
    )
    ordered = queue_ordering.get_ordered_queue_items(db, session_id)
    upcoming = [item for item in ordered if item.id != current_item_id]

    if session.queue_order_mode != "rotation":
        if upcoming:
            head = upcoming[0]
            return Turn(KIND_QUEUED, head.performer, head, [])
        return Turn(KIND_OPEN, None, None, [])

    circle = queue_ordering.get_circle(db, session)
    holder = queue_ordering.holder_in(db, session, circle)
    ribbon = _from_holder(circle, holder)

    # The projection already put a live bump first, and dropped one that is
    # hidden or already playing - so "first upcoming is the bumped id" is the
    # whole check.
    if (
        session.bumped_item_id is not None
        and upcoming
        and upcoming[0].id == session.bumped_item_id
    ):
        bumped = upcoming[0]
        return Turn(KIND_QUEUED, bumped.performer, bumped, ribbon)

    if holder is not None:
        theirs = next(
            (item for item in upcoming if item.performer_id == holder.id), None
        )
        if theirs is not None:
            return Turn(KIND_QUEUED, holder, theirs, ribbon)
        return Turn(KIND_EMPTY_SEAT, holder, None, ribbon)

    # No circle, but songs from rows that predate the roster.
    if upcoming:
        head = upcoming[0]
        return Turn(KIND_QUEUED, head.performer, head, ribbon)

    return Turn(KIND_OPEN, None, None, ribbon)


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


# ---------------------------------------------------------------------------
# Moving the pointer
# ---------------------------------------------------------------------------


def _arrive(
    session: KaraokeSession, circle: List[SessionPerformer], index: int
) -> Optional[SessionPerformer]:
    """Move the pointer to `circle[index]`, or past it if they owe turns.

    The only place borrowed turns are spent: the pointer steps over anyone with
    `turns_borrowed > 0`, decrementing it as it goes. Spending on arrival rather
    than at play time means a borrowed turn always costs exactly the *next*
    turn, even if the circle changes in between. Terminates because every step
    over decrements a counter.
    """
    if not circle:
        session.turn_performer_id = None
        return None

    while True:
        candidate = circle[index % len(circle)]
        if candidate.turns_borrowed > 0:
            candidate.turns_borrowed -= 1
            index += 1
            continue
        session.turn_performer_id = candidate.id
        return candidate


def advance_pointer(db: Session, session: KaraokeSession) -> None:
    """Move the turn to the next active seat, wrapping at the end of the lap."""
    circle = queue_ordering.get_circle(db, session)
    holder = queue_ordering.holder_in(db, session, circle)
    if holder is None:
        session.turn_performer_id = None
        return
    _arrive(session, circle, circle.index(holder) + 1)


def record_play(db: Session, session: KaraokeSession, item: KaraokeQueueItem) -> None:
    """Record that `item` has started. Called by `/play`, and nowhere else.

    - The holder's song (bumped or not) is their real turn: the pointer moves on.
    - Anyone else's song is a borrowed turn (model A): it counts as their next
      one, nobody else moves, and the pointer steps over them once later.
    - A bump is cleared when its song starts.

    Append mode has no circle, so there is nothing to record.
    """
    if session.queue_order_mode != "rotation":
        return

    if session.bumped_item_id == item.id:
        session.bumped_item_id = None

    performer = item.performer
    if performer is None or not performer.is_active:
        return

    holder = queue_ordering.current_holder(db, session)
    if holder is not None and holder.id == performer.id:
        advance_pointer(db, session)
    else:
        performer.turns_borrowed += 1


def skip(db: Session, session: KaraokeSession, turn: Turn) -> None:
    """ "Skip my turn": the pointer moves on. Their songs don't move, so each
    one is now effectively a lap later - no back-to-back songs.

    If the turn on screen is a bumped song, skipping it cancels the bump. When
    that song was the holder's, their turn goes too; when it was someone
    else's, the turn falls back to the holder, who hasn't had theirs yet.
    """
    holder = queue_ordering.current_holder(db, session)
    if turn.item is not None and turn.item.id == session.bumped_item_id:
        session.bumped_item_id = None
        if holder is None or turn.item.performer_id != holder.id:
            return
    advance_pointer(db, session)


def insert_at_turn(
    db: Session, session: KaraokeSession, performer: SessionPerformer
) -> None:
    """Seat `performer` at the pointer: they're up now, whoever was up is next.

    Every seat at or after the holder's moves up one - inactive rows included,
    so a removed person's undo still lands in the right place. The new seat is
    kept for the rest of the night.
    """
    circle = [p for p in queue_ordering.get_circle(db, session) if p.id != performer.id]
    holder = queue_ordering.holder_in(db, session, circle)

    performer.is_active = True
    performer.turns_borrowed = 0

    if holder is not None:
        seat = holder.seat
        others = (
            db.query(SessionPerformer)
            .filter(
                SessionPerformer.session_id == session.session_id,
                SessionPerformer.id != performer.id,
                SessionPerformer.seat >= seat,
            )
            .all()
        )
        for other in others:
            other.seat += 1
        performer.seat = seat

    session.turn_performer_id = performer.id


def remove(db: Session, session: KaraokeSession, performer: SessionPerformer) -> None:
    """ "Remove from rotation": out of the circle for the night.

    Their songs are hidden, not deleted, so undo is a flag flip. If the turn was
    theirs it moves to the next seat; a bump on one of their songs is dropped.
    """
    circle = queue_ordering.get_circle(db, session)
    holder = queue_ordering.holder_in(db, session, circle)

    performer.is_active = False

    if session.bumped_item_id is not None:
        bumped = db.get(KaraokeQueueItem, session.bumped_item_id)
        if bumped is not None and bumped.performer_id == performer.id:
            session.bumped_item_id = None

    if holder is None or holder.id != performer.id:
        return

    rest = [p for p in circle if p.id != performer.id]
    after = next((i for i, p in enumerate(rest) if p.seat > performer.seat), 0)
    _arrive(session, rest, after)


def restore(
    session: KaraokeSession, performer: SessionPerformer, point_back: bool
) -> None:
    """Undo a remove: same seat, and - if nothing has happened since - their turn.

    `point_back` is false when the turn has moved since the remove (a song
    started, someone skipped). Then they rejoin in their seat without taking a
    turn that has already gone to someone else.
    """
    performer.is_active = True
    if point_back:
        session.turn_performer_id = performer.id
