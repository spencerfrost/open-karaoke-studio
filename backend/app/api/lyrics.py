"""
FastAPI router for lyrics search endpoints.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.db.database import SessionLocal
from app.exceptions import NetworkError, ServiceError, ValidationError
from app.repositories.lyrics_repository import LyricsRepository
from app.repositories.song_repository import SongRepository
from app.schemas.lyrics import LyricsCreateRequest, LyricsResponse
from app.services.file_service import FileService
from app.services.lyrics_analysis import analyze_lyrics
from app.services.lyrics_alignment import align_lyrics_to_vocals, align_plain_lyrics_to_vocals
from app.services.lyrics_offset import analyze_global_offset, shift_lrc_timestamps
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


# ============================================================================
# Lyrics offset analysis endpoints
# ============================================================================


@router.get("/songs/{song_id}/analyze/offset", response_model=dict)
async def analyze_song_offset(song_id: str, db: Session = Depends(get_db)):
    """Analyze global LRC timestamp offset against the vocals audio. Read-only."""
    repo = SongRepository(db)
    if not repo.fetch(song_id):
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

    lyrics_repo = LyricsRepository(db)
    lyrics = lyrics_repo.get_active_lyrics(song_id, "synced")
    if not lyrics or not lyrics.content:
        raise HTTPException(
            status_code=404, detail=f"No active synced lyrics for song: {song_id}"
        )

    file_service = FileService()
    vocals_path = file_service.get_vocals_path(song_id, ".mp3")
    if not vocals_path.exists():
        raise HTTPException(
            status_code=422,
            detail=f"No vocals.mp3 found for song {song_id}. Run audio separation first.",
        )

    result = analyze_global_offset(lyrics.content, vocals_path)
    return result


@router.post("/songs/{song_id}/analyze/offset/apply", response_model=dict, status_code=201)
async def apply_offset_correction(song_id: str, db: Session = Depends(get_db)):
    """Compute global offset and save a corrected lyrics version (inactive)."""
    repo = SongRepository(db)
    if not repo.fetch(song_id):
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

    lyrics_repo = LyricsRepository(db)
    lyrics = lyrics_repo.get_active_lyrics(song_id, "synced")
    if not lyrics or not lyrics.content:
        raise HTTPException(
            status_code=404, detail=f"No active synced lyrics for song: {song_id}"
        )

    file_service = FileService()
    vocals_path = file_service.get_vocals_path(song_id, ".mp3")
    if not vocals_path.exists():
        raise HTTPException(
            status_code=422,
            detail=f"No vocals.mp3 found for song {song_id}. Run audio separation first.",
        )

    result = analyze_global_offset(lyrics.content, vocals_path)

    if result["estimated_offset"] is None:
        return {
            "analysis": result,
            "lyrics": None,
            "message": "Could not estimate offset — insufficient anchor measurements.",
        }

    corrected_content = shift_lrc_timestamps(
        lyrics.content, -result["estimated_offset"]
    )

    new_lyrics = lyrics_repo.save_lyrics(
        song_id=song_id,
        lyrics_type="synced",
        content=corrected_content,
        source="offset_correction",
        metadata={
            "estimated_offset": result["estimated_offset"],
            "confidence": result["confidence"],
            "anchor_count": result["anchor_count"],
            "successful_anchors": result["successful_anchors"],
            "max_deviation": result["max_deviation"],
        },
        is_active=False,
    )

    return {
        "analysis": result,
        "lyrics": _lyrics_to_response(new_lyrics),
        "message": (
            f"Offset {result['estimated_offset']:+.3f}s applied (confidence={result['confidence']}). "
            f"Saved as inactive version (id={new_lyrics.id}). "
            f"Use PATCH /api/lyrics/{new_lyrics.id}/activate to make it active."
        ),
    }


# ============================================================================
# Word-level alignment endpoints
# ============================================================================

MIN_ALIGNMENT_SCORE = 0.5  # below this, word_synced row saved but not activated


@router.get("/songs/{song_id}/alignment", response_model=dict)
async def get_song_alignment(song_id: str, db: Session = Depends(get_db)):
    """
    Return stored word-level alignment data for this song.

    Returns the active word_synced lyrics row if present, otherwise
    checks for any (including low-confidence) word_synced rows.
    Returns alignment=None if alignment has not been run.
    """
    repo = SongRepository(db)
    if not repo.fetch(song_id):
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

    lyrics_repo = LyricsRepository(db)

    # Prefer active word_synced, fall back to any word_synced
    lyrics = lyrics_repo.get_active_lyrics(song_id, "word_synced")
    if not lyrics:
        all_lyrics = lyrics_repo.get_all_lyrics(song_id)
        lyrics = next((l for l in all_lyrics if l.type == "word_synced"), None)

    if not lyrics:
        return {"alignment": None}

    try:
        words = json.loads(lyrics.content)
    except Exception:
        words = []

    return {
        "lyricsId": lyrics.id,
        "isActive": lyrics.is_active,
        "metadata": lyrics.metadata_,
        "alignment": {"words": words, **(lyrics.metadata_ or {})},
    }


@router.post("/songs/{song_id}/align", response_model=dict, status_code=200)
async def align_song_lyrics(
    song_id: str,
    language: str = Query("en", description="BCP-47 language code for the alignment model"),
    db: Session = Depends(get_db),
):
    """
    Run forced alignment and store result as a word_synced lyrics row.

    Tries active synced lyrics first; falls back to active plain lyrics.
    If mean_score >= 0.5, the word_synced row is activated and the source
    row is deactivated. Otherwise it is saved as inactive with low_confidence=True.

    Returns 422 if vocals.mp3 is not present.
    """
    repo = SongRepository(db)
    if not repo.fetch(song_id):
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

    file_service = FileService()
    vocals_path = file_service.get_vocals_path(song_id, ".mp3")
    if not vocals_path.exists():
        raise HTTPException(
            status_code=422,
            detail=f"No vocals.mp3 found for song {song_id}. Run audio separation first.",
        )

    lyrics_repo = LyricsRepository(db)

    # Determine source: prefer synced, fall back to plain
    source_lyrics = lyrics_repo.get_active_lyrics(song_id, "synced")
    use_plain = source_lyrics is None
    if use_plain:
        source_lyrics = lyrics_repo.get_active_lyrics(song_id, "plain")
    if not source_lyrics or not source_lyrics.content:
        raise HTTPException(
            status_code=404,
            detail=f"No active synced or plain lyrics for song: {song_id}",
        )

    if use_plain:
        result = align_plain_lyrics_to_vocals(
            source_lyrics.content, vocals_path, language=language
        )
    else:
        result = align_lyrics_to_vocals(
            source_lyrics.content, vocals_path, language=language
        )

    if result is None:
        raise HTTPException(
            status_code=500,
            detail="Alignment failed — check server logs for details.",
        )

    confident = result["mean_score"] >= MIN_ALIGNMENT_SCORE
    word_synced_row = lyrics_repo.save_lyrics(
        song_id=song_id,
        lyrics_type="word_synced",
        content=json.dumps(result["words"]),
        source="whisperx",
        metadata={
            "language": result["language"],
            "mean_score": result["mean_score"],
            "word_count": result["word_count"],
            "line_count": result["line_count"],
            "aligned_at": result["aligned_at"],
            "source_lyrics_id": source_lyrics.id,
            "source_type": "plain" if use_plain else "synced",
            "low_confidence": not confident,
        },
        is_active=confident,
    )

    return {
        "lyricsId": word_synced_row.id,
        "isActive": word_synced_row.is_active,
        "meanScore": result["mean_score"],
        "wordCount": result["word_count"],
        "lineCount": result["line_count"],
        "lowConfidence": not confident,
        "message": (
            f"Aligned {result['word_count']} words (mean_score={result['mean_score']:.3f}). "
            + ("Activated as word_synced." if confident else "Saved as inactive (low confidence).")
        ),
    }

