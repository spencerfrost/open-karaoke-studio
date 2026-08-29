"""
Host settings API endpoints.
"""

import logging
from typing import Optional

from app.api.dependencies import get_db, require_host
from app.db.models import HostSettings, User
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/host-settings", tags=["host-settings"])


class HostSettingsResponse(BaseModel):
    session_duration_hours: float


class HostSettingsUpdateRequest(BaseModel):
    session_duration_hours: Optional[float] = Field(None, gt=0, le=24)


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
    return HostSettingsResponse(session_duration_hours=settings.session_duration_hours)


@router.put("", response_model=HostSettingsResponse)
async def update_host_settings(
    update: HostSettingsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_host),
):
    """Update the current host's settings."""
    if current_user.is_demo:
        raise HTTPException(
            status_code=403, detail="Demo accounts can't change host settings."
        )

    settings = _get_or_create_settings(db, current_user.id)

    if update.session_duration_hours is not None:
        settings.session_duration_hours = update.session_duration_hours

    db.commit()
    db.refresh(settings)

    logger.info("Host %s updated settings", current_user.username)

    return HostSettingsResponse(session_duration_hours=settings.session_duration_hours)
