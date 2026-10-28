"""
FastAPI router for lyrics endpoints.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.dependencies import (
    RequesterContext,
    get_current_user,
    get_db,
    require_host,
    require_host_or_session_member,
)
from app.db.models import User
from app.exceptions import ServiceError
from app.jobs.lyrics_dispatch import enqueue_song_alignment, realign_hand_picked_lyrics
from app.repositories.lyrics_report_repository import LyricsReportRepository
from app.repositories.song_repository import SongRepository
from app.services.file_service import FileService
from app.services.lyrics_analysis import analyze_lyrics
from app.services.lyrics_language import whisper_language_codes
from app.services.lyrics_offset import analyze_global_offset, shift_lrc_timestamps
from app.services.lyrics_service import LyricsService
from app.services.syncedlyrics_service import SyncedLyricsService

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

    model_config = ConfigDict(extra="allow")


def _validate_alignment_source(source: Optional[str]) -> Optional[str]:
    if source not in (None, "plain", "synced"):
        raise HTTPException(
            status_code=400, detail="source must be 'plain' or 'synced'"
        )
    return source


def _validate_song_and_vocals(song_id: str, db: Session):
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

    return song


def _validate_db_alignment_request(song, source: Optional[str]) -> None:
    if source == "plain" and not song.plain_lyrics:
        raise HTTPException(
            status_code=404, detail=f"No plain lyrics for song: {song.id}"
        )
    if source == "synced" and not song.synced_lyrics:
        raise HTTPException(
            status_code=404, detail=f"No synced lyrics for song: {song.id}"
        )
    if source is None and not (song.plain_lyrics or song.synced_lyrics):
        raise HTTPException(
            status_code=404, detail=f"No synced or plain lyrics for song: {song.id}"
        )


@router.get("/languages", response_model=List[str])
def list_lyrics_languages():
    """Language codes a song can be set to: every language Whisper knows."""
    return whisper_language_codes()


# ============================================================================
# Lyrics search endpoints (external providers — no DB writes)
# ============================================================================


@router.get("/search", response_model=List[dict])
def search_lyrics(
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
        raise HTTPException(
            status_code=503, detail=f"Failed to connect to lyrics service: {e}"
        )
    except TimeoutError as e:
        logger.error("Lyrics timeout error: %s", e)
        raise HTTPException(
            status_code=504, detail=f"Lyrics service request timed out: {e}"
        )
    except Exception as e:
        logger.error("Unexpected lyrics search error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Unexpected error during lyrics search: {e}"
        )


@router.get("/search-synced", response_model=List[dict])
def search_lyrics_synced(
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
            status_code=500, detail=f"Unexpected error during syncedlyrics search: {e}"
        )


# ============================================================================
# Song lyrics CRUD
# ============================================================================


@router.get("/songs/{song_id}", response_model=dict)
def get_song_lyrics(song_id: str, db: Session = Depends(get_db)):
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
def update_song_lyrics(
    song_id: str,
    type: str = Query(..., description="Lyrics type: 'plain' or 'synced'"),
    db: Session = Depends(get_db),
    body: dict = None,
    current_user: User = Depends(get_current_user),
):
    """Update plain or synced lyrics for a song."""
    if type not in ("plain", "synced"):
        raise HTTPException(status_code=400, detail="type must be 'plain' or 'synced'")
    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")
    if body is None:
        raise HTTPException(
            status_code=422, detail="Request body required with 'content' field"
        )
    content = body.get("content")
    if type == "plain":
        song.plain_lyrics = content or None
    else:
        song.synced_lyrics = content or None
    song.word_synced_lyrics = None
    # A person chose these lyrics: automatic runs now only time them.
    song.lyrics_hand_picked_at = datetime.now(timezone.utc)
    db.commit()
    realign_hand_picked_lyrics(song)
    return {"plainLyrics": song.plain_lyrics, "syncedLyrics": song.synced_lyrics}


@router.delete("/songs/{song_id}/{type}", status_code=204)
def clear_song_lyrics(
    song_id: str,
    type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clear plain, synced, or word_synced lyrics for a song."""
    if type not in ("plain", "synced", "word_synced"):
        raise HTTPException(
            status_code=400, detail="type must be 'plain', 'synced', or 'word_synced'"
        )
    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")
    if type == "plain":
        song.plain_lyrics = None
        song.word_synced_lyrics = None
    elif type == "synced":
        song.synced_lyrics = None
        song.word_synced_lyrics = None
    else:
        song.word_synced_lyrics = None
    db.commit()


# ============================================================================
# Lyrics analysis endpoints
# ============================================================================


@router.get("/songs/{song_id}/analyze", response_model=dict)
def analyze_song_lyrics(
    song_id: str,
    min_confidence: float = Query(0.3, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
):
    """Analyze synced lyrics for section breaks. Read-only — no side effects."""
    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")
    if not song.synced_lyrics:
        raise HTTPException(
            status_code=404, detail=f"No synced lyrics for song: {song_id}"
        )
    return analyze_lyrics(song.synced_lyrics, min_confidence=min_confidence)


@router.post("/songs/{song_id}/analyze/apply", response_model=dict, status_code=200)
def apply_analysis(
    song_id: str,
    min_confidence: float = Query(0.3, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run section-break analysis and apply the result directly to synced_lyrics."""
    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")
    if not song.synced_lyrics:
        raise HTTPException(
            status_code=404, detail=f"No synced lyrics for song: {song_id}"
        )

    result = analyze_lyrics(song.synced_lyrics, min_confidence=min_confidence)
    if not result["candidates"]:
        return {"analysis": result, "message": "No candidates found — lyrics unchanged"}

    song.synced_lyrics = result["modified_lrc"]
    song.word_synced_lyrics = None
    db.commit()
    return {
        "analysis": result,
        "message": f"Applied {len(result['candidates'])} section breaks to synced lyrics",
    }


# ============================================================================
# Lyrics offset analysis endpoints
# ============================================================================


@router.get("/songs/{song_id}/analyze/offset", response_model=dict)
def analyze_song_offset(song_id: str, db: Session = Depends(get_db)):
    """Analyze global LRC timestamp offset against the vocals audio. Read-only."""
    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")
    if not song.synced_lyrics:
        raise HTTPException(
            status_code=404, detail=f"No synced lyrics for song: {song_id}"
        )

    file_service = FileService()
    vocals_path = file_service.get_vocals_path(song_id, ".mp3")
    if not vocals_path.exists():
        raise HTTPException(
            status_code=422,
            detail=f"No vocals.mp3 found for song {song_id}. Run audio separation first.",
        )
    return analyze_global_offset(song.synced_lyrics, vocals_path)


@router.post(
    "/songs/{song_id}/analyze/offset/apply", response_model=dict, status_code=200
)
def apply_offset_correction(
    song_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compute global offset and apply the corrected timestamps directly to synced_lyrics."""
    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")
    if not song.synced_lyrics:
        raise HTTPException(
            status_code=404, detail=f"No synced lyrics for song: {song_id}"
        )

    file_service = FileService()
    vocals_path = file_service.get_vocals_path(song_id, ".mp3")
    if not vocals_path.exists():
        raise HTTPException(
            status_code=422,
            detail=f"No vocals.mp3 found for song {song_id}. Run audio separation first.",
        )

    result = analyze_global_offset(song.synced_lyrics, vocals_path)
    if result["estimated_offset"] is None:
        return {
            "analysis": result,
            "message": "Could not estimate offset — insufficient anchor measurements. Lyrics unchanged.",
        }

    song.synced_lyrics = shift_lrc_timestamps(
        song.synced_lyrics, -result["estimated_offset"]
    )
    song.word_synced_lyrics = None
    db.commit()
    return {
        "analysis": result,
        "message": f"Offset {result['estimated_offset']:+.3f}s applied (confidence={result['confidence']}). Synced lyrics updated.",
    }


# ============================================================================
# Word-level alignment endpoints
# ============================================================================


@router.get("/songs/{song_id}/alignment", response_model=dict)
def get_song_alignment(song_id: str, db: Session = Depends(get_db)):
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

    if isinstance(alignment, dict):
        alignment.setdefault("instrumental_intervals", [])

    return {"alignment": alignment}


@router.post("/songs/{song_id}/align", response_model=dict, status_code=200)
def align_song_lyrics(
    song_id: str,
    language: Optional[str] = Query(
        None,
        description="Whisper language code. Defaults to the song's language, detected if unknown.",
    ),
    source: Optional[str] = Query(
        None,
        description="Only use 'synced' or 'plain' candidates. Plain lyrics are timed by ASR, not aligned.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Enqueue background lyrics alignment using stored and remote lyric candidates.

    This is the general alignment entry point. It may fetch remote lyrics candidates
    and uses the full background alignment pipeline, including offset correction for
    low-confidence synced lyrics.
    """
    source = _validate_alignment_source(source)
    song = _validate_song_and_vocals(song_id, db)
    return enqueue_song_alignment(
        song,
        include_remote=True,
        source=source,
        language=language,
    )


@router.post("/songs/{song_id}/align-db", response_model=dict, status_code=200)
def align_song_lyrics_from_database(
    song_id: str,
    language: Optional[str] = Query(
        None,
        description="Whisper language code. Defaults to the song's language, detected if unknown.",
    ),
    source: Optional[str] = Query(
        None,
        description="Only use 'synced' or 'plain' candidates. Plain lyrics are timed by ASR, not aligned.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Enqueue background lyrics alignment using only the lyrics currently stored in the database.

    This path is intended for user-pasted or manually edited lyrics and never fetches
    remote lyric candidates.
    """
    source = _validate_alignment_source(source)
    song = _validate_song_and_vocals(song_id, db)
    _validate_db_alignment_request(song, source)
    return enqueue_song_alignment(
        song,
        include_remote=False,
        source=source,
        language=language,
    )


# ============================================================================
# Lyrics reports: someone singing says the lyrics are wrong
# ============================================================================


class LyricsReportRequest(BaseModel):
    # "words": the text is wrong. "timing": the words are right but out of sync.
    kind: Literal["words", "timing"]


def _reporter_name(requester: RequesterContext) -> str:
    if requester.user is not None:
        return requester.user.display_name or requester.user.username
    device = requester.device
    if device is not None and device.display_name:
        return device.display_name
    return "Stage" if device is not None and device.device_type == "stage" else "Guest"


def _lyrics_source(song) -> Optional[str]:
    """Where the word timings on screen came from ("lrclib:1", "asr:whisperx"), if any."""
    if not song.word_synced_lyrics:
        return None
    try:
        return json.loads(song.word_synced_lyrics).get("lyrics_source")
    except (TypeError, ValueError):
        return None


def _report_to_dict(report) -> dict:
    song = report.song
    return {
        "id": report.id,
        "songId": report.song_id,
        "title": song.title if song else None,
        "artist": song.artist if song else None,
        "kind": report.kind,
        "reportCount": report.report_count,
        "reporterName": report.reporter_name,
        "createdAt": report.created_at.isoformat() if report.created_at else None,
        "lastReportedAt": (
            report.last_reported_at.isoformat() if report.last_reported_at else None
        ),
        "outcome": report.outcome,
        "resolved": report.resolved_at is not None,
        "lyricsSource": _lyrics_source(song) if song else None,
        "lyricsHandPicked": bool(song and song.lyrics_hand_picked_at is not None),
        "canRestore": bool(
            report.reported_synced_lyrics or report.reported_plain_lyrics
        ),
    }


@router.post("/songs/{song_id}/reports", response_model=dict, status_code=200)
def report_song_lyrics(
    song_id: str,
    body: LyricsReportRequest,
    db: Session = Depends(get_db),
    requester: RequesterContext = Depends(require_host_or_session_member),
):
    """
    Report that the lyrics on screen have the wrong words or are out of sync.

    The report is recorded for an admin, and alignment is queued to try a fix:
    other lyrics for "words" (the reported ones are never used again), a
    re-timing of the same words for "timing".
    """
    from app.services.lyrics_retiming import shown_lyrics_key

    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")
    words_key = shown_lyrics_key(song.synced_lyrics, song.plain_lyrics)
    if words_key is None:
        raise HTTPException(status_code=422, detail="This song has no lyrics to report")

    report = LyricsReportRepository(db).report(
        song_id=song.id,
        kind=body.kind,
        words_key=words_key,
        reporter_name=_reporter_name(requester),
        user_id=requester.user.id if requester.user else None,
        session_id=requester.session_id,
        synced_lyrics=song.synced_lyrics,
        plain_lyrics=song.plain_lyrics,
    )
    if body.kind == "words" and song.lyrics_hand_picked_at is not None:
        # Someone said the hand-picked lyrics are wrong, so other sources may replace them.
        song.lyrics_hand_picked_at = None
        db.commit()

    alignment = None
    if FileService().get_vocals_path(song.id, ".mp3").exists():
        alignment = enqueue_song_alignment(song, include_remote=True)
    logger.info(
        "Lyrics reported for song %s: %s (report %s)", song.id, body.kind, report.id
    )
    return {"report": _report_to_dict(report), "alignment": alignment}


@router.get("/reports", response_model=List[dict])
def list_lyrics_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_host),
):
    """Open lyrics reports, most recently reported first."""
    return [
        _report_to_dict(report) for report in LyricsReportRepository(db).list_open()
    ]


@router.post("/reports/{report_id}/resolve", response_model=dict, status_code=200)
def resolve_lyrics_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_host),
):
    """Mark a report as dealt with. Lyrics reported as wrong stay rejected."""
    report = LyricsReportRepository(db).resolve(report_id, user_id=current_user.id)
    if report is None:
        raise HTTPException(
            status_code=404, detail=f"Lyrics report not found: {report_id}"
        )
    return _report_to_dict(report)


@router.post("/reports/{report_id}/undo", response_model=dict, status_code=200)
def undo_lyrics_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_host),
):
    """
    The report was wrong: put back the lyrics it was about and forget it.

    The lyrics on screen when it was first reported are restored and marked
    hand-picked (an admin vouched for them), then re-timed. Deleting the
    report lifts their rejection. Reports from before lyrics were kept have
    nothing to restore; their rejection is still lifted.
    """
    reports = LyricsReportRepository(db)
    report = reports.get(report_id)
    if report is None:
        raise HTTPException(
            status_code=404, detail=f"Lyrics report not found: {report_id}"
        )
    song = SongRepository(db).fetch(report.song_id)
    restored = bool(report.reported_synced_lyrics or report.reported_plain_lyrics)
    if song is not None and restored:
        song.synced_lyrics = report.reported_synced_lyrics
        song.plain_lyrics = report.reported_plain_lyrics
        song.word_synced_lyrics = None
        song.lyrics_hand_picked_at = datetime.now(timezone.utc)
    reports.delete(report)

    alignment = None
    if song is not None:
        db.refresh(song)
        alignment = (
            realign_hand_picked_lyrics(song)
            if restored
            else (
                enqueue_song_alignment(song, include_remote=True)
                if FileService().get_vocals_path(song.id, ".mp3").exists()
                else None
            )
        )
    logger.info("Lyrics report %s undone (restored=%s)", report_id, restored)
    return {"restored": restored, "alignment": alignment}


# ============================================================================
# Batch alignment endpoints
# ============================================================================


@router.get("/batch/align", response_model=dict)
def batch_align_status(db: Session = Depends(get_db)):
    """
    Return library-wide alignment statistics without running any processing.

    `repair` counts the songs a `repair` run would queue, and `repairReasons`
    how many of them have each reason (a song can have several).
    """
    from app.db.models import DbSong
    from app.services.lyrics_repair import count_reasons, select_songs_for_alignment

    selected, with_vocals = select_songs_for_alignment(db, "all")
    needs_repair = [(song, reasons) for song, reasons in selected if reasons]

    return {
        "total": db.query(DbSong).count(),
        "withVocals": with_vocals,
        "aligned": sum(1 for song, _ in selected if song.word_synced_lyrics),
        "needsAlignment": sum(
            1
            for song, _ in selected
            if not song.word_synced_lyrics and (song.synced_lyrics or song.plain_lyrics)
        ),
        "noLyrics": sum(
            1
            for song, _ in selected
            if not (song.word_synced_lyrics or song.synced_lyrics or song.plain_lyrics)
        ),
        "repair": len(needs_repair),
        "repairReasons": count_reasons(needs_repair),
    }
