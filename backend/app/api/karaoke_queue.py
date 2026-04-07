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

from app.api.dependencies import get_current_user, require_host
from app.db.database import SessionLocal
from app.db.models import (
    DbSong,
    HostSettings,
    KaraokeQueueItem,
    KaraokeSession,
    PerformanceHistory,
    SessionPlaybackState,
    User,
)
from app.ws.connection_manager import SessionConnectionManager
from app.ws.queue import broadcast_queue_update, broadcast_pending_update
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
    status: str = "active"
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


class QueueStateResponse(BaseModel):
    """Response model for explicit queue state."""

    current: Optional[QueueItemResponse] = None
    upcoming: List[QueueItemResponse]
    items: List[QueueItemResponse]
    pending: List[QueueItemResponse] = []


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
        status=item.status,
        addedAt=(
            item.created_at.isoformat()
            if hasattr(item, "created_at") and item.created_at
            else None
        ),
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

    all_queue_items = (
        db.query(KaraokeQueueItem)
        .options(joinedload(KaraokeQueueItem.song).joinedload(DbSong.album_rel))
        .filter(KaraokeQueueItem.session_id == session_code)
        .order_by(KaraokeQueueItem.position, KaraokeQueueItem.id)
        .all()
    )

    pending_items = [item for item in all_queue_items if item.status == "pending" and item.song]
    queue_items = [item for item in all_queue_items if item.status != "pending"]

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

    pending_responses = [queue_item_to_response(item) for item in pending_items]

    return QueueStateResponse(
        current=current_response,
        upcoming=upcoming_responses,
        items=items,
        pending=pending_responses,
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=QueueStateResponse)
async def get_queue(
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
):
    """
    Retrieve the current karaoke queue with song details for a session.
    """
    return build_queue_state(db, session_code)


@router.post("", response_model=QueueItemResponse, status_code=201)
async def add_to_queue(
    queue_data: QueueAddRequest,
    request: Request,
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
    manager: SessionConnectionManager = Depends(get_session_manager),
):
    """
    Add a new item to the karaoke queue.
    Respects host settings: queue_open and queue_submission_mode.
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

    # Determine if the requester is the host (optional auth)
    requester_is_host = False
    try:
        from app.services.auth_service import verify_token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            payload = verify_token(auth_header[7:])
            if payload and (payload.get("is_host") or payload.get("is_admin")):
                requester_is_host = True
    except Exception:
        pass

    # Enforce host settings if session has a host user
    if karaoke_session.host_user_id:
        host_settings = (
            db.query(HostSettings)
            .filter(HostSettings.user_id == karaoke_session.host_user_id)
            .first()
        )
        if host_settings and not requester_is_host:
            if not host_settings.queue_open:
                raise HTTPException(status_code=403, detail="Queue is currently closed")

            if host_settings.max_songs_per_singer > 0:
                singer_count = (
                    db.query(KaraokeQueueItem)
                    .filter(
                        KaraokeQueueItem.session_id == session_code,
                        KaraokeQueueItem.singer_name == queue_data.singer,
                        KaraokeQueueItem.status == "active",
                    )
                    .count()
                )
                if singer_count >= host_settings.max_songs_per_singer:
                    raise HTTPException(
                        status_code=429,
                        detail=f"Singer already has {host_settings.max_songs_per_singer} song(s) in the queue",
                    )

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

    # Determine status (pending if approval mode and not host)
    item_status = "active"
    if karaoke_session.host_user_id and not requester_is_host:
        host_settings = (
            db.query(HostSettings)
            .filter(HostSettings.user_id == karaoke_session.host_user_id)
            .first()
        )
        if host_settings and host_settings.queue_submission_mode == "approval":
            item_status = "pending"

    # Get max upcoming position (exclude current loaded item and pending items)
    max_position_query = db.query(KaraokeQueueItem.position).filter(
        KaraokeQueueItem.session_id == session_code,
        KaraokeQueueItem.status == "active",
    )
    if playback_state.current_queue_item_id is not None:
        max_position_query = max_position_query.filter(
            KaraokeQueueItem.id != playback_state.current_queue_item_id
        )

    max_position = max_position_query.order_by(KaraokeQueueItem.position.desc()).first()
    new_position = (max_position[0] + 1) if max_position else 1

    # Create new queue item
    new_item = KaraokeQueueItem(
        singer_name=queue_data.singer,
        song_id=queue_data.songId,
        session_id=session_code,
        position=new_position,
        status=item_status,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    # Broadcast appropriate update
    if item_status == "pending":
        await broadcast_pending_update(manager, session_code)
    else:
        await broadcast_queue_update(manager, session_code)

    return QueueItemResponse(
        id=new_item.id,
        songId=new_item.song_id,
        singer=new_item.singer_name,
        position=new_item.position,
        status=new_item.status,
        addedAt=(
            new_item.created_at.isoformat()
            if hasattr(new_item, "created_at") and new_item.created_at
            else None
        ),
        song=song_to_info(song),
    )


@router.delete("/{item_id}")
async def remove_from_queue(
    item_id: int,
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
    manager: SessionConnectionManager = Depends(get_session_manager),
    current_user: User = Depends(require_host),
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
    current_user: User = Depends(require_host),
):
    """
    Reorder the karaoke queue.
    """
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


@router.post("/{item_id}/play", response_model=QueuePlayResponse)
async def play_queue_item(
    item_id: int,
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
    manager: SessionConnectionManager = Depends(get_session_manager),
    current_user: User = Depends(require_host),
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
            if item.song.album_id and item.song.album_rel and item.song.album_rel.cover_path
            else f"/api/songs/{item.song.id}/thumbnail"
            if item.song.thumbnail_path
            else None
        ),
        syncedLyrics=item.song.synced_lyrics,
        plainLyrics=item.song.plain_lyrics,
        singer=item.singer_name,
    )


@router.post("/{item_id}/approve")
async def approve_queue_item(
    item_id: int,
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
    manager: SessionConnectionManager = Depends(get_session_manager),
    current_user: User = Depends(require_host),
):
    """Move a pending queue item to active status."""
    item = (
        db.query(KaraokeQueueItem)
        .filter(
            KaraokeQueueItem.id == item_id,
            KaraokeQueueItem.session_id == session_code,
            KaraokeQueueItem.status == "pending",
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Pending item not found")

    item.status = "active"
    db.commit()

    await broadcast_queue_update(manager, session_code)
    await broadcast_pending_update(manager, session_code)

    return {"success": True}


@router.delete("/{item_id}/reject")
async def reject_queue_item(
    item_id: int,
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
    manager: SessionConnectionManager = Depends(get_session_manager),
    current_user: User = Depends(require_host),
):
    """Remove a pending queue item without adding it to the active queue."""
    item = (
        db.query(KaraokeQueueItem)
        .filter(
            KaraokeQueueItem.id == item_id,
            KaraokeQueueItem.session_id == session_code,
            KaraokeQueueItem.status == "pending",
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Pending item not found")

    db.delete(item)
    db.commit()

    await broadcast_pending_update(manager, session_code)

    return {"success": True}


@router.post("/skip")
async def skip_current_song(
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
    manager: SessionConnectionManager = Depends(get_session_manager),
    current_user: User = Depends(require_host),
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
