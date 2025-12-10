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

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload


from app.db.database import SessionLocal
from app.db.models import DbSong, KaraokeQueueItem, KaraokeSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/karaoke-queue", tags=["queue"])


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


# ============================================================================
# Dependencies
# ============================================================================

def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
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

async def broadcast_queue_update():
    """Broadcast queue update via FastAPI WebSocket service"""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://localhost:5124/api/broadcast/queue-update",
                timeout=1.0,
            )
    except Exception as e:
        logger.warning(f"Failed to broadcast queue update: {e}")


def song_to_info(song: DbSong) -> SongInfo:
    """Convert database song to SongInfo"""
    return SongInfo(
        id=song.id,
        title=song.title,
        artist=song.artist,
        album=song.album,
        duration=song.duration,
        coverArt=getattr(song, "cover_art_url", None),
        syncedLyrics=song.synced_lyrics,
        plainLyrics=song.plain_lyrics,
    )


def queue_item_to_response(item: KaraokeQueueItem) -> QueueItemResponse:
    """Convert queue item to response model"""
    return QueueItemResponse(
        id=item.id,
        songId=item.song_id,
        singer=item.singer_name,
        position=item.position,
        addedAt=item.created_at.isoformat() if hasattr(item, "created_at") and item.created_at else None,
        song=song_to_info(item.song),
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.get("", response_model=List[QueueItemResponse])
async def get_queue(
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
):
    """
    Retrieve the current karaoke queue with song details for a session.
    """
    queue = (
        db.query(KaraokeQueueItem)
        .options(joinedload(KaraokeQueueItem.song))
        .filter(KaraokeQueueItem.session_id == session_code)
        .order_by(KaraokeQueueItem.position)
        .all()
    )

    result = []
    for item in queue:
        if item.song:  # Ensure song exists
            result.append(queue_item_to_response(item))

    return result


@router.post("", response_model=QueueItemResponse, status_code=201)
async def add_to_queue(
    queue_data: QueueAddRequest,
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
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
    song = db.query(DbSong).filter(DbSong.id == queue_data.songId).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Get max position
    max_position = (
        db.query(KaraokeQueueItem.position)
        .filter(KaraokeQueueItem.session_id == session_code)
        .order_by(KaraokeQueueItem.position.desc())
        .first()
    )
    new_position = (max_position[0] + 1) if max_position else 1

    # Create new queue item
    new_item = KaraokeQueueItem(
        singer_name=queue_data.singer,
        song_id=queue_data.songId,
        session_id=session_code,
        position=new_position,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    # Broadcast queue update
    await broadcast_queue_update()

    return QueueItemResponse(
        id=new_item.id,
        songId=new_item.song_id,
        singer=new_item.singer_name,
        position=new_item.position,
        addedAt=new_item.created_at.isoformat() if hasattr(new_item, "created_at") and new_item.created_at else None,
        song=song_to_info(song),
    )


@router.delete("/{item_id}")
async def remove_from_queue(
    item_id: int,
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
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

    db.delete(item)
    db.commit()

    # Reindex positions to be contiguous
    remaining_items = (
        db.query(KaraokeQueueItem)
        .filter(KaraokeQueueItem.session_id == session_code)
        .order_by(KaraokeQueueItem.position)
        .all()
    )

    for idx, queue_item in enumerate(remaining_items):
        queue_item.position = idx

    db.commit()

    # Broadcast queue update
    await broadcast_queue_update()

    return {"success": True}


@router.put("/reorder")
async def reorder_queue(
    reorder_data: QueueReorderRequest,
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
):
    """
    Reorder the karaoke queue.
    """
    for item in reorder_data.queue:
        queue_item = (
            db.query(KaraokeQueueItem)
            .filter(
                KaraokeQueueItem.id == item["id"],
                KaraokeQueueItem.session_id == session_code,
            )
            .first()
        )
        if queue_item:
            queue_item.position = item["position"]

    db.commit()

    # Broadcast queue update
    await broadcast_queue_update()

    return {"success": True}


@router.post("/{item_id}/play", response_model=QueuePlayResponse)
async def play_queue_item(
    item_id: int,
    session_code: str = Depends(get_session_code),
    db: Session = Depends(get_db),
):
    """
    Play a specific item from the queue (moves it to the player).
    """
    item = (
        db.query(KaraokeQueueItem)
        .options(joinedload(KaraokeQueueItem.song))
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

    # Remove current song (position 0) if it exists
    current_song = (
        db.query(KaraokeQueueItem)
        .filter(
            KaraokeQueueItem.position == 0,
            KaraokeQueueItem.session_id == session_code,
        )
        .first()
    )

    if current_song:
        db.delete(current_song)

    # Move the played item to position 0 (current song)
    item.position = 0
    db.commit()

    # Reindex remaining positions to be contiguous (1, 2, 3, ...)
    remaining_items = (
        db.query(KaraokeQueueItem)
        .filter(
            KaraokeQueueItem.position > 0,
            KaraokeQueueItem.session_id == session_code,
        )
        .order_by(KaraokeQueueItem.position)
        .all()
    )

    for idx, queue_item in enumerate(remaining_items, start=1):
        queue_item.position = idx

    db.commit()

    # Broadcast queue update
    await broadcast_queue_update()

    return QueuePlayResponse(
        id=item.song.id,
        title=item.song.title,
        artist=item.song.artist,
        album=item.song.album,
        duration=item.song.duration,
        coverArt=getattr(item.song, "cover_art_url", None),
        syncedLyrics=item.song.synced_lyrics,
        plainLyrics=item.song.plain_lyrics,
        singer=item.singer_name,
    )
