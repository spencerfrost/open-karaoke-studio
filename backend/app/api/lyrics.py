"""
FastAPI router for lyrics search endpoints.
"""

import logging
from typing import Any, Dict, List, Optional

from app.db.database import SessionLocal
from app.exceptions import NetworkError, ServiceError, ValidationError
from app.repositories.lyrics_repository import LyricsRepository
from app.repositories.song_repository import SongRepository
from app.schemas.lyrics import LyricsCreateRequest, LyricsResponse
from app.services.lyrics_analysis import analyze_lyrics
from app.services.lyrics_service import LyricsService
from app.services.syncedlyrics_service import SyncedLyricsService
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

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
    album_name: Optional[str] = Query(
        None, description="Album name (optional, can improve results)"
    ),
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
            status_code=503, detail=f"Failed to connect to lyrics service: {str(e)}"
        )
    except TimeoutError as e:
        logger.error("Lyrics timeout error: %s", e)
        raise HTTPException(
            status_code=504, detail=f"Lyrics service request timed out: {str(e)}"
        )
    except Exception as e:
        logger.error("Unexpected lyrics search error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Unexpected error during lyrics search: {str(e)}"
        )


@router.get("/search-synced", response_model=List[dict])
async def search_lyrics_synced(
    track_name: str = Query(..., min_length=1, description="Song title (required)"),
    artist_name: str = Query(..., min_length=1, description="Artist name (required)"),
    album_name: Optional[str] = Query(None, description="Album name (optional)"),
):
    """
    Search for lyrics via syncedlyrics library (testing).

    Parameters:
    - track_name: Song title (required)
    - artist_name: Artist name (required)
    - album_name: Album name (optional) - may improve results

    Returns:
    - A JSON array with lyrics results from syncedlyrics
    """
    try:
        service = SyncedLyricsService()

        # Build params dict
        params = {
            "track_name": track_name,
            "artist_name": artist_name,
        }
        if album_name:
            params["album_name"] = album_name

        results = service.search_lyrics_structured(params)

        logger.info(
            "Found %s syncedlyrics results for: %s - %s",
            len(results),
            artist_name,
            track_name,
        )
        return results

    except ServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Unexpected syncedlyrics search error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during syncedlyrics search: {str(e)}",
        )


# ============================================================================
# Lyrics version management endpoints
# ============================================================================


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _lyrics_to_response(lyrics) -> dict:
    """Convert a DbLyrics record to a response dict."""
    return {
        "id": lyrics.id,
        "songId": lyrics.song_id,
        "type": lyrics.type,
        "content": lyrics.content,
        "source": lyrics.source,
        "metadata": lyrics.metadata_,
        "isActive": lyrics.is_active,
        "createdAt": lyrics.created_at.isoformat() if lyrics.created_at else None,
        "updatedAt": lyrics.updated_at.isoformat() if lyrics.updated_at else None,
    }


@router.get("/songs/{song_id}", response_model=List[dict])
async def get_song_lyrics(song_id: str, db: Session = Depends(get_db)):
    """Get all lyrics versions for a song."""
    repo = SongRepository(db)
    if not repo.fetch(song_id):
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

    lyrics_repo = LyricsRepository(db)
    all_lyrics = lyrics_repo.get_all_lyrics(song_id)
    return [_lyrics_to_response(l) for l in all_lyrics]


@router.post("/songs/{song_id}", response_model=dict, status_code=201)
async def create_song_lyrics(
    song_id: str, request: LyricsCreateRequest, db: Session = Depends(get_db)
):
    """Add a new lyrics version for a song."""
    repo = SongRepository(db)
    if not repo.fetch(song_id):
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

    lyrics_repo = LyricsRepository(db)
    lyrics = lyrics_repo.save_lyrics(
        song_id=song_id,
        lyrics_type=request.type,
        content=request.content,
        source=request.source,
        metadata=request.metadata,
        is_active=request.isActive,
    )
    return _lyrics_to_response(lyrics)


@router.patch("/{lyrics_id}/activate", response_model=dict)
async def activate_lyrics(lyrics_id: int, db: Session = Depends(get_db)):
    """Set a specific lyrics version as active."""
    lyrics_repo = LyricsRepository(db)
    lyrics = lyrics_repo.set_active(lyrics_id)
    if not lyrics:
        raise HTTPException(status_code=404, detail=f"Lyrics not found: {lyrics_id}")
    return _lyrics_to_response(lyrics)


@router.delete("/{lyrics_id}", status_code=204)
async def delete_lyrics(lyrics_id: int, db: Session = Depends(get_db)):
    """Delete a specific lyrics version."""
    lyrics_repo = LyricsRepository(db)
    if not lyrics_repo.delete_lyrics(lyrics_id):
        raise HTTPException(status_code=404, detail=f"Lyrics not found: {lyrics_id}")


# ============================================================================
# Lyrics analysis endpoints
# ============================================================================


@router.get("/songs/{song_id}/analyze", response_model=dict)
async def analyze_song_lyrics(
    song_id: str,
    min_confidence: float = Query(0.3, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
):
    """Analyze synced lyrics for section breaks. Read-only — no side effects."""
    repo = SongRepository(db)
    if not repo.fetch(song_id):
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

    lyrics_repo = LyricsRepository(db)
    lyrics = lyrics_repo.get_active_lyrics(song_id, "synced")
    if not lyrics or not lyrics.content:
        raise HTTPException(
            status_code=404, detail=f"No active synced lyrics for song: {song_id}"
        )

    result = analyze_lyrics(lyrics.content, min_confidence=min_confidence)
    return result


@router.post("/songs/{song_id}/analyze/apply", response_model=dict, status_code=201)
async def apply_analysis(
    song_id: str,
    min_confidence: float = Query(0.3, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
):
    """Run analysis and save result as an inactive lyrics version."""
    repo = SongRepository(db)
    if not repo.fetch(song_id):
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

    lyrics_repo = LyricsRepository(db)
    lyrics = lyrics_repo.get_active_lyrics(song_id, "synced")
    if not lyrics or not lyrics.content:
        raise HTTPException(
            status_code=404, detail=f"No active synced lyrics for song: {song_id}"
        )

    result = analyze_lyrics(lyrics.content, min_confidence=min_confidence)

    if not result["candidates"]:
        return {"analysis": result, "lyrics": None, "message": "No candidates found"}

    new_lyrics = lyrics_repo.save_lyrics(
        song_id=song_id,
        lyrics_type="synced",
        content=result["modified_lrc"],
        source="analysis",
        metadata={
            "candidates": result["candidates"],
            "stats": result["stats"],
            "min_confidence": min_confidence,
        },
        is_active=False,
    )

    return {
        "analysis": result,
        "lyrics": _lyrics_to_response(new_lyrics),
        "message": f"Saved as inactive version (id={new_lyrics.id}). Use PATCH /api/lyrics/{new_lyrics.id}/activate to make it active.",
    }
