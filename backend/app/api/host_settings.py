"""
Host settings API endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_host
from app.db.models import HostSettings, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/host-settings", tags=["host-settings"])


class HostSettingsResponse(BaseModel):
    queue_submission_mode: str
    max_songs_per_singer: int
    queue_open: bool
    session_duration_hours: int


class HostSettingsUpdateRequest(BaseModel):
    queue_submission_mode: Optional[str] = Field(None, pattern="^(instant|approval)$")
    max_songs_per_singer: Optional[int] = Field(None, ge=0, le=50)
    queue_open: Optional[bool] = None
    session_duration_hours: Optional[int] = Field(None, ge=1, le=24)


def _get_or_create_settings(db: Session, user_id: int) -> HostSettings:
    settings = db.query(HostSettings).filter(HostSettings.user_id == user_id).first()
    if not settings:
        settings = HostSettings(user_id=user_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("", response_model=HostSettingsResponse)
async def get_host_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_host),
):
    """Get the current host's settings, creating defaults if none exist."""
    settings = _get_or_create_settings(db, current_user.id)
    return HostSettingsResponse(
        queue_submission_mode=settings.queue_submission_mode,
        max_songs_per_singer=settings.max_songs_per_singer,
        queue_open=settings.queue_open,
        session_duration_hours=settings.session_duration_hours,
    )


@router.put("", response_model=HostSettingsResponse)
async def update_host_settings(
    update: HostSettingsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_host),
):
    """Update the current host's settings."""
    settings = _get_or_create_settings(db, current_user.id)

    if update.queue_submission_mode is not None:
        settings.queue_submission_mode = update.queue_submission_mode
    if update.max_songs_per_singer is not None:
        settings.max_songs_per_singer = update.max_songs_per_singer
    if update.queue_open is not None:
        settings.queue_open = update.queue_open
    if update.session_duration_hours is not None:
        settings.session_duration_hours = update.session_duration_hours

    db.commit()
    db.refresh(settings)

    logger.info("Host %s updated settings", current_user.username)

    return HostSettingsResponse(
        queue_submission_mode=settings.queue_submission_mode,
        max_songs_per_singer=settings.max_songs_per_singer,
        queue_open=settings.queue_open,
        session_duration_hours=settings.session_duration_hours,
    )
