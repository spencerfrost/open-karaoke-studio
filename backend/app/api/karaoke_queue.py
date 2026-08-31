"""
Karaoke Queue API endpoints for Open Karaoke Studio FastAPI backend.

This module provides REST API endpoints for queue management:
- Get queue for a session
- Add items to queue
- Remove items from queue
- Reorder queue
- Play specific queue item
"""

import logging
from typing import Generator, List, Optional

from app.api.dependencies import (
    RequesterContext,
    require_host,
    require_host_or_session_member,
)
from app.db.database import SessionLocal
from app.db.models import (
    DbSong,
    KaraokeQueueItem,
    KaraokeSession,
    PerformanceHistory,
    SessionPlaybackState,
    User,
)
from app.services.queue_ordering import (
    advance_to,
    bump_to_next,
    compute_lap,
    enter_rotation,
    get_ordered_queue_items,
)
from app.services.roster_service import resolve_or_create_performer_verbose
from app.services.turn_service import compute_turn, serialize_turn
from app.ws.connection_manager import SessionConnectionManager
from app.ws.queue import broadcast_queue_update, broadcast_roster_update
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload, subqueryload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/karaoke-queue", tags=["queue"])


def get_session_manager(request: Request) -> SessionConnectionManager:
    """Get the shared SessionConnectionManager from app state."""
    return request.app.state.session_manager


# ============================================================================
# Pydantic Models
# ============================================================================


class SongInfo(BaseModel):
    """Song information for queue items"""

    id: str
    title: str
    artist: str
    album: Optional[str] = None
    duration: Optional[float] = None
    coverArt: Optional[str] = None
    syncedLyrics: Optional[str] = None
    plainLyrics: Optional[str] = None


class QueueItemResponse(BaseModel):
    """Response model for a queue item"""

    id: int
    songId: str
    singer: str
    position: int
    lap: int
    addedAt: Optional[str] = None
    song: SongInfo


class QueueAddRequest(BaseModel):
    """Request model for adding to queue"""

    singer: str = Field(..., min_length=1, description="Singer name")
    songId: str = Field(..., min_length=1, description="Song ID to add")


class QueueReorderRequest(BaseModel):
    """Request model for reordering queue"""

    queue: List[dict] = Field(..., description="List of {id, position} objects")


class QueuePlayResponse(BaseModel):
    """Response model for playing a queue item"""

    id: str
    title: str
    artist: str
    album: Optional[str] = None
    duration: Optional[float] = None
    coverArt: Optional[str] = None
    syncedLyrics: Optional[str] = None
    plainLyrics: Optional[str] = None
    singer: str


class TurnPerformer(BaseModel):
    """A performer as the turn payload names them."""

    id: int
    name: str


class TurnResponse(BaseModel):
    """Whose turn it is, as the handoff screen renders it.

    `itemId` points into `upcoming` rather than repeating the item: the body is
    already in the same payload, and a third copy of the song serializer is the
    drift this unit exists to avoid.
    """

    kind: str
    performerId: Optional[int] = None
    performerName: Optional[str] = None
    itemId: Optional[int] = None
    circle: List[TurnPerformer] = Field(default_factory=list)


class QueueStateResponse(BaseModel):
    """Response model for explicit queue state."""

    current: Optional[QueueItemResponse] = None
    upcoming: List[QueueItemResponse]
    items: List[QueueItemResponse]
    turn: TurnResponse


# ============================================================================
# Dependencies
# ============================================================================


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error("Database session error: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


def get_session_code(
    session_code: Optional[str] = Query(None, alias="session_code"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> str:
    """Extract session code from query param or header"""
    code = session_code or x_session_id
    if not code:
        raise HTTPException(status_code=400, detail="session_code is required")
    return code


def require_queue_access(
    session_code: str = Depends(get_session_code),
    requester: RequesterContext = Depends(require_host_or_session_member),
) -> str:
    """The session code this caller is allowed to touch.

    An account holder may address any session - hosts run them, and the
    planned performer tier is scoped by its own membership anyway. An
    anonymous session guest is confined to the session their device
    credential names.
    """
    if requester.user is None and requester.session_id != session_code:
        raise HTTPException(status_code=403, detail="Not a member of that session")
    return session_code


def require_session_owner(
    session_code: str = Depends(get_session_code),
    current_user: User = Depends(require_host),
    db: Session = Depends(get_db),
) -> KaraokeSession:
    """The session this caller may mutate - their own, or any if they're an admin."""
    session = (
        db.query(KaraokeSession)
        .filter(
            KaraokeSession.session_id == session_code,
            KaraokeSession.is_active.is_(True),
        )
        .first()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or inactive")
    if session.host_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not your session")
    return session


# ============================================================================
# Helper Functions
# ============================================================================


def song_to_info(song: DbSong) -> SongInfo:
    """Convert database song to SongInfo"""
    if song.album_id and song.album_rel and song.album_rel.cover_path:
        cover_art = f"/api/albums/{song.album_id}/cover"
    elif song.thumbnail_path:
        cover_art = f"/api/songs/{song.id}/thumbnail"
    else:
        cover_art = None
    return SongInfo(
        id=song.id,
        title=song.title,
        artist=song.artist,
        album=song.album,
        duration=song.duration,
        coverArt=cover_art,
        syncedLyrics=song.synced_lyrics,
        plainLyrics=song.plain_lyrics,
    )


def queue_item_to_response(
    item: KaraokeQueueItem,
    position_override: Optional[int] = None,
) -> QueueItemResponse:
    """Convert queue item to response model"""
    return QueueItemResponse(
        id=item.id,
        songId=item.song_id,
        singer=item.singer_name,
        position=position_override if position_override is not None else item.position,
        lap=item.lap,
        addedAt=item.created_at.isoformat() if item.created_at else None,
        song=song_to_info(item.song),
    )


def get_or_create_playback_state(
    db: Session,
    session_code: str,
) -> SessionPlaybackState:
    """Get or create persisted playback state for the session."""
    state = (
        db.query(SessionPlaybackState)
        .filter(SessionPlaybackState.session_id == session_code)
        .first()
    )
    if state:
        return state

    state = SessionPlaybackState(session_id=session_code)
    db.add(state)
    db.flush()
    return state


def reindex_upcoming_positions(
    db: Session,
    session_code: str,
    current_queue_item_id: Optional[int],
) -> None:
    """Ensure upcoming queue item positions are contiguous and start at 1."""
    query = (
        db.query(KaraokeQueueItem)
        .filter(KaraokeQueueItem.session_id == session_code)
        .order_by(KaraokeQueueItem.position, KaraokeQueueItem.id)
    )
    if current_queue_item_id is not None:
        query = query.filter(KaraokeQueueItem.id != current_queue_item_id)

    for idx, queue_item in enumerate(query.all(), start=1):
        queue_item.position = idx


def build_queue_state(db: Session, session_code: str) -> QueueStateResponse:
    """Build explicit queue state (current + upcoming)."""
    playback_state = (
        db.query(SessionPlaybackState)
        .filter(SessionPlaybackState.session_id == session_code)
        .first()
    )

    queue_items = get_ordered_queue_items(db, session_code)

    queue_items_by_id = {item.id: item for item in queue_items}

    current_item: Optional[KaraokeQueueItem] = None
    if playback_state and playback_state.current_queue_item_id:
        candidate = queue_items_by_id.get(playback_state.current_queue_item_id)
        if candidate and candidate.song:
            current_item = candidate

    upcoming_items = [
        item
        for item in queue_items
        if item.song and (current_item is None or item.id != current_item.id)
    ]

    upcoming_responses = [
        queue_item_to_response(item, position_override=idx)
        for idx, item in enumerate(upcoming_items, start=1)
    ]
    current_response = (
        queue_item_to_response(current_item, position_override=0)
        if current_item
        else None
    )

    items = [current_response] if current_response else []
    items.extend(upcoming_responses)

    return QueueStateResponse(
        current=current_response,
        upcoming=upcoming_responses,
        items=items,
        turn=TurnResponse(**serialize_turn(compute_turn(db, session_code))),
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=QueueStateResponse)
async def get_queue(
    session_code: str = Depends(require_queue_access),
    db: Session = Depends(get_db),
):
    """
    Retrieve the current karaoke queue with song details for a session.
    """
    return build_queue_state(db, session_code)


@router.post("", response_model=QueueItemResponse, status_code=201)
async def add_to_queue(
    queue_data: QueueAddRequest,
    session_code: str = Depends(require_queue_access),
    db: Session = Depends(get_db),
    manager: SessionConnectionManager = Depends(get_session_manager),
):
    """
    Add a new item to the karaoke queue.
    """
    # Verify session exists and is active
    karaoke_session = (
        db.query(KaraokeSession)
        .filter(
            KaraokeSession.session_id == session_code,
            KaraokeSession.is_active == True,
        )
        .first()
    )

    if not karaoke_session:
        raise HTTPException(status_code=404, detail="Session not found or inactive")

    # Check if song exists
    song = (
        db.query(DbSong)
        .options(joinedload(DbSong.album_rel))
        .filter(DbSong.id == queue_data.songId)
        .first()
    )
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    playback_state = get_or_create_playback_state(db, session_code)

    # Get max upcoming position (exclude the current loaded item)
    max_position_query = db.query(KaraokeQueueItem.position).filter(
        KaraokeQueueItem.session_id == session_code,
    )
    if playback_state.current_queue_item_id is not None:
        max_position_query = max_position_query.filter(
            KaraokeQueueItem.id != playback_state.current_queue_item_id
        )

    max_position = max_position_query.order_by(KaraokeQueueItem.position.desc()).first()
    new_position = (max_position[0] + 1) if max_position else 1

    try:
        performer, performer_created = resolve_or_create_performer_verbose(
            db, session_code, queue_data.singer
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    lap = compute_lap(db, karaoke_session, performer)
    enter_rotation(performer)

    # Create new queue item
    new_item = KaraokeQueueItem(
        singer_name=queue_data.singer,
        song_id=queue_data.songId,
        session_id=session_code,
        position=new_position,
        performer_id=performer.id,
        lap=lap,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    if performer_created:
        await broadcast_roster_update(manager, session_code, performer.name)

    await broadcast_queue_update(manager, session_code)

    return QueueItemResponse(
        id=new_item.id,
        songId=new_item.song_id,
        singer=new_item.singer_name,
        position=new_item.position,
        lap=new_item.lap,
        addedAt=new_item.created_at.isoformat() if new_item.created_at else None,
        song=song_to_info(song),
    )


@router.delete("/{item_id}")
async def remove_from_queue(
    item_id: int,
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
    manager: SessionConnectionManager = Depends(get_session_manager),
    session: KaraokeSession = Depends(require_session_owner),
):
    """
    Remove an item from the karaoke queue.
    """
    item = (
        db.query(KaraokeQueueItem)
        .filter(
            KaraokeQueueItem.id == item_id,
            KaraokeQueueItem.session_id == session_code,
        )
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    playback_state = get_or_create_playback_state(db, session_code)

    if playback_state.current_queue_item_id == item.id:
        playback_state.current_queue_item_id = None
        playback_state.current_song_id = None
        playback_state.is_playing = False
        playback_state.current_time = 0
        playback_state.duration = 0
        playback_state.is_ready = False

    db.delete(item)
    reindex_upcoming_positions(db, session_code, playback_state.current_queue_item_id)

    db.commit()

    # Broadcast queue update
    await broadcast_queue_update(manager, session_code)

    return {"success": True}


@router.put("/reorder")
async def reorder_queue(
    reorder_data: QueueReorderRequest,
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
    manager: SessionConnectionManager = Depends(get_session_manager),
    session: KaraokeSession = Depends(require_session_owner),
):
    """
    Reorder the karaoke queue.

    Free reordering only makes sense in append mode - in rotation mode the next
    add would immediately undo a drag, so `Bump to next` is the only mutation
    allowed there instead. See docs/plans/2026-08-29-roster-and-rotation.md.
    """
    if session.queue_order_mode != "append":
        raise HTTPException(
            status_code=400,
            detail="Free reorder is only available in append mode - use bump instead",
        )

    playback_state = get_or_create_playback_state(db, session_code)

    for item in reorder_data.queue:
        queue_item = (
            db.query(KaraokeQueueItem)
            .filter(
                KaraokeQueueItem.id == item["id"],
                KaraokeQueueItem.session_id == session_code,
            )
            .first()
        )
        if queue_item and queue_item.id != playback_state.current_queue_item_id:
            queue_item.position = item["position"]

    reindex_upcoming_positions(db, session_code, playback_state.current_queue_item_id)

    db.commit()

    # Broadcast queue update
    await broadcast_queue_update(manager, session_code)

    return {"success": True}


@router.post("/{item_id}/bump", response_model=QueueItemResponse)
async def bump_queue_item(
    item_id: int,
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
    manager: SessionConnectionManager = Depends(get_session_manager),
    session: KaraokeSession = Depends(require_session_owner),
):
    """
    Move one queue item to the front of the rotation - "Grandma's leaving, let
    her sing now." Rewrites `lap` on exactly this row; every other row is
    untouched. Rotation mode only.
    """
    if session.queue_order_mode != "rotation":
        raise HTTPException(
            status_code=400,
            detail="Bump is only available in rotation mode - reorder instead",
        )

    item = bump_to_next(db, session_code, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    db.commit()
    db.refresh(item)

    await broadcast_queue_update(manager, session_code)

    return queue_item_to_response(item)


@router.post("/{item_id}/play", response_model=QueuePlayResponse)
async def play_queue_item(
    item_id: int,
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
    manager: SessionConnectionManager = Depends(get_session_manager),
    session: KaraokeSession = Depends(require_session_owner),
):
    """
    Play a specific item from the queue (moves it to the player).
    """
    item = (
        db.query(KaraokeQueueItem)
        .options(joinedload(KaraokeQueueItem.song).joinedload(DbSong.album_rel))
        .filter(
            KaraokeQueueItem.id == item_id,
            KaraokeQueueItem.session_id == session_code,
        )
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not item.song:
        raise HTTPException(status_code=404, detail="Song not found")

    playback_state = get_or_create_playback_state(db, session_code)

    # Remove previous current item from queue once a new current item is loaded
    if (
        playback_state.current_queue_item_id is not None
        and playback_state.current_queue_item_id != item.id
    ):
        previous_current_item = (
            db.query(KaraokeQueueItem)
            .filter(
                KaraokeQueueItem.id == playback_state.current_queue_item_id,
                KaraokeQueueItem.session_id == session_code,
            )
            .first()
        )
        if previous_current_item:
            history_entry = PerformanceHistory(
                song_id=previous_current_item.song_id,
                singer_name=previous_current_item.singer_name,
                session_id=session_code,
                performer_id=previous_current_item.performer_id,
                user_id=(
                    previous_current_item.performer.user_id
                    if previous_current_item.performer
                    else None
                ),
            )
            db.add(history_entry)
            db.delete(previous_current_item)

    # Mark selected queue item as the explicit current loaded item
    playback_state.current_queue_item_id = item.id
    playback_state.current_song_id = item.song.id
    playback_state.is_playing = False
    playback_state.current_time = 0
    playback_state.duration = item.song.duration or 0
    playback_state.is_ready = False

    # Starting a song is what moves the rotation - a walk-up now joins at this
    # lap, and this singer's next add lands on the one after it.
    advance_to(session, item)

    reindex_upcoming_positions(db, session_code, playback_state.current_queue_item_id)

    db.commit()

    # Broadcast queue update
    await broadcast_queue_update(manager, session_code)

    return QueuePlayResponse(
        id=item.song.id,
        title=item.song.title,
        artist=item.song.artist,
        album=item.song.album,
        duration=item.song.duration,
        coverArt=(
            f"/api/albums/{item.song.album_id}/cover"
            if item.song.album_id
            and item.song.album_rel
            and item.song.album_rel.cover_path
            else (
                f"/api/songs/{item.song.id}/thumbnail"
                if item.song.thumbnail_path
                else None
            )
        ),
        syncedLyrics=item.song.synced_lyrics,
        plainLyrics=item.song.plain_lyrics,
        singer=item.singer_name,
    )


@router.post("/skip")
async def skip_current_song(
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
    manager: SessionConnectionManager = Depends(get_session_manager),
    session: KaraokeSession = Depends(require_session_owner),
):
    """Skip the currently playing song and advance to the next in queue."""
    playback_state = get_or_create_playback_state(db, session_code)

    if playback_state.current_queue_item_id is not None:
        current_item = (
            db.query(KaraokeQueueItem)
            .filter(KaraokeQueueItem.id == playback_state.current_queue_item_id)
            .first()
        )
        if current_item:
            db.delete(current_item)

    playback_state.current_queue_item_id = None
    playback_state.current_song_id = None
    playback_state.is_playing = False
    playback_state.current_time = 0
    playback_state.duration = 0
    playback_state.is_ready = False

    reindex_upcoming_positions(db, session_code, None)
    db.commit()

    await broadcast_queue_update(manager, session_code)

    return {"success": True}
