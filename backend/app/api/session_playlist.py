"""
Session Playlist API endpoints.

Generates a YouTube Music playlist from the songs performed in a session.
Playlist state is held in memory — it only needs to live long enough for
performers to grab the link/QR code after the session ends.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Literal, Optional

from app.api.dependencies import get_db
from app.db.models import DbSong, KaraokeSession, PerformanceHistory
from app.services.youtube_music_service import YoutubeMusicService
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["session-playlist"])

PlaylistStatus = Literal["pending", "processing", "ready", "failed"]

# In-memory store: session_id → playlist state dict
_playlist_state: Dict[str, dict] = {}


class SessionPlaylistResponse(BaseModel):
    status: PlaylistStatus
    youtube_music_url: Optional[str] = None
    youtube_music_playlist_id: Optional[str] = None
    song_count: int = 0
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


def _generate_playlist(session_id: str, db: Session) -> None:
    """Background task: create a YouTube Music playlist for the session."""
    state = _playlist_state[session_id]
    state["status"] = "processing"

    try:
        rows = (
            db.query(PerformanceHistory)
            .filter(PerformanceHistory.session_id == session_id)
            .order_by(PerformanceHistory.performed_at)
            .all()
        )

        video_ids = []
        for row in rows:
            song: Optional[DbSong] = row.song
            if song and song.video_id:
                video_ids.append(song.video_id)

        if not video_ids:
            state["status"] = "failed"
            state["error_message"] = "No songs with video IDs found in this session"
            return

        date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
        name = f"Karaoke Night — {date_str}"
        description = f"Songs performed during the karaoke session on {date_str}"

        service = YoutubeMusicService()
        url, playlist_id = service.create_playlist(name, description, video_ids)

        state["status"] = "ready"
        state["youtube_music_url"] = url
        state["youtube_music_playlist_id"] = playlist_id
        state["song_count"] = len(video_ids)
        state["completed_at"] = datetime.now(timezone.utc).isoformat()

    except Exception as e:
        logger.error(
            "Failed to generate playlist for session %s: %s", session_id, e, exc_info=True
        )
        state["status"] = "failed"
        state["error_message"] = str(e)
    finally:
        db.close()


@router.post("/{session_id}/playlist", status_code=202)
async def generate_session_playlist(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> SessionPlaylistResponse:
    """
    Trigger YouTube Music playlist generation for the session.
    Returns immediately; poll GET /{session_id}/playlist for status.
    """
    session = (
        db.query(KaraokeSession)
        .filter(KaraokeSession.session_id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Return existing state if already generated or in progress
    if session_id in _playlist_state:
        state = _playlist_state[session_id]
        return SessionPlaylistResponse(**state)

    now = datetime.now(timezone.utc).isoformat()
    _playlist_state[session_id] = {
        "status": "pending",
        "youtube_music_url": None,
        "youtube_music_playlist_id": None,
        "song_count": 0,
        "error_message": None,
        "created_at": now,
        "completed_at": None,
    }

    background_tasks.add_task(_generate_playlist, session_id, db)
    return SessionPlaylistResponse(**_playlist_state[session_id])


@router.get("/{session_id}/playlist", response_model=SessionPlaylistResponse)
async def get_session_playlist(session_id: str) -> SessionPlaylistResponse:
    """
    Poll for the status of the playlist generation for a session.
    """
    state = _playlist_state.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Playlist generation not started")
    return SessionPlaylistResponse(**state)
