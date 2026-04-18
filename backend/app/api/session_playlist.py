"""
Session Playlist API endpoints.

Generates a YouTube Music playlist from the songs performed in a session.
Playlist state is persisted to the Job model so it survives worker restarts.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from app.api.dependencies import get_db
from app.db.models import DbSong, KaraokeSession, PerformanceHistory
from app.db.models import Job, JobStatus
from app.repositories.job_repository import JobRepository
from app.services.youtube_music_service import YoutubeMusicService
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["session-playlist"])

PlaylistStatus = Literal["pending", "processing", "ready", "failed"]


def _playlist_job_id(session_id: str) -> str:
    return f"playlist-{session_id}"


class SessionPlaylistResponse(BaseModel):
    status: PlaylistStatus
    youtube_music_url: Optional[str] = None
    youtube_music_playlist_id: Optional[str] = None
    song_count: int = 0
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


def _job_to_response(job: Job) -> SessionPlaylistResponse:
    """Convert a Job to a SessionPlaylistResponse."""
    youtube_music_url = None
    youtube_music_playlist_id = None
    song_count = 0

    if job.status_message:
        try:
            data = json.loads(job.status_message)
            youtube_music_url = data.get("youtube_music_url")
            youtube_music_playlist_id = data.get("youtube_music_playlist_id")
            song_count = data.get("song_count", 0)
        except ValueError:
            pass

    status_map = {
        JobStatus.PENDING: "pending",
        JobStatus.PROCESSING: "processing",
        JobStatus.COMPLETED: "ready",
        JobStatus.FAILED: "failed",
    }
    playlist_status: PlaylistStatus = status_map.get(job.status, "pending")

    return SessionPlaylistResponse(
        status=playlist_status,
        youtube_music_url=youtube_music_url,
        youtube_music_playlist_id=youtube_music_playlist_id,
        song_count=song_count,
        error_message=job.error,
        created_at=job.created_at.isoformat() if job.created_at else datetime.now(timezone.utc).isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )


def _generate_playlist(session_id: str, job_id: str) -> None:
    """Background task: create a YouTube Music playlist for the session."""
    job_repo = JobRepository()
    job = job_repo.get_job(job_id)
    if not job:
        logger.error("Playlist job %s not found", job_id)
        return

    job.status = JobStatus.PROCESSING
    job_repo.update(job)

    try:
        from app.db.database import get_db_session

        with get_db_session() as db:
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
            job.status = JobStatus.FAILED
            job.error = "No songs with video IDs found in this session"
            job_repo.update(job)
            return

        date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
        name = f"Karaoke Night — {date_str}"
        description = f"Songs performed during the karaoke session on {date_str}"

        service = YoutubeMusicService()
        url, playlist_id = service.create_playlist(name, description, video_ids)

        job.status = JobStatus.COMPLETED
        job.status_message = json.dumps({
            "youtube_music_url": url,
            "youtube_music_playlist_id": playlist_id,
            "song_count": len(video_ids),
        })
        job.completed_at = datetime.now(timezone.utc)
        job_repo.update(job)

    except Exception as e:
        logger.error(
            "Failed to generate playlist for session %s: %s", session_id, e, exc_info=True
        )
        job.status = JobStatus.FAILED
        job.error = str(e)
        job_repo.update(job)


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

    job_id = _playlist_job_id(session_id)
    job_repo = JobRepository()
    existing = job_repo.get_job(job_id)

    if existing:
        return _job_to_response(existing)

    now = datetime.now(timezone.utc)
    job = Job(
        id=job_id,
        filename=job_id,
        status=JobStatus.PENDING,
        song_id=None,
        engine_type="playlist_generation",
        title=f"Playlist for session {session_id}",
        created_at=now,
    )
    try:
        job_repo.create(job)
    except Exception:
        # Concurrent request already created it — return whichever got there first
        existing = job_repo.get_job(job_id)
        if existing:
            return _job_to_response(existing)
        raise
    background_tasks.add_task(_generate_playlist, session_id, job_id)
    return _job_to_response(job_repo.get_job(job_id))


@router.get("/{session_id}/playlist", response_model=SessionPlaylistResponse)
async def get_session_playlist(session_id: str) -> SessionPlaylistResponse:
    """
    Poll for the status of the playlist generation for a session.
    """
    job_id = _playlist_job_id(session_id)
    job_repo = JobRepository()
    job = job_repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Playlist generation not started")
    return _job_to_response(job)
