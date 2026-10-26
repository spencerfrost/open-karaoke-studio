"""
Songs API endpoints for Open Karaoke Studio FastAPI backend.

This module provides REST API endpoints for song management:
- List all songs with pagination and sorting
- Get song details by ID
- Create new songs
- Update song metadata
- Delete songs
- Search songs
- Get artists list
- Download audio tracks
- Get thumbnails
"""

import logging
import os
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import unquote

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from sqlalchemy import case, distinct, func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    RequesterContext,
    get_current_user,
    get_db,
    require_admin,
    require_host,
    require_host_or_session_member,
)
from app.api.validators import (
    CAMEL_TO_SNAKE_CASE,
    VALID_ARTIST_SORT_FIELDS,
    VALID_SONG_SORT_FIELDS,
    extract_lyrics_fields,
    map_fields_to_db,
    validate_direction,
    validate_sort_field,
)
from app.api.youtube import get_session_manager
from app.config import get_config
from app.db.models.artist import DbArtist, DbArtistAlias
from app.db.models.song import DbSong, in_songbook
from app.db.models.song_artist import DbSongArtist
from app.db.models.user import User
from app.repositories.song_repository import SongRepository
from app.schemas.song import (
    ArtistInfo,
    ArtistSearchResponse,
    BulkDeleteGhostsRequest,
    BulkDeleteOrphansRequest,
    FingerprintApplyRequest,
    FlaggedSong,
    MetadataAuditResponse,
    MetadataIssue,
    PaginationInfo,
    SongCreateRequest,
    SongReplaceYouTubeRequest,
    SongReprocessRequest,
    SongResponse,
    SongSearchResponse,
    SongUpdateRequest,
)
from app.schemas.youtube import SongFromYouTubeRequest, SongFromYouTubeResponse
from app.services.artist_parsing import ArtistCredit, credit_line
from app.services.batch_jobs import record_scan
from app.services.demo_service import enforce_demo_download_quota
from app.services.file_service import NON_SONG_DIRS, FileService
from app.services.lyrics_language import normalize_language
from app.services.song_artist_service import set_song_credits
from app.services.song_intake_service import (
    add_song_from_youtube,
    create_song_record,
    job_created_event,
    restart_youtube_processing,
)
from app.utils.filing import filing_letter, filing_name
from app.ws.connection_manager import SessionConnectionManager
from app.ws.jobs import broadcast_job_created

# ============================================================================
# Router & Logger
# ============================================================================
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/songs", tags=["songs"])

# ============================================================================
# Helpers
# ============================================================================


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=List[SongResponse])
async def get_songs(
    limit: Optional[int] = Query(
        None, ge=1, le=500, description="Maximum number of songs to return"
    ),
    offset: int = Query(0, ge=0, description="Number of songs to skip"),
    sort_by: str = Query("date_added", description="Field to sort by"),
    direction: str = Query("desc", description="Sort direction (asc or desc)"),
    db: Session = Depends(get_db),
):
    """
    Get all songs with optional pagination and sorting.

    - **limit**: Maximum number of songs to return (default: all)
    - **offset**: Number of songs to skip for pagination
    - **sort_by**: Field to sort by (date_added, title, artist, album, year)
    - **direction**: Sort direction (asc or desc)
    """
    # Validate sort_by and direction
    sort_by = validate_sort_field(sort_by, VALID_SONG_SORT_FIELDS)
    direction = validate_direction(direction)

    try:
        repo = SongRepository(db)
        songs = repo.fetch_all(
            sort_by=sort_by,
            direction=direction,
            limit=limit,
            offset=offset,
            songbook_only=True,
        )

        response_data = [song.to_dict() for song in songs]
        logger.debug("Returning %d songs.", len(response_data))
        return response_data

    except Exception as e:
        logger.error("Error retrieving songs: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve songs: {str(e)}"
        )


@router.get("/search", response_model=SongSearchResponse | ArtistSearchResponse)
async def search_songs(
    q: str = Query("", description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    group_by_artist: bool = Query(False, description="Group results by artist"),
    sort: str = Query("relevance", description="Sort order"),
    direction: str = Query("desc", description="Sort direction"),
    db: Session = Depends(get_db),
):
    """
    Search songs with pagination and optional artist grouping.

    - **q**: Search query (searches title, artist, album, show name)
    - **limit**: Maximum number of results (1-100)
    - **offset**: Number of results to skip
    - **group_by_artist**: If true, group results by artist
    - **sort**: Sort order (relevance, title, artist, date_added)
    - **direction**: Sort direction (asc or desc)
    """
    query = q.strip()
    if not query:
        return SongSearchResponse(
            songs=[],
            pagination=PaginationInfo(
                total=0, limit=limit, offset=offset, hasMore=False
            ),
        )

    # Validate direction
    direction = validate_direction(direction, raise_on_invalid=True)

    try:
        term = f"%{query}%"
        # Songs crediting an artist the query names, under any of their names:
        # "Dixie Chicks" finds The Chicks, "IRah" finds a song they guest on.
        credited_artist_ids = select(DbArtist.id).where(
            or_(
                DbArtist.display_name.ilike(term),
                DbArtist.id.in_(
                    select(DbArtistAlias.artist_id).where(
                        DbArtistAlias.name.ilike(term)
                    )
                ),
            )
        )
        credited_song_ids = select(DbSongArtist.song_id).where(
            or_(
                DbSongArtist.artist_id.in_(credited_artist_ids),
                DbSongArtist.credited_as.ilike(term),
            )
        )
        search_filter = or_(
            DbSong.title.ilike(term),
            DbSong.artist.ilike(term),
            DbSong.album.ilike(term),
            DbSong.show_name.ilike(term),
            DbSong.id.in_(credited_song_ids),
        )

        if group_by_artist:
            # Grouped by each song's primary artist row, not its artist text,
            # so "Jay-Z" and "JAY-Z feat. X" land together.
            artist_query = (
                db.query(
                    DbArtist.id,
                    DbArtist.display_name,
                    DbArtist.name,
                    func.count(DbSong.id).label("song_count"),
                )
                .join(DbSong, DbSong.artist_id == DbArtist.id)
                .filter(search_filter, in_songbook())
                .group_by(DbArtist.id)
                .order_by(DbArtist.display_name)
            )
            total_artists = artist_query.count()
            artist_results = artist_query.offset(offset).limit(limit).all()

            artists_data = []
            total_songs = 0
            for artist_id, display_name, name, count in artist_results:
                songs = (
                    db.query(DbSong)
                    .filter(DbSong.artist_id == artist_id, search_filter, in_songbook())
                    .limit(5)
                    .all()
                )
                total_songs += count
                artists_data.append(
                    ArtistInfo(
                        artist=display_name or name,
                        songCount=count,
                        songs=[song.to_dict() for song in songs],
                    )
                )

            return ArtistSearchResponse(
                artists=artists_data,
                totalSongs=total_songs,
                totalArtists=total_artists,
                pagination=PaginationInfo(
                    total=total_artists,
                    limit=limit,
                    offset=offset,
                    hasMore=offset + limit < total_artists,
                ),
            )
        else:
            base_query = db.query(DbSong).filter(search_filter, in_songbook())

            if sort == "relevance":
                base_query = base_query.order_by(
                    DbSong.title, DbSong.artist, DbSong.date_added.desc()
                )
            else:
                sort_field = getattr(DbSong, sort, DbSong.title)
                if direction.lower() == "desc":
                    base_query = base_query.order_by(sort_field.desc())
                else:
                    base_query = base_query.order_by(sort_field.asc())

            total_count = base_query.count()
            songs = base_query.offset(offset).limit(limit).all()

            return SongSearchResponse(
                songs=[song.to_dict() for song in songs],
                pagination=PaginationInfo(
                    total=total_count,
                    limit=limit,
                    offset=offset,
                    hasMore=offset + limit < total_count,
                ),
            )

    except Exception as e:
        logger.error("Error searching songs: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search songs: {str(e)}")


@router.get("/artists")
async def get_artists(
    search: Optional[str] = Query(None, description="Search term to filter artists"),
    limit: Optional[int] = Query(None, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    The artist list, with each artist's own and featured song counts.

    Lists an artist with a primary credit, or featured on songs by two or more
    different primary artists; a one-off guest files under the song's artist.
    A search finds every artist, by name or alias, with `listed` saying which
    the full list has.

    - **search**: Optional search term to filter artists
    - **limit**: Maximum number of artists to return (default: all)
    - **offset**: Number of artists to skip for pagination
    """
    try:
        is_primary = DbSongArtist.role == "primary"
        is_featured = DbSongArtist.role == "featured"
        own_count = func.count(case((is_primary, 1)))
        featured_count = func.count(case((is_featured, 1)))
        # The different primary artists of the songs they're featured on
        featured_with = func.count(distinct(case((is_featured, DbSong.artist_id))))
        query = (
            db.query(
                DbArtist.id,
                DbArtist.display_name,
                DbArtist.name,
                DbArtist.youtube_music_artist_id,
                own_count.label("own_count"),
                featured_count.label("featured_count"),
                featured_with.label("featured_with"),
            )
            .join(DbSongArtist, DbSongArtist.artist_id == DbArtist.id)
            # Counts only songs the songbook lists, so an artist whose only
            # song failed drops out instead of leading to an empty list.
            .join(DbSong, DbSong.id == DbSongArtist.song_id)
            .filter(in_songbook())
            .group_by(DbArtist.id)
        )

        if search and search.strip():
            term = f"%{search.strip()}%"
            aliased_ids = select(DbArtistAlias.artist_id).where(
                DbArtistAlias.name.ilike(term)
            )
            query = query.filter(
                or_(
                    DbArtist.name.ilike(term),
                    DbArtist.display_name.ilike(term),
                    DbArtist.id.in_(aliased_ids),
                )
            )
        else:
            query = query.having(or_(own_count > 0, featured_with >= 2))

        # Sorted here rather than in SQL: filing ignores leading articles and
        # accents (see app.utils.filing), and a few hundred rows is nothing.
        # Pagination has to follow the sort, so it slices afterwards.
        artists = sorted(
            (
                {
                    "id": artist_id,
                    "name": display_name or name,
                    "sortName": filing_name(display_name or name),
                    "ownCount": own,
                    "featuredCount": featured,
                    "firstLetter": filing_letter(display_name or name),
                    "youtubeMusicArtistId": ytm_id,
                    "listed": own > 0 or featured_with_count >= 2,
                }
                for (
                    artist_id,
                    display_name,
                    name,
                    ytm_id,
                    own,
                    featured,
                    featured_with_count,
                ) in query.all()
                if display_name or name
            ),
            key=lambda a: a["sortName"],
        )
        total = len(artists)
        if limit:
            artists = artists[offset : offset + limit]

        return {
            "artists": artists,
            "pagination": {
                "total": total,
                "limit": limit or total,
                "offset": offset,
                "hasMore": limit is not None and offset + limit < total,
            },
        }

    except Exception as e:
        logger.error("Error getting artists: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get artists: {str(e)}")


@router.get("/shows")
async def get_shows(
    search: Optional[str] = Query(None, description="Search term to filter shows"),
    db: Session = Depends(get_db),
):
    """Get a list of all unique musical/soundtrack show names with their song counts."""
    try:
        query = (
            db.query(DbSong.show_name, func.count(DbSong.id).label("song_count"))
            .filter(DbSong.show_name.isnot(None), DbSong.show_name != "", in_songbook())
            .group_by(DbSong.show_name)
        )

        if search and search.strip():
            query = query.filter(DbSong.show_name.ilike(f"%{search.strip()}%"))

        shows = sorted(
            (
                {
                    "name": show_name,
                    "sortName": filing_name(show_name),
                    "songCount": count,
                    "firstLetter": filing_letter(show_name),
                }
                for show_name, count in query.all()
            ),
            key=lambda show: show["sortName"],
        )

        return {"shows": shows}

    except Exception as e:
        logger.error("Error getting shows: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get shows: {str(e)}")


@router.get("/by-artist/{artist_id}")
async def get_songs_by_artist(
    artist_id: int,
    limit: int = Query(
        20, ge=1, le=500, description="Maximum number of songs to return"
    ),
    offset: int = Query(0, ge=0, description="Number of songs to skip"),
    sort: str = Query("title", description="Sort field: title, album, year, dateAdded"),
    direction: str = Query("asc", description="Sort direction: asc or desc"),
    db: Session = Depends(get_db),
):
    """
    An artist's songs: their own first, then the ones they're featured on.

    Each song carries `role`, the artist's role on it.

    - **artist_id**: The artist's id
    - **limit**: Maximum number of songs to return (1-500)
    - **offset**: Number of songs to skip
    - **sort**: Sort field within each group (title, album, year, dateAdded)
    - **direction**: Sort direction (asc or desc)
    """
    if sort not in VALID_ARTIST_SORT_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field: {sort}. Must be one of: title, album, year, dateAdded",
        )
    db_sort_field = CAMEL_TO_SNAKE_CASE.get(sort, sort)
    direction = validate_direction(direction, raise_on_invalid=True)

    artist = db.get(DbArtist, artist_id)
    if artist is None:
        raise HTTPException(status_code=404, detail="Artist not found")

    try:
        sort_column = getattr(DbSong, db_sort_field, DbSong.title)
        base_query = (
            db.query(DbSong, DbSongArtist.role)
            .join(DbSongArtist, DbSongArtist.song_id == DbSong.id)
            .filter(DbSongArtist.artist_id == artist_id, in_songbook())
            .order_by(
                # Own songs first
                case((DbSongArtist.role == "primary", 0), else_=1),
                (
                    sort_column.desc()
                    if direction.lower() == "desc"
                    else sort_column.asc()
                ),
            )
        )

        total_count = base_query.count()
        rows = base_query.offset(offset).limit(limit).all()

        return {
            "songs": [{**song.to_dict(), "role": role} for song, role in rows],
            "artist": {
                "id": artist.id,
                "name": artist.display_name or artist.name,
                "youtubeMusicArtistId": artist.youtube_music_artist_id,
            },
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "hasMore": offset + limit < total_count,
            },
        }

    except Exception as e:
        logger.error(
            "Error fetching songs for artist %s: %s", artist_id, e, exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get songs for artist: {str(e)}",
        )


@router.get("/by-show/{show_name}")
async def get_songs_by_show(
    show_name: str,
    limit: int = Query(
        20, ge=1, le=500, description="Maximum number of songs to return"
    ),
    offset: int = Query(0, ge=0, description="Number of songs to skip"),
    sort: str = Query("title", description="Sort field: title, album, year, dateAdded"),
    direction: str = Query("asc", description="Sort direction: asc or desc"),
    db: Session = Depends(get_db),
):
    """
    Get songs for a specific musical/soundtrack show, with pagination.

    - **show_name**: The show name (URL-encoded), matched exactly
    - **limit**: Maximum number of songs to return (1-500)
    - **offset**: Number of songs to skip
    - **sort**: Sort field (title, album, year, dateAdded)
    - **direction**: Sort direction (asc or desc)
    """
    show_name = unquote(show_name)

    if sort not in VALID_ARTIST_SORT_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field: {sort}. Must be one of: title, album, year, dateAdded",
        )
    db_sort_field = CAMEL_TO_SNAKE_CASE.get(sort, sort)
    direction = validate_direction(direction, raise_on_invalid=True)

    try:
        base_query = db.query(DbSong).filter(
            DbSong.show_name == show_name, in_songbook()
        )

        sort_column = getattr(DbSong, db_sort_field, DbSong.title)
        if direction.lower() == "desc":
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())

        total_count = base_query.count()
        songs = base_query.offset(offset).limit(limit).all()

        return {
            "songs": [song.to_dict() for song in songs],
            "show": show_name,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "hasMore": offset + limit < total_count,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching songs for show '{show_name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get songs for show: {str(e)}",
        )


@router.get("/by-fingerprint-status", response_model=List[SongResponse])
async def get_songs_by_fingerprint_status(
    status: str = Query(..., description="acoustid_fingerprint_status value"),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_host),
):
    """Return songs filtered by acoustid_fingerprint_status."""
    valid = {
        "not_checked",
        "matched",
        "suggested",
        "ambiguous",
        "no_match",
        "failed",
        "skipped",
    }
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"status must be one of: {valid}")
    songs = SongRepository(db).fetch_all(
        filters={"acoustid_fingerprint_status": status},
        sort_by="date_added",
        direction="asc",
        limit=limit,
        offset=offset,
    )
    return [song.to_dict() for song in songs]


@router.get("/library-audit")
async def get_library_audit(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_host),
):
    """
    Audit the karaoke library by cross-referencing filesystem directories with DB records.

    Returns three categories of discrepancies:
    - orphaned_directories: dirs on disk with no DB record
    - ghost_records: DB records with no directory on disk
    - incomplete_songs: DB records with a directory but missing key audio files
    """
    config = get_config()
    file_service = FileService()
    repo = SongRepository(db)

    disk_ids = set(file_service.get_processed_song_ids())
    all_songs = repo.fetch_all()
    db_ids = {song.id for song in all_songs}
    db_songs_by_id = {song.id: song for song in all_songs}

    # Orphaned directories: on disk, not in DB
    orphaned_directories = []
    for dir_name in sorted(disk_ids - db_ids):
        song_dir = config.LIBRARY_DIR / dir_name
        files = file_service.list_song_files(dir_name)
        total_size = sum(f.stat().st_size for f in files if f.exists())
        orphaned_directories.append(
            {
                "dir_name": dir_name,
                "files": [f.name for f in files],
                "total_size_bytes": total_size,
            }
        )

    # Ghost records: in DB, not on disk
    ghost_records = []
    for song_id in sorted(db_ids - disk_ids):
        song = db_songs_by_id[song_id]
        ghost_records.append(
            {
                "id": song.id,
                "title": song.title,
                "artist": song.artist,
                "date_added": song.date_added.isoformat() if song.date_added else None,
            }
        )

    # Incomplete songs: in DB and on disk, but missing key audio files
    key_files = ["original.mp3", "vocals.mp3", "instrumental.mp3"]
    incomplete_songs = []
    for song_id in sorted(disk_ids & db_ids):
        song_dir = config.LIBRARY_DIR / song_id
        present = {f.name for f in song_dir.iterdir() if f.is_file()}
        missing = [f for f in key_files if f not in present]
        if missing:
            song = db_songs_by_id[song_id]
            has_original = "original.mp3" in present
            # Also accept .wav variants as present
            if not has_original:
                has_original = "original.wav" in present
            incomplete_songs.append(
                {
                    "id": song.id,
                    "title": song.title,
                    "artist": song.artist,
                    "missing_files": missing,
                    "has_original": has_original,
                    "video_id": song.video_id,
                }
            )

    record_scan(
        db,
        "disk_check",
        total=len(disk_ids | db_ids),
        issues=len(orphaned_directories) + len(ghost_records) + len(incomplete_songs),
    )
    return {
        "orphaned_directories": orphaned_directories,
        "ghost_records": ghost_records,
        "incomplete_songs": incomplete_songs,
        "summary": {
            "total_directories": len(disk_ids),
            "total_db_songs": len(db_ids),
            "orphaned_count": len(orphaned_directories),
            "ghost_count": len(ghost_records),
            "incomplete_count": len(incomplete_songs),
        },
    }


# ============================================================================
# Metadata quality audit
# ============================================================================

_SUSPICIOUS_TITLE_PATTERNS = [
    "official music video",
    "official video",
    "official audio",
    "(hd)",
    "(4k)",
    "(lyrics)",
    "(lyric video)",
    "(audio)",
    "ft.",
    "- topic",
    "vevo",
]


def _check_song_metadata(song: DbSong) -> list:
    """Return a list of metadata quality issues for a single song."""
    issues = []
    title = song.title or ""
    artist = song.artist or ""

    if not title.strip():
        issues.append(
            {"type": "empty_title", "label": "Missing Title", "severity": "error"}
        )
    if not artist.strip():
        issues.append(
            {"type": "empty_artist", "label": "Missing Artist", "severity": "error"}
        )
    if artist.strip() == "Unknown Artist":
        issues.append(
            {"type": "unknown_artist", "label": "Unknown Artist", "severity": "warning"}
        )

    title_lower = title.lower()
    if any(p in title_lower for p in _SUSPICIOUS_TITLE_PATTERNS):
        issues.append(
            {
                "type": "suspicious_title",
                "label": "Raw YouTube Title",
                "severity": "warning",
            }
        )

    if len(title) > 80:
        issues.append({"type": "long_title", "label": "Long Title", "severity": "info"})

    if len(title) < 5 and len(artist) > 40:
        issues.append(
            {
                "type": "swapped_fields",
                "label": "Possibly Swapped",
                "severity": "warning",
            }
        )

    combined = f"{title} {artist}"
    if "\ufffd" in combined or any(ord(c) > 0xFFFF for c in combined):
        issues.append(
            {
                "type": "encoding_artifact",
                "label": "Encoding Issue",
                "severity": "warning",
            }
        )

    if not song.source:
        issues.append(
            {"type": "missing_source", "label": "No Source", "severity": "info"}
        )
    if song.duration is None:
        issues.append(
            {"type": "missing_duration", "label": "No Duration", "severity": "warning"}
        )
    if not song.album:
        issues.append(
            {"type": "missing_album", "label": "No Album", "severity": "info"}
        )
    if not song.plain_lyrics and not song.synced_lyrics:
        issues.append(
            {"type": "missing_lyrics", "label": "No Lyrics", "severity": "info"}
        )
    if not song.vocal_range_low and not song.vocal_range_high:
        issues.append(
            {
                "type": "missing_vocal_range",
                "label": "No Vocal Range",
                "severity": "info",
            }
        )

    return issues


@router.get("/metadata-audit", response_model=MetadataAuditResponse)
async def get_metadata_audit(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_host),
):
    """
    Scan all songs for metadata quality issues.

    Checks for missing fields, suspicious title patterns, encoding artifacts,
    and other data quality problems. Returns only songs with at least one issue.
    """
    repo = SongRepository(db)
    all_songs = repo.fetch_all()
    flagged = []
    summary: dict = defaultdict(int)

    for song in all_songs:
        issues = _check_song_metadata(song)
        if issues:
            for issue in issues:
                summary[issue["type"]] += 1
            flagged.append(
                FlaggedSong(
                    id=song.id,
                    title=song.title,
                    artist=song.artist,
                    date_added=song.date_added.isoformat() if song.date_added else None,
                    source=song.source,
                    issues=[MetadataIssue(**i) for i in issues],
                )
            )

    record_scan(db, "metadata_scan", total=len(all_songs), issues=len(flagged))
    return MetadataAuditResponse(
        flagged_songs=flagged,
        summary=dict(summary),
        total_songs_scanned=len(all_songs),
        total_flagged=len(flagged),
    )


@router.delete("/orphan/{dir_name}", status_code=200)
async def delete_orphaned_directory(
    dir_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Delete an orphaned library directory that has no corresponding DB record.
    """
    config = get_config()

    # Safety: reject any path traversal attempts and the shared artwork folders
    if (
        "/" in dir_name
        or "\\" in dir_name
        or ".." in dir_name
        or dir_name in NON_SONG_DIRS
    ):
        raise HTTPException(status_code=400, detail="Invalid directory name")

    # Confirm it's actually on disk
    song_dir = config.LIBRARY_DIR / dir_name
    if not song_dir.exists() or not song_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Directory not found: {dir_name}")

    # Confirm there is no DB record (safety check)
    repo = SongRepository(db)
    if repo.fetch(dir_name):
        raise HTTPException(
            status_code=409,
            detail=f"A DB record exists for {dir_name}. Use DELETE /api/songs/{dir_name} instead.",
        )

    file_service = FileService()
    file_service.delete_song_files(dir_name)
    logger.info("Deleted orphaned directory: %s", dir_name)
    return {"message": f"Orphaned directory '{dir_name}' deleted successfully"}


@router.delete("/orphan-bulk", status_code=200)
async def bulk_delete_orphaned_directories(
    request: BulkDeleteOrphansRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Bulk-delete multiple orphaned library directories with no corresponding DB records.
    """
    config = get_config()
    repo = SongRepository(db)
    file_service = FileService()

    deleted = 0
    skipped = 0

    for dir_name in request.dir_names:
        # Safety: reject any path traversal attempts and the shared artwork folders
        if (
            "/" in dir_name
            or "\\" in dir_name
            or ".." in dir_name
            or dir_name in NON_SONG_DIRS
        ):
            logger.warning("Bulk delete skipping invalid dir name: %r", dir_name)
            skipped += 1
            continue

        song_dir = config.LIBRARY_DIR / dir_name
        if not song_dir.exists() or not song_dir.is_dir():
            skipped += 1
            continue

        # Skip if a DB record exists (safety check)
        if repo.fetch(dir_name):
            logger.warning("Bulk delete skipping %r: DB record exists", dir_name)
            skipped += 1
            continue

        file_service.delete_song_files(dir_name)
        deleted += 1

    logger.info("Bulk orphan delete: %d deleted, %d skipped", deleted, skipped)
    return {"deleted": deleted, "skipped": skipped}


@router.delete("/ghost-bulk", status_code=200)
async def bulk_delete_ghost_records(
    request: BulkDeleteGhostsRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Bulk-delete multiple ghost DB records that have no corresponding files on disk.
    """
    repo = SongRepository(db)

    deleted = 0
    skipped = 0

    for song_id in request.song_ids:
        song = repo.fetch(song_id)
        if not song:
            skipped += 1
            continue
        repo.delete(song_id)
        deleted += 1

    logger.info("Bulk ghost delete: %d deleted, %d skipped", deleted, skipped)
    return {"deleted": deleted, "skipped": skipped}


@router.get("/duplicates")
async def get_duplicate_songs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_host),
):
    """
    Return clusters of songs that share the same case-insensitive title+artist.
    """
    repo = SongRepository(db)
    clusters = repo.find_duplicates()
    result = [
        [
            {
                "id": s.id,
                "title": s.title,
                "artist": s.artist,
                "date_added": s.date_added.isoformat() if s.date_added else None,
                "source": s.source,
            }
            for s in cluster
        ]
        for cluster in clusters
    ]
    record_scan(
        db,
        "duplicates",
        total=db.query(func.count(DbSong.id)).scalar() or 0,
        issues=len(result),
    )
    return {
        "clusters": result,
        "total_clusters": len(result),
        "total_duplicates": sum(len(c) for c in result),
    }


@router.get("/{song_id}", response_model=SongResponse)
async def get_song_details(song_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific song.
    """
    try:
        repo = SongRepository(db)
        db_song = repo.fetch(song_id)

        if not db_song:
            raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

        return db_song.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching song details: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get song details: {str(e)}"
        )


@router.post("", response_model=SongResponse, status_code=201)
async def create_song(
    song_data: SongCreateRequest,
    db: Session = Depends(get_db),
    requester: RequesterContext = Depends(require_host_or_session_member),
):
    """
    Create a new song with basic information.

    Requires a logged-in account or active session membership.
    """
    # Enforce demo download quota up front: a song created here is followed by
    # POST /api/youtube/download. Blocking only the download would leave an
    # orphaned, track-less song in the library, so a demo user over quota must
    # be rejected before anything is persisted. No-op for non-demo requesters.
    # The add-song flow uses POST /api/songs/from-youtube, which does both.
    enforce_demo_download_quota(db, requester)

    try:
        song = create_song_record(
            db,
            {
                "id": song_data.id,
                "title": song_data.title,
                "artist": song_data.artist,
                "album": song_data.album,
                "show_name": song_data.show_name,
                # A show given here is a person's, not the recording's
                "show_name_hand_set_at": (
                    datetime.now(timezone.utc) if song_data.show_name else None
                ),
                "duration": song_data.duration,
                "source": song_data.source,
                "video_id": song_data.video_id,
            },
        )

        response = song.to_dict()
        response["status"] = "pending"

        logger.info("Successfully created song: %s", song.id)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating song: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create song: {str(e)}")


@router.post("/from-youtube", response_model=SongFromYouTubeResponse, status_code=202)
async def add_song_from_youtube_route(
    body: SongFromYouTubeRequest,
    db: Session = Depends(get_db),
    requester: RequesterContext = Depends(require_host_or_session_member),
    manager: SessionConnectionManager = Depends(get_session_manager),
):
    """
    Add a YouTube song to the library and queue its processing, in one request.

    When the song's only library copy failed, that copy is restarted instead of
    adding a duplicate. 409 when a working copy is already there; 429/403 past
    the demo's download quota.
    """
    added = await run_in_threadpool(
        add_song_from_youtube,
        db,
        requester,
        video_id=body.video_id,
        title=body.title,
        artists=[a.model_dump() for a in body.artists],
        album=body.album,
        duration=body.duration,
        source=body.source,
    )
    await broadcast_job_created(manager, added.event)
    return SongFromYouTubeResponse(
        songId=added.song_id, jobId=added.job_id, restarted=added.restarted
    )


@router.patch("/{song_id}", response_model=SongResponse)
async def update_song(
    song_id: str,
    update_data: SongUpdateRequest,
    db: Session = Depends(get_db),
    requester: RequesterContext = Depends(require_host_or_session_member),
):
    """
    Update a song with any provided fields.

    Requires a logged-in account or active session membership.
    """
    try:
        repo = SongRepository(db)
        db_song = repo.fetch(song_id)

        if not db_song:
            raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

        # Build update fields from provided data
        update_dict = update_data.model_dump(exclude_unset=True)

        # A credit list replaces the artist text, which is rebuilt from it.
        credits_given = update_dict.pop("artists", None)
        if credits_given is not None:
            update_dict.pop("artist", None)
            if not any(c["role"] == "primary" for c in credits_given):
                raise HTTPException(
                    status_code=422, detail="At least one primary artist is needed"
                )

        # Extract lyrics fields for separate handling
        lyrics_data = extract_lyrics_fields(update_dict)

        # Language is validated, and can be cleared, which the mapping below can't do
        language_set = "language" in update_dict
        if language_set:
            try:
                language = normalize_language(update_dict.pop("language"))
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))

        # Map remaining fields to DB columns
        update_fields = map_fields_to_db(update_dict)
        if language_set:
            update_fields["language"] = language
        update_fields.pop("show_name", None)  # Handled below with its marker

        # A person changing the title or artist confirms them, so AcoustID
        # leaves them alone. The recording linked under the old names no
        # longer describes the song, and the edit settles any review.
        if any(
            key in update_fields and update_fields[key] != getattr(db_song, key)
            for key in ("title", "artist")
        ):
            update_fields.update(
                metadata_confirmed_at=datetime.now(timezone.utc),
                musicbrainz_recording_id=None,
                acoustid_suggested_recording_id=None,
                acoustid_suggested_title=None,
                acoustid_suggested_artist=None,
            )
            if db_song.show_name_hand_set_at is None:
                update_fields["show_name"] = None  # It came from that recording
            if db_song.acoustid_fingerprint_status in (
                "matched",
                "suggested",
                "ambiguous",
                "no_match",
            ):
                update_fields["acoustid_fingerprint_status"] = "skipped"
        artist_text_changed = (
            "artist" in update_fields and update_fields["artist"] != db_song.artist
        )

        # Editing the credits confirms them too. The recording stays: a fixed
        # credit list still describes the same recording.
        if credits_given is not None:
            update_fields.update(
                artist=credit_line([(c["name"], c["role"]) for c in credits_given]),
                metadata_confirmed_at=datetime.now(timezone.utc),
            )

        # A person setting the album name keeps automatic lookups off the
        # song; the cover it had stays linked, so trimming "(Deluxe)" doesn't
        # lose it. Clearing the name drops the cover too and lets the next
        # lookup find one.
        if "album" in update_dict:
            album = (update_dict["album"] or "").strip() or None
            if album is None:
                update_fields.update(
                    album=None,
                    album_id=None,
                    album_hand_set_at=None,
                    album_checked_at=None,
                )
            elif album != db_song.album:
                update_fields.update(
                    album=album, album_hand_set_at=datetime.now(timezone.utc)
                )
            else:
                update_fields.pop("album", None)

        # A person setting or clearing the show takes it off the recording
        # for good: cleared, the song stays out of every show.
        if "showName" in update_dict:
            show_name = (update_dict["showName"] or "").strip() or None
            if show_name != db_song.show_name:
                update_fields.update(
                    show_name=show_name,
                    show_name_hand_set_at=datetime.now(timezone.utc),
                )

        if update_fields:
            updated_song = repo.update(song_id, **update_fields)
            if not updated_song:
                raise HTTPException(
                    status_code=500, detail="Failed to update song metadata"
                )

        # Credits as given, or parsed from retyped artist text
        if credits_given is not None or artist_text_changed:
            db_song = repo.fetch(song_id)
            set_song_credits(
                db,
                db_song,
                (
                    [
                        ArtistCredit(name=c["name"], role=c["role"])
                        for c in credits_given
                    ]
                    if credits_given is not None
                    else None
                ),
            )
            db.commit()

        # Update lyrics columns directly
        lyrics_text_saved = False
        if lyrics_data:
            db_song = repo.fetch(song_id)
            if "plainLyrics" in lyrics_data:
                db_song.plain_lyrics = lyrics_data["plainLyrics"] or None
                db_song.word_synced_lyrics = None
                lyrics_text_saved = True
            if "syncedLyrics" in lyrics_data:
                db_song.synced_lyrics = lyrics_data["syncedLyrics"] or None
                db_song.word_synced_lyrics = None
                lyrics_text_saved = True
            if "wordSyncedLyrics" in lyrics_data:
                db_song.word_synced_lyrics = lyrics_data["wordSyncedLyrics"] or None
            if lyrics_text_saved:
                # A person chose these lyrics: automatic runs now only time them.
                db_song.lyrics_hand_picked_at = datetime.now(timezone.utc)
            db.commit()
            if lyrics_text_saved:
                from app.jobs.lyrics_dispatch import realign_hand_picked_lyrics

                realign_hand_picked_lyrics(db_song)

        # Re-fetch to get updated relationships
        db_song = repo.fetch(song_id)
        return db_song.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating song: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update song: {str(e)}")


@router.delete("/{song_id}")
async def delete_song(
    song_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Delete a song by its ID.
    """
    try:
        repo = SongRepository(db)
        db_song = repo.fetch(song_id)

        if not db_song:
            raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

        success = repo.delete(song_id)

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to delete song from database"
            )

        # Delete associated files
        try:
            file_service = FileService()
            file_service.delete_song_files(song_id)
        except Exception as e:
            logger.warning("Error deleting files for song %s: %s", song_id, e)

        logger.info("Successfully deleted song: %s", song_id)
        return {"message": "Song deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting song: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete song: {str(e)}")


@router.get("/{song_id}/thumbnail")
async def get_thumbnail(song_id: str, db: Session = Depends(get_db)):
    """
    Serve the thumbnail image for a song, auto-detecting format.
    """
    # Decode the song ID to handle URL-encoded characters
    song_id = unquote(song_id)

    try:
        repo = SongRepository(db)
        db_song = repo.fetch(song_id)

        if not db_song:
            raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

        file_service = FileService()
        song_dir = file_service.get_song_directory(song_id)

        # Try different formats in order of preference
        formats_to_try = [
            ("webp", "image/webp"),
            ("jpg", "image/jpeg"),
            ("jpeg", "image/jpeg"),
            ("png", "image/png"),
        ]

        for extension, mimetype in formats_to_try:
            thumbnail_path = song_dir / f"thumbnail.{extension}"
            if thumbnail_path.exists() and os.access(thumbnail_path, os.R_OK):
                # Without Cache-Control every view revalidates; see
                # get_artist_image.
                return FileResponse(
                    thumbnail_path,
                    media_type=mimetype,
                    headers={"Cache-Control": "public, max-age=3600"},
                )

        raise HTTPException(
            status_code=404, detail=f"Thumbnail not found for song: {song_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error serving thumbnail: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get thumbnail: {str(e)}"
        )


@router.get("/{song_id}/download/{track_type}")
async def download_song_track(
    song_id: str,
    track_type: str,
    db: Session = Depends(get_db),
):
    """
    Download a specific audio track for a song.

    Public endpoint: served unauthenticated so <audio> elements can load it
    directly (they cannot send an Authorization header). Same precedent as
    GET /{song_id}/thumbnail. Safety comes from the track_type allowlist and
    the library-bounds check below.

    - **track_type**: Type of track to download (vocals, instrumental, original)
    """
    logger.debug("Download request for song %r, track type %r", song_id, track_type)

    track_type = track_type.lower()
    valid_track_types = ["vocals", "instrumental", "backing-vocals", "original"]

    if track_type not in valid_track_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid track type: {track_type}. Valid types: {', '.join(valid_track_types)}",
        )

    try:
        file_service = FileService()
        song_dir = file_service.get_song_directory(song_id)

        if not song_dir.is_dir():
            raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

        # Map track type to filename (backing-vocals uses underscore on disk)
        track_filename = track_type.replace("-", "_")
        track_file = song_dir / f"{track_filename}.mp3"

        if not track_file.is_file():
            raise HTTPException(
                status_code=404,
                detail=f"{track_type.capitalize()} track not found for this song",
            )

        # Security check - ensure file is within library bounds
        config = get_config()
        library_base_path = config.LIBRARY_DIR.resolve()
        file_path_resolved = track_file.resolve()

        if library_base_path not in file_path_resolved.parents:
            logger.error("Attempted download outside library bounds: %s", track_file)
            raise HTTPException(status_code=403, detail="Access denied")

        return FileResponse(
            track_file,
            media_type="audio/mpeg",
            filename=f"{track_type}.mp3",
            content_disposition_type="inline",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error downloading track: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to download track: {str(e)}"
        )


@router.post("/{song_id}/reprocess", status_code=202)
async def reprocess_song(
    song_id: str,
    request: SongReprocessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Re-process a song's audio with a different separation engine.

    Creates a background job to reprocess the audio.
    Returns immediately with a job ID for tracking progress.

    - **song_id**: The song ID to reprocess
    - **engine_type**: Separation engine to use (demucs, roformer, hybrid, clean_backing, three_track, three_track_duality_v2, three_track_mel1143)
    """
    from datetime import datetime, timezone
    from pathlib import Path

    from app.db.models import Job, JobStatus, JobStep
    from app.repositories import JobRepository

    logger.info(
        f"Reprocess request for song {song_id} with engine {request.engine_type}"
    )

    try:
        # 1. Verify song exists
        repo = SongRepository(db)
        db_song = repo.fetch(song_id)

        if not db_song:
            raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

        # 2. Verify original.mp3 exists
        config = get_config()
        song_dir = Path(config.BASE_LIBRARY_DIR) / song_id
        original_path = song_dir / "original.mp3"

        if not original_path.exists():
            raise HTTPException(
                status_code=400,
                detail="Original audio file not found. Cannot reprocess.",
            )

        # 3. Check if already processing (prevent duplicate jobs)
        job_repository = JobRepository()
        active_jobs = job_repository.get_in_flight_jobs()
        for job in active_jobs:
            if job.song_id == song_id:
                raise HTTPException(
                    status_code=409,
                    detail="Song is already being processed",
                )

        # 4. Reset song status and create job record
        repo.update(song_id, status="processing", error_message=None)

        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            filename="original.mp3",
            status=JobStatus.PENDING,
            step=JobStep.SEPARATE,
            status_message=f"Queued for reprocessing with {request.engine_type}",
            progress=0,
            song_id=song_id,
            title=db_song.title,
            artist=db_song.artist,
            engine_type=request.engine_type,
            created_at=datetime.now(timezone.utc),
        )
        job_repository.create(job)

        # 5. Queue Celery task
        from app.jobs.celery_app import celery

        task = celery.send_task(
            "process_audio_job",
            args=[job_id, request.engine_type],
        )

        # 6. Update job with task ID
        job.task_id = task.id
        job_repository.update(job)

        logger.info(
            f"Reprocess job {job_id} queued for song {song_id} with engine {request.engine_type}"
        )

        return {
            "jobId": job_id,
            "status": "pending",
            "message": f"Reprocessing started with {request.engine_type}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error starting reprocess: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to start reprocessing: {str(e)}"
        )


@router.post("/{song_id}/fingerprint/lookup")
async def lookup_song_fingerprint(
    song_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Run AcoustID fingerprint synchronously and return all candidates. Does not save results."""
    from pathlib import Path

    from app.services.acoustid_service import AcoustIdService

    if not SongRepository(db).fetch(song_id):
        raise HTTPException(status_code=404, detail="Song not found")

    config = get_config()
    song_dir = Path(config.BASE_LIBRARY_DIR) / song_id
    original = song_dir / "original.mp3"
    instrumental = song_dir / "instrumental.mp3"
    vocals = song_dir / "vocals.mp3"
    audio_path = (
        original
        if original.exists()
        else (
            instrumental
            if instrumental.exists()
            else vocals if vocals.exists() else None
        )
    )

    if not audio_path:
        raise HTTPException(status_code=422, detail="No audio file found for this song")

    try:
        candidates = AcoustIdService(SongRepository(db)).lookup_candidates(audio_path)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("fingerprint/lookup failed for song %s", song_id)
        raise HTTPException(status_code=500, detail="Fingerprint lookup failed")

    return {"candidates": candidates}


@router.post("/{song_id}/fingerprint/apply")
async def apply_song_fingerprint(
    song_id: str,
    request: FingerprintApplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Apply a recording a person picked (from AcoustID or a MusicBrainz search)."""
    song_repo = SongRepository(db)
    if not song_repo.fetch(song_id):
        raise HTTPException(status_code=404, detail="Song not found")

    _apply_picked_recording(
        db,
        song_id,
        recording_id=request.recording_id,
        title=request.title,
        artist=request.artist,
        score=request.score,
    )
    return {"status": "applied"}


@router.post("/{song_id}/fingerprint/suggestion/accept")
async def accept_fingerprint_suggestion(
    song_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Rename the song as AcoustID suggested and link its recording."""
    song = SongRepository(db).fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    if not song.acoustid_suggested_recording_id:
        raise HTTPException(status_code=409, detail="Song has no AcoustID suggestion")

    _apply_picked_recording(
        db,
        song_id,
        recording_id=song.acoustid_suggested_recording_id,
        title=song.acoustid_suggested_title or song.title,
        artist=song.acoustid_suggested_artist or song.artist,
        score=song.acoustid_score,
    )
    return {"status": "applied"}


def _apply_picked_recording(
    db: Session,
    song_id: str,
    *,
    recording_id: str,
    title: str,
    artist: str,
    score: Optional[float],
) -> None:
    """Set the title, artist and recording a person chose, and confirm them."""
    from app.jobs.celery_app import celery

    song_repo = SongRepository(db)
    song_repo.update(
        song_id,
        title=title,
        artist=artist,
        acoustid_score=score,
        musicbrainz_recording_id=recording_id,
        acoustid_fingerprint_status="matched",
        acoustid_suggested_recording_id=None,
        acoustid_suggested_title=None,
        acoustid_suggested_artist=None,
        metadata_confirmed_at=datetime.now(timezone.utc),
    )

    logger.info(
        "Picked recording for song %s → '%s' by '%s' (score=%s, recording=%s)",
        song_id,
        title,
        artist,
        f"{score:.2f}" if score is not None else "n/a",
        recording_id,
    )

    # The credits come from the recording a person chose: the enrichment
    # writes them (and the soundtrack show_name), overriding the lock.
    celery.send_task(
        "enrich_song_artist_credits", args=[song_id], kwargs={"picked": True}
    )


@router.post("/{song_id}/skip-fingerprint", status_code=200)
async def skip_fingerprint(
    song_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Keep the song's current title and artist: AcoustID won't change or suggest them."""
    repo = SongRepository(db)
    song = repo.fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    fields: dict = {
        "acoustid_fingerprint_status": "skipped",
        "acoustid_suggested_recording_id": None,
        "acoustid_suggested_title": None,
        "acoustid_suggested_artist": None,
        "metadata_confirmed_at": datetime.now(timezone.utc),
    }
    # A suggested song has no recording that matches the names being kept.
    if song.acoustid_fingerprint_status == "suggested":
        fields["musicbrainz_recording_id"] = None
    repo.update(song_id, **fields)
    logger.info("Kept current title/artist for song %s", song_id)
    return {"status": "skipped"}


@router.post("/{song_id}/analyze-vocal-range", status_code=200)
async def analyze_vocal_range(
    song_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Detect vocal range from the isolated vocals stem and persist the result."""
    import asyncio
    from pathlib import Path

    from app.config import get_config
    from app.services.audio import detect_vocal_range

    repo = SongRepository(db)
    if not repo.fetch(song_id):
        raise HTTPException(status_code=404, detail="Song not found")

    config = get_config()
    vocals_path = Path(config.BASE_LIBRARY_DIR) / song_id / "vocals.mp3"
    if not vocals_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Vocals stem not found — song may not be processed yet",
        )

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: detect_vocal_range(
            vocals_path, lambda msg: logger.debug("VocalRange: %s", msg)
        ),
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Could not detect vocal range (insufficient voiced frames)",
        )

    low, high = result
    repo.update(song_id, vocal_range_low=low, vocal_range_high=high)
    logger.info("Vocal range detected for song %s: %s – %s", song_id, low, high)
    return {"vocal_range_low": low, "vocal_range_high": high}


@router.post("/{song_id}/fingerprint", status_code=202)
async def fingerprint_single_song_endpoint(
    song_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Dispatch an AcoustID fingerprint job for a single song."""
    if not SongRepository(db).fetch(song_id):
        raise HTTPException(status_code=404, detail="Song not found")
    from app.jobs.celery_app import celery

    task = celery.send_task("fingerprint_single_song", args=[song_id])
    return {"taskId": task.id, "status": "dispatched"}


@router.post("/{song_id}/validate-youtube-replacement", status_code=200)
async def validate_youtube_replacement(
    song_id: str,
    request: SongReplaceYouTubeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Validate a YouTube replacement track with AcoustID before processing."""
    import shutil
    import uuid
    from pathlib import Path

    from app.schemas.song import ReplacementValidationResponse
    from app.services.acoustid_service import AcoustIdService
    from app.services.youtube_service import YouTubeService

    song_repo = SongRepository(db)
    if not song_repo.fetch(song_id):
        raise HTTPException(status_code=404, detail="Song not found")

    try:
        # Use a temporary unique ID for download
        temp_song_id = f"validation_{uuid.uuid4().hex[:8]}"
        youtube_service = YouTubeService()

        try:
            # Download video to temp location in library (will be cleaned up after)
            youtube_service.download_video(
                video_id_or_url=request.video_id,
                song_id=temp_song_id,
                artist=request.artist,
                title=request.title,
            )

            # Find the downloaded audio file
            from app.config import get_config

            config = get_config()
            temp_song_dir = Path(config.BASE_LIBRARY_DIR) / temp_song_id
            audio_path = temp_song_dir / "original.mp3"

            if not audio_path.exists():
                raise FileNotFoundError(f"Downloaded audio not found at {audio_path}")

            # Run AcoustID fingerprinting using lookup_candidates (doesn't modify DB)
            acoustid_service = AcoustIdService(SongRepository(db))
            candidates = acoustid_service.lookup_candidates(audio_path)

            # Extract best match
            if candidates:
                best = candidates[0]
                acoustid_status = "matched"
                acoustid_score = best["score"]
                mbid = best["recordingId"]
                title_match = best["title"]
                artist_match = best["artist"]
            else:
                acoustid_status = "no_match"
                acoustid_score = None
                mbid = None
                title_match = None
                artist_match = None

            # Determine validation success
            validated = acoustid_status == "matched" and (acoustid_score or 0) >= 0.9
            message = _format_validation_message(acoustid_status, acoustid_score)

            return ReplacementValidationResponse(
                validated=validated,
                audioPath=str(audio_path) if validated else None,
                acoustidStatus=acoustid_status,
                acoustidScore=acoustid_score,
                musicbrainzId=mbid,
                title=title_match,
                artist=artist_match,
                message=message,
            )

        except Exception as e:
            logger.error("AcoustID validation failed: %s", e, exc_info=True)
            raise

        finally:
            # Clean up temp directory
            if temp_song_dir.exists():
                shutil.rmtree(temp_song_dir, ignore_errors=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "YouTube validation failed for song %s: %s", song_id, e, exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post("/{song_id}/validate-upload-replacement", status_code=200)
async def validate_upload_replacement(
    song_id: str,
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Validate an uploaded replacement track with AcoustID before processing."""
    import shutil
    import tempfile
    from pathlib import Path

    from app.schemas.song import ReplacementValidationResponse
    from app.services.acoustid_service import AcoustIdService

    song_repo = SongRepository(db)
    if not song_repo.fetch(song_id):
        raise HTTPException(status_code=404, detail="Song not found")

    if not (audio_file.content_type or "").startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file")

    try:
        # Save to temp location
        temp_dir = Path(tempfile.mkdtemp())
        temp_audio = temp_dir / "validation.mp3"
        temp_audio.write_bytes(await audio_file.read())

        try:
            # Run AcoustID fingerprinting using lookup_candidates (doesn't modify DB)
            acoustid_service = AcoustIdService(SongRepository(db))
            candidates = acoustid_service.lookup_candidates(temp_audio)

            # Extract best match
            if candidates:
                best = candidates[0]
                acoustid_status = "matched"
                acoustid_score = best["score"]
                mbid = best["recordingId"]
                title_match = best["title"]
                artist_match = best["artist"]
            else:
                acoustid_status = "no_match"
                acoustid_score = None
                mbid = None
                title_match = None
                artist_match = None

            # Determine validation success
            validated = acoustid_status == "matched" and (acoustid_score or 0) >= 0.9
            message = _format_validation_message(acoustid_status, acoustid_score)

            return ReplacementValidationResponse(
                validated=validated,
                audioPath=str(temp_audio) if validated else None,
                acoustidStatus=acoustid_status,
                acoustidScore=acoustid_score,
                musicbrainzId=mbid,
                title=title_match,
                artist=artist_match,
                message=message,
            )

        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Upload validation failed for song %s: %s", song_id, e, exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


def _format_validation_message(status: str, score: Optional[float]) -> str:
    """Format a human-readable validation message."""
    if status == "matched":
        if score and score >= 0.9:
            return f"✓ Match found with high confidence ({score:.1%})"
        elif score:
            return f"⚠ Match found but confidence too low ({score:.1%} < 90%)"
        else:
            return "⚠ Match found but confidence unknown"
    elif status == "no_match":
        return "✗ No AcoustID match found — this track may not be the right song"
    elif status == "failed":
        return "✗ AcoustID fingerprinting failed — unable to validate this track"
    else:
        return f"? Unknown validation status: {status}"


@router.post("/{song_id}/replace-youtube", status_code=202)
async def replace_song_youtube(
    song_id: str,
    request: SongReplaceYouTubeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Replace a song's audio source with a YouTube Music track and reprocess."""
    song_repo = SongRepository(db)
    db_song = song_repo.fetch(song_id)
    if not db_song:
        raise HTTPException(status_code=404, detail="Song not found")

    job_id = restart_youtube_processing(
        song_repo,
        song_id,
        video_id=request.video_id,
        artist=request.artist or db_song.artist,
        title=request.title or db_song.title,
        engine_type=request.engine_type,
    )
    logger.info("replace-youtube: queued job %s for song %s", job_id, song_id)
    return {"jobId": job_id, "status": "pending"}


@router.post("/{song_id}/retry", status_code=202)
async def retry_failed_song(
    song_id: str,
    db: Session = Depends(get_db),
    requester: RequesterContext = Depends(require_host_or_session_member),
    manager: SessionConnectionManager = Depends(get_session_manager),
):
    """Restart a failed song from its own YouTube source.

    Open to anyone who can add songs: adding a song whose earlier attempt
    failed restarts that row rather than creating a duplicate beside it.
    Only failed songs qualify, so this can't disturb a working one.
    """
    song_repo = SongRepository(db)
    db_song = song_repo.fetch(song_id)
    if not db_song:
        raise HTTPException(status_code=404, detail="Song not found")
    if db_song.status != "error":
        raise HTTPException(status_code=409, detail="Only a failed song can be retried")
    if not db_song.video_id:
        raise HTTPException(
            status_code=400, detail="This song has no YouTube source to retry from"
        )

    # Counts against demo download quotas like any other add. No-op otherwise.
    session_id, user_id = enforce_demo_download_quota(db, requester)

    job_id = restart_youtube_processing(
        song_repo,
        song_id,
        video_id=db_song.video_id,
        artist=db_song.artist,
        title=db_song.title,
        engine_type="three_track",
        session_id=session_id,
        user_id=user_id,
    )
    logger.info("retry: queued job %s for failed song %s", job_id, song_id)

    await broadcast_job_created(
        manager,
        job_created_event(
            job_id=job_id,
            song_id=song_id,
            artist=db_song.artist,
            title=db_song.title,
            session_id=session_id,
        ),
    )
    return {"jobId": job_id, "status": "pending"}


@router.post("/{song_id}/replace-upload", status_code=202)
async def replace_song_upload(
    song_id: str,
    audio_file: UploadFile = File(...),
    engine_type: str = Form(default="three_track"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Replace a song's audio source with an uploaded MP3 and reprocess."""
    from datetime import datetime, timezone

    from app.db.models import Job, JobStatus, JobStep
    from app.repositories import JobRepository

    song_repo = SongRepository(db)
    db_song = song_repo.fetch(song_id)
    if not db_song:
        raise HTTPException(status_code=404, detail="Song not found")
    if not (audio_file.content_type or "").startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file")

    valid_engines = {
        "demucs",
        "roformer",
        "hybrid",
        "clean_backing",
        "three_track",
        "three_track_duality_v2",
        "three_track_mel1143",
    }
    if engine_type not in valid_engines:
        raise HTTPException(
            status_code=400, detail=f"engine_type must be one of: {valid_engines}"
        )

    job_repository = JobRepository()
    active_jobs = job_repository.get_in_flight_jobs()
    if any(j.song_id == song_id for j in active_jobs):
        raise HTTPException(status_code=409, detail="Song is already being processed")

    song_repo.update(
        song_id,
        status="processing",
        error_message=None,
        acoustid_fingerprint_status="not_checked",
        acoustid_score=None,
        musicbrainz_recording_id=None,
        acoustid_suggested_recording_id=None,
        acoustid_suggested_title=None,
        acoustid_suggested_artist=None,
        vocal_range_low=None,
        vocal_range_high=None,
        loudness_lufs=None,
        true_peak_dbtp=None,
        gain_db=None,
        engine_type=None,
    )

    song_dir = FileService().get_song_directory(song_id)
    dest = song_dir / "original.mp3"
    dest.write_bytes(await audio_file.read())

    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        filename="original.mp3",
        status=JobStatus.PENDING,
        step=JobStep.SEPARATE,
        status_message="Queued for reprocessing with uploaded audio",
        progress=0,
        song_id=song_id,
        title=db_song.title,
        artist=db_song.artist,
        engine_type=engine_type,
        created_at=datetime.now(timezone.utc),
    )
    job_repository.create(job)

    from app.jobs.celery_app import celery

    task = celery.send_task("process_audio_job", args=[job_id, engine_type])
    job.task_id = task.id
    job_repository.update(job)

    logger.info("replace-upload: queued job %s for song %s", job_id, song_id)
    return {"jobId": job_id, "status": "pending"}
