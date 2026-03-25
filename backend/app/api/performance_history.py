"""
Performance History API endpoints for Open Karaoke Studio.

Provides read access to the persistent log of all songs performed.
"""

import logging
from typing import List, Optional

from app.api.dependencies import get_db
from app.db.models import DbSong, KaraokeSession, PerformanceHistory
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/performance-history", tags=["performance-history"])


class PerformanceHistoryItem(BaseModel):
    id: int
    song_id: Optional[str]
    song_title: Optional[str]
    artist: Optional[str]
    singer_name: str
    session_code: Optional[str]
    performed_at: str

    class Config:
        from_attributes = True


class PerformanceHistoryResponse(BaseModel):
    items: List[PerformanceHistoryItem]
    total: int
    limit: int
    offset: int


@router.get("", response_model=PerformanceHistoryResponse)
def get_performance_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get paginated list of all performances, most recent first.
    """
    total = db.query(PerformanceHistory).count()

    rows = (
        db.query(PerformanceHistory)
        .order_by(PerformanceHistory.performed_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for row in rows:
        song: Optional[DbSong] = row.song
        items.append(
            PerformanceHistoryItem(
                id=row.id,
                song_id=row.song_id,
                song_title=song.title if song else None,
                artist=song.artist if song else None,
                singer_name=row.singer_name,
                session_code=row.session_id,
                performed_at=row.performed_at.isoformat(),
            )
        )

    return PerformanceHistoryResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
