"""
FastAPI router for lyrics search endpoints.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


from app.exceptions import NetworkError, ServiceError, ValidationError
from app.services.lyrics_service import LyricsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lyrics", tags=["lyrics"])


class LyricsResult(BaseModel):
    """Individual lyrics result from LRCLIB."""
    id: Optional[int] = None
    name: Optional[str] = None
    trackName: Optional[str] = None
    artistName: Optional[str] = None
    albumName: Optional[str] = None
    duration: Optional[float] = None
    instrumental: Optional[bool] = None
    plainLyrics: Optional[str] = None
    syncedLyrics: Optional[str] = None
    
    class Config:
        extra = "allow"


@router.get("/search", response_model=List[dict])
async def search_lyrics(
    track_name: str = Query(..., min_length=1, description="Song title (required)"),
    artist_name: str = Query(..., min_length=1, description="Artist name (required)"),
    album_name: Optional[str] = Query(None, description="Album name (optional, can improve results)")
):
    """
    Search for lyrics via LRCLIB.
    
    Parameters:
    - track_name: Song title (required)
    - artist_name: Artist name (required)
    - album_name: Album name (optional) - can improve search results

    Returns:
    - A JSON array with lyrics results from LRCLIB
    """
    try:
        lyrics_service = LyricsService()

        # Build query string from parameters
        query_parts = [artist_name, track_name]
        if album_name:
            query_parts.append(album_name)

        query = " ".join(query_parts)
        results = lyrics_service.search_lyrics(query)

        logger.info("Found %s lyrics results for query: %s", len(results), query)
        return results

    except ServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ConnectionError as e:
        logger.error("Lyrics connection error: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to lyrics service: {str(e)}"
        )
    except TimeoutError as e:
        logger.error("Lyrics timeout error: %s", e)
        raise HTTPException(
            status_code=504,
            detail=f"Lyrics service request timed out: {str(e)}"
        )
    except Exception as e:
        logger.error("Unexpected lyrics search error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during lyrics search: {str(e)}"
        )
