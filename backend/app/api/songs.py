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
from app.db.models.song import DbSong
from app.db.models.user import User
from app.repositories.lyrics_repository import LyricsRepository
from app.repositories.song_repository import SongRepository
from app.schemas.song import (
    ArtistInfo,
    ArtistSearchResponse,
    PaginationInfo,
    SongCreateRequest,
    SongReprocessRequest,
    SongResponse,
    SongSearchResponse,
    SongUpdateRequest,
)
from app.services.file_service import FileService
from fastapi import APIRouter, Depends, HTTPException, Query
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
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


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
    logger.info("Received request for /api/songs")

    # Validate sort_by and direction
    sort_by = validate_sort_field(sort_by, VALID_SONG_SORT_FIELDS)
    direction = validate_direction(direction)

    try:
        repo = SongRepository(db)
        songs = repo.fetch_all(
            sort_by=sort_by, direction=direction, limit=limit, offset=offset
        )

        response_data = [song.to_dict() for song in songs]
        logger.info(f"Returning {len(response_data)} songs.")
        return response_data

    except Exception as e:
        logger.error(f"Error retrieving songs: {e}", exc_info=True)
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
        logger.error(f"Error searching songs: {e}", exc_info=True)
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
            db.query(DbSong.artist, func.count(DbSong.id).label("song_count"))
            .group_by(DbSong.artist)
            .order_by(DbSong.artist)
        )

        # Apply search filter if provided
        if search and search.strip():
            query = query.filter(DbSong.artist.ilike(f"%{search.strip()}%"))

        total = query.count()

        if limit:
            query = query.offset(offset).limit(limit)

        results = query.all()

        return {
            "artists": [
                {
                    "name": artist,
                    "songCount": count,
                    "firstLetter": artist[0].upper() if artist else "?",
                }
                for artist, count in results
            ],
            "pagination": {
                "total": total,
                "limit": limit or total,
                "offset": offset,
                "hasMore": limit is not None and offset + limit < total,
            },
        }

    except Exception as e:
        logger.error(f"Error getting artists: {e}", exc_info=True)
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
        base_query = db.query(DbSong).filter(DbSong.artist == artist_name)

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
        logger.error(f"Error fetching chords for song {song_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get chord data: {str(e)}"
        )


@router.get("/{song_id}", response_model=SongResponse)
async def get_song_details(song_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific song.
    """
    logger.info(f"Received request for song details: {song_id}")

    try:
        repo = SongRepository(db)
        db_song = repo.fetch(song_id)

        if not db_song:
            raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

        return db_song.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching song details: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get song details: {str(e)}"
        )


@router.post("", response_model=SongResponse, status_code=201)
async def create_song(song_data: SongCreateRequest, db: Session = Depends(get_db)):
    """
    Create a new song with basic information.
    """
    song_id = song_data.id or str(uuid.uuid4())
    logger.info(f"Creating new song with ID: {song_id}")

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

        # Create the song directory
        try:
            file_service = FileService()
            song_dir = file_service.get_song_directory(song_id)
            song_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory for song: {song_dir}")
        except Exception as e:
            logger.warning(f"Error creating directory for song {song_id}: {e}")

        response = song.to_dict()
        response["status"] = "pending"

        logger.info(f"Successfully created song: {song_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating song: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create song: {str(e)}")


@router.patch("/{song_id}", response_model=SongResponse)
async def update_song(
    song_id: str, update_data: SongUpdateRequest, db: Session = Depends(get_db)
):
    """
    Update a song with any provided fields.
    """
    logger.info(f"Received request to update song {song_id}")

    try:
        repo = SongRepository(db)
        db_song = repo.fetch(song_id)

        if not db_song:
            raise HTTPException(status_code=404, detail=f"Song not found: {song_id}")

        # Build update fields from provided data
        update_dict = update_data.model_dump(exclude_unset=True)

        # Extract lyrics fields for separate handling via LyricsRepository
        lyrics_data = extract_lyrics_fields(update_dict)

        # Map remaining fields to DB columns
        update_fields = map_fields_to_db(update_dict)

        if update_fields:
            updated_song = repo.update(song_id, **update_fields)
            if not updated_song:
                raise HTTPException(
                    status_code=500, detail="Failed to update song metadata"
                )

        # Save lyrics via LyricsRepository
        if lyrics_data:
            lyrics_repo = LyricsRepository(db)
            if "plainLyrics" in lyrics_data:
                if lyrics_data["plainLyrics"]:
                    lyrics_repo.save_lyrics(
                        song_id, "plain", lyrics_data["plainLyrics"], source="manual"
                    )
                else:
                    lyrics_repo.deactivate_type(song_id, "plain")
            if "syncedLyrics" in lyrics_data:
                if lyrics_data["syncedLyrics"]:
                    lyrics_repo.save_lyrics(
                        song_id, "synced", lyrics_data["syncedLyrics"], source="manual"
                    )
                else:
                    lyrics_repo.deactivate_type(song_id, "synced")

        # Re-fetch to get updated lyrics relationship
        db_song = repo.fetch(song_id)
        return db_song.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating song: {e}", exc_info=True)
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
    logger.info(f"Received request to delete song: {song_id}")

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
            logger.warning(f"Error deleting files for song {song_id}: {e}")

        logger.info(f"Successfully deleted song: {song_id}")
        return {"message": "Song deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting song: {e}", exc_info=True)
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
        logger.error(f"Error serving thumbnail: {e}", exc_info=True)
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
    logger.info(f"Download request for song '{song_id}', track type '{track_type}'")

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
            logger.error(f"Attempted download outside library bounds: {track_file}")
            raise HTTPException(status_code=403, detail="Access denied")

        return FileResponse(
            track_file,
            media_type="audio/mpeg",
            filename=f"{track_type}.mp3",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading track: {e}", exc_info=True)
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
        logger.error(f"Error starting reprocess: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to start reprocessing: {str(e)}"
        )
