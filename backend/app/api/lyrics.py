"""
FastAPI router for lyrics endpoints.
"""

import json
import logging
from typing import List, Optional

from app.db.database import SessionLocal
from app.exceptions import ServiceError
from app.repositories.song_repository import SongRepository
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

MIN_ALIGNMENT_SCORE = 0.5


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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Lyrics search endpoints (external providers — no DB writes)
# ============================================================================


@router.get("/search", response_model=List[dict])
async def search_lyrics(
    track_name: str = Query(..., min_length=1, description="Song title (required)"),
    artist_name: str = Query(..., min_length=1, description="Artist name (required)"),
    album_name: Optional[str] = Query(None, description="Album name (optional)"),
):
    """Search for lyrics via LRCLIB."""
    try:
        lyrics_service = LyricsService()
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
        raise HTTPException(status_code=503, detail=f"Failed to connect to lyrics service: {e}")
    except TimeoutError as e:
        logger.error("Lyrics timeout error: %s", e)
        raise HTTPException(status_code=504, detail=f"Lyrics service request timed out: {e}")
    except Exception as e:
        logger.error("Unexpected lyrics search error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error during lyrics search: {e}")


@router.get("/search-synced", response_model=List[dict])
async def search_lyrics_synced(
    track_name: str = Query(..., min_length=1, description="Song title (required)"),
    artist_name: str = Query(..., min_length=1, description="Artist name (required)"),
    album_name: Optional[str] = Query(None, description="Album name (optional)"),
):
    """Search for lyrics via syncedlyrics library."""
    try:
        service = SyncedLyricsService()
        params = {"track_name": track_name, "artist_name": artist_name}
        if album_name:
            params["album_name"] = album_name
        results = service.search_lyrics_structured(params)
        logger.info("Found %s syncedlyrics results for: %s - %s", len(results), artist_name, track_name)
        return results
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Unexpected syncedlyrics search error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error during syncedlyrics search: {e}")


# ============================================================================
# Song lyrics CRUD
# ============================================================================


@router.get("/songs/{song_id}", response_model=dict)
async def get_song_lyrics(song_id: str, db: Session = Depends(get_db)):
    """Get the current lyrics for a song (plain, synced, and whether alignment exists)."""
    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")
    return {
        "plainLyrics": song.plain_lyrics,
        "syncedLyrics": song.synced_lyrics,
        "hasAlignment": song.word_synced_lyrics is not None,
    }


@router.post("/songs/{song_id}", response_model=dict, status_code=200)
async def update_song_lyrics(
    song_id: str,
    type: str = Query(..., description="Lyrics type: 'plain' or 'synced'"),
    db: Session = Depends(get_db),
    body: dict = None,
):
    """Update plain or synced lyrics for a song."""
    if type not in ("plain", "synced"):
        raise HTTPException(status_code=400, detail="type must be 'plain' or 'synced'")
    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")
    if body is None:
        raise HTTPException(status_code=422, detail="Request body required with 'content' field")
    content = body.get("content")
    if type == "plain":
        song.plain_lyrics = content or None
    else:
        song.synced_lyrics = content or None
    db.commit()
    return {"plainLyrics": song.plain_lyrics, "syncedLyrics": song.synced_lyrics}


@router.delete("/songs/{song_id}/{type}", status_code=204)
async def clear_song_lyrics(song_id: str, type: str, db: Session = Depends(get_db)):
    """Clear plain, synced, or word_synced lyrics for a song."""
    if type not in ("plain", "synced", "word_synced"):
        raise HTTPException(status_code=400, detail="type must be 'plain', 'synced', or 'word_synced'")
    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")
    if type == "plain":
        song.plain_lyrics = None
    elif type == "synced":
        song.synced_lyrics = None
    else:
        song.word_synced_lyrics = None
    db.commit()


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
    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")
    if not song.synced_lyrics:
        raise HTTPException(status_code=404, detail=f"No synced lyrics for song: {song_id}")
    return analyze_lyrics(song.synced_lyrics, min_confidence=min_confidence)


@router.post("/songs/{song_id}/analyze/apply", response_model=dict, status_code=200)
async def apply_analysis(
    song_id: str,
    min_confidence: float = Query(0.3, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
):
    """Run section-break analysis and apply the result directly to synced_lyrics."""
    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")
    if not song.synced_lyrics:
        raise HTTPException(status_code=404, detail=f"No synced lyrics for song: {song_id}")

    result = analyze_lyrics(song.synced_lyrics, min_confidence=min_confidence)
    if not result["candidates"]:
        return {"analysis": result, "message": "No candidates found — lyrics unchanged"}

    song.synced_lyrics = result["modified_lrc"]
    db.commit()
    return {"analysis": result, "message": f"Applied {len(result['candidates'])} section breaks to synced lyrics"}


# ============================================================================
# Lyrics offset analysis endpoints
# ============================================================================


@router.get("/songs/{song_id}/analyze/offset", response_model=dict)
async def analyze_song_offset(song_id: str, db: Session = Depends(get_db)):
    """Analyze global LRC timestamp offset against the vocals audio. Read-only."""
    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")
    if not song.synced_lyrics:
        raise HTTPException(status_code=404, detail=f"No synced lyrics for song: {song_id}")

    file_service = FileService()
    vocals_path = file_service.get_vocals_path(song_id, ".mp3")
    if not vocals_path.exists():
        raise HTTPException(
            status_code=422,
            detail=f"No vocals.mp3 found for song {song_id}. Run audio separation first.",
        )
    return analyze_global_offset(song.synced_lyrics, vocals_path)


@router.post("/songs/{song_id}/analyze/offset/apply", response_model=dict, status_code=200)
async def apply_offset_correction(song_id: str, db: Session = Depends(get_db)):
    """Compute global offset and apply the corrected timestamps directly to synced_lyrics."""
    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")
    if not song.synced_lyrics:
        raise HTTPException(status_code=404, detail=f"No synced lyrics for song: {song_id}")

    file_service = FileService()
    vocals_path = file_service.get_vocals_path(song_id, ".mp3")
    if not vocals_path.exists():
        raise HTTPException(
            status_code=422,
            detail=f"No vocals.mp3 found for song {song_id}. Run audio separation first.",
        )

    result = analyze_global_offset(song.synced_lyrics, vocals_path)
    if result["estimated_offset"] is None:
        return {"analysis": result, "message": "Could not estimate offset — insufficient anchor measurements. Lyrics unchanged."}

    song.synced_lyrics = shift_lrc_timestamps(song.synced_lyrics, -result["estimated_offset"])
    db.commit()
    return {
        "analysis": result,
        "message": f"Offset {result['estimated_offset']:+.3f}s applied (confidence={result['confidence']}). Synced lyrics updated.",
    }


# ============================================================================
# Word-level alignment endpoints
# ============================================================================


@router.get("/songs/{song_id}/alignment", response_model=dict)
async def get_song_alignment(song_id: str, db: Session = Depends(get_db)):
    """Return stored word-level alignment data for this song."""
    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

    if not song.word_synced_lyrics:
        return {"alignment": None}

    try:
        alignment = json.loads(song.word_synced_lyrics)
    except Exception:
        return {"alignment": None}

    return {"alignment": alignment}


@router.post("/songs/{song_id}/align", response_model=dict, status_code=200)
async def align_song_lyrics(
    song_id: str,
    language: str = Query("en", description="BCP-47 language code for the alignment model"),
    source: Optional[str] = Query(None, description="Force source type: 'plain' or 'synced'. Defaults to synced-first."),
    db: Session = Depends(get_db),
):
    """
    Run forced alignment and store result in word_synced_lyrics.

    Tries synced lyrics first; falls back to plain. Use ?source=plain to force plain text.
    Only saves the result if mean_score >= 0.5. Returns 422 if vocals.mp3 is not present.
    """
    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

    file_service = FileService()
    vocals_path = file_service.get_vocals_path(song_id, ".mp3")
    if not vocals_path.exists():
        raise HTTPException(
            status_code=422,
            detail=f"No vocals.mp3 found for song {song_id}. Run audio separation first.",
        )

    if source == "plain":
        source_content = song.plain_lyrics
        use_plain = True
    elif source == "synced":
        source_content = song.synced_lyrics
        use_plain = False
    else:
        source_content = song.synced_lyrics
        use_plain = source_content is None
        if use_plain:
            source_content = song.plain_lyrics

    if not source_content:
        raise HTTPException(status_code=404, detail=f"No synced or plain lyrics for song: {song_id}")

    if use_plain:
        result = align_plain_lyrics_to_vocals(source_content, vocals_path, language=language)
    else:
        result = align_lyrics_to_vocals(source_content, vocals_path, language=language)

    if result is None:
        raise HTTPException(status_code=500, detail="Alignment failed — check server logs for details.")

    confident = result["mean_score"] >= MIN_ALIGNMENT_SCORE
    if confident:
        song.word_synced_lyrics = json.dumps({
            "words": result["words"],
            "language": result["language"],
            "mean_score": result["mean_score"],
            "word_count": result["word_count"],
            "line_count": result["line_count"],
            "aligned_at": result["aligned_at"],
        })
        db.commit()

    return {
        "saved": confident,
        "meanScore": result["mean_score"],
        "wordCount": result["word_count"],
        "lineCount": result["line_count"],
        "lowConfidence": not confident,
        "message": (
            f"Aligned {result['word_count']} words (mean_score={result['mean_score']:.3f}). "
            + ("Saved." if confident else "Score too low — not saved.")
        ),
    }


# ============================================================================
# Batch alignment endpoints
# ============================================================================


@router.get("/batch/align", response_model=dict)
async def batch_align_status(db: Session = Depends(get_db)):
    """
    Return library-wide alignment statistics without running any processing.
    """
    file_service = FileService()
    all_songs = SongRepository(db).fetch_all()

    total = len(all_songs)
    with_vocals = 0
    aligned = 0
    needs_alignment = 0
    no_lyrics = 0

    for song in all_songs:
        vocals_path = file_service.get_vocals_path(song.id, ".mp3")
        if not vocals_path.exists():
            continue
        with_vocals += 1

        if song.word_synced_lyrics:
            aligned += 1
        elif song.synced_lyrics or song.plain_lyrics:
            needs_alignment += 1
        else:
            no_lyrics += 1

    return {
        "total": total,
        "withVocals": with_vocals,
        "aligned": aligned,
        "needsAlignment": needs_alignment,
        "noLyrics": no_lyrics,
    }


@router.post("/batch/align", status_code=202, response_model=dict)
async def batch_align_songs(
    mode: str = Query("missing", description="'missing' = only unaligned songs, 'all' = re-run everyone"),
    language: str = Query("en", description="BCP-47 language code"),
):
    """
    Dispatch a Celery task to run forced alignment across the library.

    Returns immediately with a taskId. Poll GET /batch/align/status/{taskId}
    to check progress and retrieve results when the task completes.
    """
    from app.jobs.jobs import batch_align_lyrics

    if mode not in ("missing", "all"):
        raise HTTPException(status_code=400, detail="mode must be 'missing' or 'all'")

    task = batch_align_lyrics.delay(mode=mode, language=language)
    logger.info("Dispatched batch_align_lyrics task %s (mode=%s)", task.id, mode)
    return {"taskId": task.id, "status": "dispatched", "mode": mode, "language": language}


@router.get("/batch/align/status/{task_id}", response_model=dict)
async def batch_align_task_status(task_id: str):
    """
    Poll the status of a dispatched batch alignment task.

    States: PENDING, STARTED, SUCCESS, FAILURE
    """
    from celery.result import AsyncResult

    from app.jobs.celery_app import celery

    result = AsyncResult(task_id, app=celery)
    state = result.state

    if state == "PENDING":
        return {"taskId": task_id, "state": "PENDING"}
    if state == "STARTED":
        return {"taskId": task_id, "state": "STARTED"}
    if state == "SUCCESS":
        return {"taskId": task_id, "state": "SUCCESS", "result": result.result}
    if state == "FAILURE":
        return {"taskId": task_id, "state": "FAILURE", "error": str(result.result)}
    return {"taskId": task_id, "state": state}
