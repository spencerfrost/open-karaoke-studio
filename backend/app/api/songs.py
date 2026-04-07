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
from typing import Generator, List, Optional
from urllib.parse import unquote

from app.api.dependencies import get_current_user
from app.api.validators import (
    CAMEL_TO_SNAKE_CASE,
    VALID_ARTIST_SORT_FIELDS,
    VALID_SONG_SORT_FIELDS,
    extract_lyrics_fields,
    map_fields_to_db,
    validate_direction,
    validate_sort_field,
)
from app.config import get_config
from app.db.database import SessionLocal
from app.db.models.artist import DbArtist
from app.db.models.song import DbSong
from app.db.models.song_artist import DbSongArtist
from app.db.models.user import User
from app.repositories.album_repository import AlbumRepository
from app.repositories.artist_repository import ArtistRepository
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
    SongReprocessRequest,
    SongReplaceYouTubeRequest,
    SongResponse,
    SongSearchResponse,
    SongUpdateRequest,
)
from app.services.file_service import FileService
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

# ============================================================================
# Router & Logger
# ============================================================================
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/songs", tags=["songs"])

# ============================================================================
# Dependencies
# ============================================================================


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error("Database session error: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================================
# Helpers
# ============================================================================


def _download_album_cover(
    collection_id: int, artwork_urls: list[str]
) -> str | None:
    """Download the highest-res iTunes artwork and cache it locally.

    Returns the relative path 'covers/{collection_id}.jpg' on success, None on failure.
    """
    import requests

    config = get_config()
    covers_dir = config.library_path / "covers"
    covers_dir.mkdir(exist_ok=True)
    dest = covers_dir / f"{collection_id}.jpg"

    # Derive 600px URL from the first artwork URL (iTunes URL pattern)
    url_600 = None
    for url in artwork_urls:
        if url:
            url_600 = url.replace("100x100bb", "600x600bb").replace(
                "100x100", "600x600"
            )
            break

    if not url_600:
        return None

    try:
        response = requests.get(
            url_600, timeout=10, headers={"User-Agent": "curl/8.0.0"}
        )
        response.raise_for_status()
        dest.write_bytes(response.content)
        logger.info("Downloaded album cover for collection %s", collection_id)
        return f"covers/{collection_id}.jpg"
    except Exception as e:
        logger.warning("Failed to download album cover for collection %s: %s", collection_id, e)
        return None


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
            sort_by=sort_by, direction=direction, limit=limit, offset=offset
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

    - **q**: Search query (searches title, artist, album)
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
        search_filter = or_(
            DbSong.title.ilike(f"%{query}%"),
            DbSong.artist.ilike(f"%{query}%"),
            DbSong.album.ilike(f"%{query}%"),
        )

        if group_by_artist:
            artist_query = (
                db.query(DbSong.artist, func.count(DbSong.id).label("song_count"))
                .filter(search_filter)
                .group_by(DbSong.artist)
            )
            total_artists = artist_query.count()
            artist_results = artist_query.offset(offset).limit(limit).all()

            artists_data = []
            total_songs = 0
            for artist, count in artist_results:
                songs = db.query(DbSong).filter(DbSong.artist == artist).limit(5).all()
                total_songs += count
                artists_data.append(
                    ArtistInfo(
                        artist=artist,
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
            base_query = db.query(DbSong).filter(search_filter)

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
    Get a list of all unique artists with their song counts.

    - **search**: Optional search term to filter artists
    - **limit**: Maximum number of artists to return (default: all)
    - **offset**: Number of artists to skip for pagination
    """
    try:
        query = (
            db.query(
                DbArtist.id,
                DbArtist.display_name,
                DbArtist.name,
                func.count(DbSongArtist.song_id).label("song_count"),
            )
            .join(DbSongArtist, DbSongArtist.artist_id == DbArtist.id)
            .group_by(DbArtist.id)
            .order_by(DbArtist.name)
        )

        # Apply search filter if provided
        if search and search.strip():
            search_term = search.strip()
            query = query.filter(
                or_(
                    DbArtist.name.ilike(f"%{search_term}%"),
                    DbArtist.display_name.ilike(f"%{search_term}%"),
                )
            )

        total = query.count()

        if limit:
            query = query.offset(offset).limit(limit)

        results = query.all()

        return {
            "artists": [
                {
                    "id": artist_id,
                    "name": display_name or name,
                    "songCount": count,
                    "firstLetter": "#" if name and name[0].isdigit() else (name[0].upper() if name else "?"),
                }
                for artist_id, display_name, name, count in results
            ],
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


@router.get("/by-artist/{artist_name}")
async def get_songs_by_artist(
    artist_name: str,
    limit: int = Query(
        20, ge=1, le=500, description="Maximum number of songs to return"
    ),
    offset: int = Query(0, ge=0, description="Number of songs to skip"),
    sort: str = Query("title", description="Sort field: title, album, year, dateAdded"),
    direction: str = Query("asc", description="Sort direction: asc or desc"),
    db: Session = Depends(get_db),
):
    """
    Get songs for a specific artist with pagination.

    - **artist_name**: The artist name (URL-encoded)
    - **limit**: Maximum number of songs to return (1-100)
    - **offset**: Number of songs to skip
    - **sort**: Sort field (title, album, year, dateAdded)
    - **direction**: Sort direction (asc or desc)
    """
    # Decode the artist name
    artist_name = unquote(artist_name)

    # Validate sort field and direction
    if sort not in VALID_ARTIST_SORT_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field: {sort}. Must be one of: title, album, year, dateAdded",
        )
    db_sort_field = CAMEL_TO_SNAKE_CASE.get(sort, sort)
    direction = validate_direction(direction, raise_on_invalid=True)

    try:
        # Subquery to get song IDs for this artist (avoids DISTINCT on JSON columns)
        song_ids_subq = (
            db.query(DbSongArtist.song_id)
            .join(DbArtist, DbArtist.id == DbSongArtist.artist_id)
            .filter(DbArtist.name == artist_name.lower().strip())
            .subquery()
        )
        base_query = db.query(DbSong).filter(DbSong.id.in_(song_ids_subq))

        # Apply sorting
        sort_column = getattr(DbSong, db_sort_field, DbSong.title)
        if direction.lower() == "desc":
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())

        total_count = base_query.count()
        songs = base_query.offset(offset).limit(limit).all()

        return {
            "songs": [song.to_dict() for song in songs],
            "artist": artist_name,
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
        logger.error(
            f"Error fetching songs for artist '{artist_name}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get songs for artist: {str(e)}",
        )


@router.get("/by-fingerprint-status", response_model=List[SongResponse])
async def get_songs_by_fingerprint_status(
    status: str = Query(..., description="acoustid_fingerprint_status value"),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return songs filtered by acoustid_fingerprint_status."""
    valid = {"no_match", "failed", "not_checked", "matched", "skipped", "ambiguous"}
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
    current_user: User = Depends(get_current_user),
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
        issues.append({"type": "empty_title", "label": "Missing Title", "severity": "error"})
    if not artist.strip():
        issues.append({"type": "empty_artist", "label": "Missing Artist", "severity": "error"})
    if artist.strip() == "Unknown Artist":
        issues.append({"type": "unknown_artist", "label": "Unknown Artist", "severity": "warning"})

    title_lower = title.lower()
    if any(p in title_lower for p in _SUSPICIOUS_TITLE_PATTERNS):
        issues.append({"type": "suspicious_title", "label": "Raw YouTube Title", "severity": "warning"})

    if len(title) > 80:
        issues.append({"type": "long_title", "label": "Long Title", "severity": "info"})

    if len(title) < 5 and len(artist) > 40:
        issues.append({"type": "swapped_fields", "label": "Possibly Swapped", "severity": "warning"})

    combined = f"{title} {artist}"
    if "\ufffd" in combined or any(ord(c) > 0xFFFF for c in combined):
        issues.append({"type": "encoding_artifact", "label": "Encoding Issue", "severity": "warning"})

    if not song.source:
        issues.append({"type": "missing_source", "label": "No Source", "severity": "info"})
    if song.duration is None:
        issues.append({"type": "missing_duration", "label": "No Duration", "severity": "warning"})
    if not song.album:
        issues.append({"type": "missing_album", "label": "No Album", "severity": "info"})
    if not song.plain_lyrics and not song.synced_lyrics:
        issues.append({"type": "missing_lyrics", "label": "No Lyrics", "severity": "info"})
    if not song.vocal_range_low and not song.vocal_range_high:
        issues.append({"type": "missing_vocal_range", "label": "No Vocal Range", "severity": "info"})

    return issues


@router.get("/metadata-audit", response_model=MetadataAuditResponse)
async def get_metadata_audit(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    """
    Delete an orphaned library directory that has no corresponding DB record.
    """
    config = get_config()

    # Safety: reject any path traversal attempts
    if "/" in dir_name or "\\" in dir_name or ".." in dir_name:
        raise HTTPException(status_code=400, detail="Invalid directory name")

    # Confirm it's actually on disk
    song_dir = config.LIBRARY_DIR / dir_name
    if not song_dir.exists() or not song_dir.is_dir():
        raise HTTPException(
            status_code=404, detail=f"Directory not found: {dir_name}"
        )

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
    current_user: User = Depends(get_current_user),
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
        # Safety: reject any path traversal attempts
        if "/" in dir_name or "\\" in dir_name or ".." in dir_name:
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
    current_user: User = Depends(get_current_user),
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


@router.get("/{song_id}/chords")
async def get_song_chords(song_id: str, db: Session = Depends(get_db)):
    """
    Get chord detection data for a song.

    Returns timestamped chord progression as a JSON array.
    """
    try:
        repo = SongRepository(db)
        db_song = repo.fetch(song_id)

        if not db_song:
            raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

        if db_song.chords_data is None:
            raise HTTPException(
                status_code=404, detail="No chord data available for this song"
            )

        return db_song.chords_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching chords for song %s: %s", song_id, e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get chord data: {str(e)}"
        )


@router.get("/duplicates")
async def get_duplicate_songs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
async def create_song(song_data: SongCreateRequest, db: Session = Depends(get_db)):
    """
    Create a new song with basic information.
    """
    song_id = song_data.id or str(uuid.uuid4())
    logger.info("Creating new song with ID: %s", song_id)

    try:
        repo = SongRepository(db)

        song_dict = {
            "id": song_id,
            "title": song_data.title,
            "artist": song_data.artist,
            "album": song_data.album,
            "duration": song_data.duration,
            "source": song_data.source,
            "video_id": song_data.video_id,
        }

        song = repo.create(song_dict)

        if not song:
            raise HTTPException(
                status_code=500, detail=f"Failed to create song {song_id} in database"
            )

        # Populate song_artists join table
        from app.services.song_artist_service import populate_song_artists

        populate_song_artists(db, song, song_data.artist)

        # Create the song directory
        try:
            file_service = FileService()
            song_dir = file_service.get_song_directory(song_id)
            song_dir.mkdir(parents=True, exist_ok=True)
            logger.debug("Created directory for song: %s", song_dir)
        except Exception as e:
            logger.warning("Error creating directory for song %s: %s", song_id, e)

        response = song.to_dict()
        response["status"] = "pending"

        logger.info("Successfully created song: %s", song_id)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating song: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create song: {str(e)}")


@router.patch("/{song_id}", response_model=SongResponse)
async def update_song(
    song_id: str, update_data: SongUpdateRequest, db: Session = Depends(get_db)
):
    """
    Update a song with any provided fields.
    """
    try:
        repo = SongRepository(db)
        db_song = repo.fetch(song_id)

        if not db_song:
            raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

        # Build update fields from provided data
        update_dict = update_data.model_dump(exclude_unset=True)

        # Extract itunesCollectionId before mapping — handled separately (album linkage)
        itunes_collection_id = update_dict.pop("itunesCollectionId", None)

        # Extract itunesArtworkUrls — used below to download album cover, not stored in DB
        update_dict.pop("itunesArtworkUrls", None)

        # Extract lyrics fields for separate handling
        lyrics_data = extract_lyrics_fields(update_dict)

        # Map remaining fields to DB columns
        update_fields = map_fields_to_db(update_dict)

        if update_fields:
            updated_song = repo.update(song_id, **update_fields)
            if not updated_song:
                raise HTTPException(
                    status_code=500, detail="Failed to update song metadata"
                )

        # Re-populate song_artists join table when artist changes
        if "artist" in update_dict:
            from app.services.song_artist_service import populate_song_artists

            db_song = repo.fetch(song_id)
            populate_song_artists(db, db_song, db_song.artist)

        # Update lyrics columns directly
        if lyrics_data:
            db_song = repo.fetch(song_id)
            if "plainLyrics" in lyrics_data:
                db_song.plain_lyrics = lyrics_data["plainLyrics"] or None
            if "syncedLyrics" in lyrics_data:
                db_song.synced_lyrics = lyrics_data["syncedLyrics"] or None
            db.commit()

        # Handle album + artist linkage when iTunes collection ID is provided
        if itunes_collection_id is not None:
            db_song = repo.fetch(song_id)
            artist_name = update_data.artist or db_song.artist
            artist = ArtistRepository(db).get_or_create(artist_name)

            album_title = update_data.album or db_song.album or "Unknown Album"
            album_repo = AlbumRepository(db)
            album = album_repo.get_or_create(
                title=album_title,
                itunes_collection_id=itunes_collection_id,
                artist_id=artist.id,
                release_date=update_data.releaseDate or db_song.release_date,
            )

            if not album.cover_path and update_data.itunesArtworkUrls:
                cover_path = _download_album_cover(
                    itunes_collection_id, update_data.itunesArtworkUrls
                )
                if cover_path:
                    album_repo.update_cover(album, cover_path)

            repo.update(song_id, artist_id=artist.id, album_id=album.id)

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
    current_user: User = Depends(get_current_user),
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
                return FileResponse(thumbnail_path, media_type=mimetype)

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
    song_id: str, track_type: str, db: Session = Depends(get_db)
):
    """
    Download a specific audio track for a song.

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
    current_user: User = Depends(get_current_user),
):
    """
    Re-process a song's audio with a different separation engine.

    Creates a background job to reprocess the audio.
    Returns immediately with a job ID for tracking progress.

    - **song_id**: The song ID to reprocess
    - **engine_type**: Separation engine to use (demucs, roformer, hybrid, clean_backing)
    """
    from datetime import datetime, timezone
    from pathlib import Path

    from app.db.models import Job, JobStatus
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
        active_jobs = job_repository.get_jobs_by_status(
            [JobStatus.PENDING, JobStatus.PROCESSING, JobStatus.DOWNLOADING]
        )
        for job in active_jobs:
            if job.song_id == song_id:
                raise HTTPException(
                    status_code=409,
                    detail="Song is already being processed",
                )

        # 4. Create job record
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            filename="original.mp3",
            status=JobStatus.PENDING,
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


@router.post("/fingerprint", status_code=202)
async def batch_fingerprint_songs_endpoint(
    force: bool = Query(False, description="Re-fingerprint all songs, including already-processed ones"),
    current_user: User = Depends(get_current_user),
):
    """Dispatch a Celery task to fingerprint songs. Pass ?force=true to reprocess everything."""
    from app.jobs.jobs import batch_fingerprint_songs

    task = batch_fingerprint_songs.delay(reprocess_all=force)
    return {"taskId": task.id, "status": "dispatched", "reprocess_all": force}


@router.post("/backfill-artwork", status_code=202)
async def backfill_artwork_endpoint(
    force: bool = Query(False, description="Reprocess all songs, including those already with album art"),
    current_user: User = Depends(get_current_user),
):
    """Dispatch a Celery task to backfill album art for songs missing it."""
    from app.jobs.jobs import batch_backfill_artwork

    task = batch_backfill_artwork.delay(force=force)
    return {"taskId": task.id, "status": "dispatched", "force": force}


@router.post("/backfill-duration", status_code=202)
async def backfill_duration_endpoint(
    mode: str = Query("missing", description="'missing' to fill only null durations, 'all' to recompute every song"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dispatch a Celery task to populate duration from the original audio file."""
    if mode not in ("missing", "all"):
        raise HTTPException(status_code=400, detail="mode must be 'missing' or 'all'")

    from app.jobs.jobs import batch_backfill_duration

    query = db.query(DbSong.id)
    if mode == "missing":
        query = query.filter(DbSong.duration.is_(None))
    queued = query.count()

    task = batch_backfill_duration.delay(mode=mode)
    return {"taskId": task.id, "queued": queued}


@router.post("/{song_id}/fingerprint/lookup")
async def lookup_song_fingerprint(
    song_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        original if original.exists()
        else instrumental if instrumental.exists()
        else vocals if vocals.exists()
        else None
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
    current_user: User = Depends(get_current_user),
):
    """Apply a selected AcoustID candidate to the song record."""
    song_repo = SongRepository(db)
    song = song_repo.fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    song_repo.update(
        song_id,
        title=request.title,
        artist=request.artist,
        acoustid_score=request.score,
        musicbrainz_recording_id=request.recording_id,
        acoustid_fingerprint_status="matched",
    )

    # Re-populate song_artists join table so artist browse stays in sync
    from app.services.song_artist_service import populate_song_artists

    song = song_repo.fetch(song_id)
    populate_song_artists(db, song, request.artist)

    logger.info(
        "fingerprint/apply: song %s → '%s' by '%s' (score=%.2f, recording=%s)",
        song_id,
        request.title,
        request.artist,
        request.score,
        request.recording_id,
    )
    return {"status": "applied"}


@router.post("/{song_id}/skip-fingerprint", status_code=200)
async def skip_fingerprint(
    song_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a song's AcoustID status as skipped so it no longer appears in the review panel."""
    repo = SongRepository(db)
    song = repo.fetch(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    song.acoustid_fingerprint_status = "skipped"
    db.commit()
    logger.info("Marked song %s as fingerprint-skipped", song_id)
    return {"status": "skipped"}


@router.post("/{song_id}/analyze-vocal-range", status_code=200)
async def analyze_vocal_range(
    song_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        raise HTTPException(status_code=404, detail="Vocals stem not found — song may not be processed yet")

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: detect_vocal_range(vocals_path, lambda msg: logger.debug("VocalRange: %s", msg)),
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Could not detect vocal range (insufficient voiced frames)")

    low, high = result
    repo.update(song_id, vocal_range_low=low, vocal_range_high=high)
    logger.info("Vocal range detected for song %s: %s – %s", song_id, low, high)
    return {"vocal_range_low": low, "vocal_range_high": high}


@router.post("/{song_id}/fingerprint", status_code=202)
async def fingerprint_single_song_endpoint(
    song_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    """Validate a YouTube replacement track with AcoustID before processing."""
    from pathlib import Path
    import shutil
    import uuid

    from app.services.youtube_service import YouTubeService
    from app.services.acoustid_service import AcoustIdService
    from app.schemas.song import ReplacementValidationResponse

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
        logger.error("YouTube validation failed for song %s: %s", song_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post("/{song_id}/validate-upload-replacement", status_code=200)
async def validate_upload_replacement(
    song_id: str,
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Validate an uploaded replacement track with AcoustID before processing."""
    from pathlib import Path
    import tempfile
    import shutil

    from app.services.acoustid_service import AcoustIdService
    from app.schemas.song import ReplacementValidationResponse

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
        logger.error("Upload validation failed for song %s: %s", song_id, e, exc_info=True)
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
    current_user: User = Depends(get_current_user),
):
    """Replace a song's audio source with a YouTube Music track and reprocess."""
    from datetime import datetime, timezone

    from app.db.models import JobStatus
    from app.repositories import JobRepository
    from app.services.youtube_service import YouTubeService

    song_repo = SongRepository(db)
    db_song = song_repo.fetch(song_id)
    if not db_song:
        raise HTTPException(status_code=404, detail="Song not found")

    job_repository = JobRepository()
    active_jobs = job_repository.get_jobs_by_status(
        [JobStatus.PENDING, JobStatus.PROCESSING, JobStatus.DOWNLOADING]
    )
    if any(j.song_id == song_id for j in active_jobs):
        raise HTTPException(status_code=409, detail="Song is already being processed")

    song_repo.update(
        song_id,
        acoustid_fingerprint_status="not_checked",
        acoustid_score=None,
        musicbrainz_recording_id=None,
        bpm=None,
        chords_data=None,
        vocal_range_low=None,
        vocal_range_high=None,
        loudness_dbfs=None,
        gain_db=None,
        engine_type=None,
    )

    FileService().delete_song_files(song_id)

    job_id = YouTubeService().download_and_process_async(
        video_id_or_url=request.video_id,
        song_id=song_id,
        artist=request.artist or db_song.artist,
        title=request.title or db_song.title,
        engine_type=request.engine_type,
    )
    logger.info("replace-youtube: queued job %s for song %s", job_id, song_id)
    return {"jobId": job_id, "status": "pending"}


@router.post("/{song_id}/replace-upload", status_code=202)
async def replace_song_upload(
    song_id: str,
    audio_file: UploadFile = File(...),
    engine_type: str = Form(default="three_track"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replace a song's audio source with an uploaded MP3 and reprocess."""
    from datetime import datetime, timezone

    from app.db.models import Job, JobStatus
    from app.repositories import JobRepository

    song_repo = SongRepository(db)
    db_song = song_repo.fetch(song_id)
    if not db_song:
        raise HTTPException(status_code=404, detail="Song not found")
    if not (audio_file.content_type or "").startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file")

    valid_engines = {"demucs", "roformer", "hybrid", "clean_backing", "three_track"}
    if engine_type not in valid_engines:
        raise HTTPException(status_code=400, detail=f"engine_type must be one of: {valid_engines}")

    job_repository = JobRepository()
    active_jobs = job_repository.get_jobs_by_status(
        [JobStatus.PENDING, JobStatus.PROCESSING, JobStatus.DOWNLOADING]
    )
    if any(j.song_id == song_id for j in active_jobs):
        raise HTTPException(status_code=409, detail="Song is already being processed")

    song_repo.update(
        song_id,
        acoustid_fingerprint_status="not_checked",
        acoustid_score=None,
        musicbrainz_recording_id=None,
        bpm=None,
        chords_data=None,
        vocal_range_low=None,
        vocal_range_high=None,
        loudness_dbfs=None,
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
