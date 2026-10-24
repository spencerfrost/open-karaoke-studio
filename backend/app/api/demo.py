"""
FastAPI router for the public live demo.

GET /api/demo says whether this server offers the demo at all (any pool
account seeded), so the entry page only shows "Try it live" where it can work.
POST /api/demo/start hands a visitor a free `is_demo` pool account with its
session already running, and returns the same payload as a normal login so the
frontend signs in with it the same way. See app.services.demo_service.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.users import LoginResponse
from app.limiter import limiter
from app.services.auth_service import create_access_token
from app.services.demo_service import (
    DEMO_TOKEN_EXPIRE_MINUTES,
    demo_enabled,
    start_demo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/demo", tags=["demo"])

# Per client IP. Every call counts, including ones that come back 503 because
# the pool is full, so this leaves room for a few "busy, try again" retries.
# The pool size and the daily download budget stay the real ceiling on what
# the demo can cost.
DEMO_START_RATE_LIMIT = "5/hour;12/day"


class DemoStatusResponse(BaseModel):
    """Whether the live demo is offered on this server."""

    enabled: bool


@router.get("", response_model=DemoStatusResponse)
async def get_demo_status(db: Session = Depends(get_db)) -> DemoStatusResponse:
    """Report whether any demo pool account exists."""
    return DemoStatusResponse(enabled=demo_enabled(db))


@router.post("/start", response_model=LoginResponse)
@limiter.limit(DEMO_START_RATE_LIMIT)
async def start_demo_session(
    request: Request, db: Session = Depends(get_db)
) -> LoginResponse:
    """Start a demo session on a free pool account and sign the visitor in."""
    try:
        user = start_demo(db)
        token = create_access_token(user, expires_minutes=DEMO_TOKEN_EXPIRE_MINUTES)
        return LoginResponse(
            success=True,
            id=str(user.id),
            display_name=user.display_name,
            token=token,
            is_admin=False,
            is_host=True,
            is_demo=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to start demo session: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start the demo")
