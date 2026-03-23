"""MusicBrainz search proxy endpoint."""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.db.models.user import User
from app.services.musicbrainz_service import search_recordings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/musicbrainz", tags=["musicbrainz"])


@router.get("/search")
async def musicbrainz_search(
    query: str = Query(..., min_length=1, description="Free-text search query"),
    limit: int = Query(10, ge=1, le=25),
    current_user: User = Depends(get_current_user),
):
    """Search MusicBrainz recordings by artist/title text query."""
    try:
        results = search_recordings(query, limit=limit)
    except httpx.HTTPError as e:
        logger.warning("MusicBrainz search error: %s", e)
        raise HTTPException(status_code=502, detail="MusicBrainz search failed")

    return {"results": results}
