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

from app.config import get_config
from app.db.database import SessionLocal
from app.db.models.song import DbSong
from app.repositories.song_repository import SongRepository
from app.schemas.song import (
    ArtistInfo,
    ArtistSearchResponse,
    PaginationInfo,
    SongCreateRequest,
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
    limit: Optional[int] = Query(None, ge=1, le=500, description="Maximum number of songs to return"),
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

    # Validate sort_by
    valid_sort_fields = {"date_added", "title", "artist", "album", "year"}
    if sort_by not in valid_sort_fields:
        sort_by = "date_added"

    if direction.lower() not in ["asc", "desc"]:
        direction = "desc"

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
        raise HTTPException(status_code=500, detail=f"Failed to retrieve songs: {str(e)}")


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
            pagination=PaginationInfo(total=0, limit=limit, offset=offset, hasMore=False),
        )

    if direction not in ["asc", "desc"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort direction: {direction}. Must be 'asc' or 'desc'",
        )

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
    limit: int = Query(20, ge=1, le=500, description="Maximum number of songs to return"),
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
    
    # Validate sort field
    valid_sorts = {"title", "album", "year", "dateAdded", "date_added"}
    if sort not in valid_sorts:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field: {sort}. Must be one of: title, album, year, dateAdded",
        )
    
    # Map camelCase to snake_case for database field
    sort_field_map = {
        "title": "title",
        "album": "album", 
        "year": "year",
        "dateAdded": "date_added",
        "date_added": "date_added",
    }
    db_sort_field = sort_field_map.get(sort, "title")
    
    if direction not in ["asc", "desc"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort direction: {direction}. Must be 'asc' or 'desc'",
        )
    
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
        logger.error(f"Error fetching songs for artist '{artist_name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get songs for artist: {str(e)}",
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
        raise HTTPException(status_code=500, detail=f"Failed to get song details: {str(e)}")


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
        update_fields = {}
        update_dict = update_data.model_dump(exclude_unset=True)

        # Handle field mapping (camelCase to snake_case)
        field_mapping = {
            "syncedLyrics": "synced_lyrics",
            "plainLyrics": "plain_lyrics",
            "releaseDate": "release_date",
            "itunesTrackId": "itunes_track_id",
            "itunesArtistId": "itunes_artist_id",
            "itunesCollectionId": "itunes_collection_id",
            "itunesArtworkUrls": "itunes_artwork_urls",
            "itunesExplicit": "itunes_explicit",
            "itunesPreviewUrl": "itunes_preview_url",
            "trackTimeMillis": "track_time_millis",
        }

        for key, value in update_dict.items():
            if value is not None:
                db_field = field_mapping.get(key, key)
                # Serialize list fields to JSON for TEXT columns
                if db_field == "itunes_artwork_urls" and isinstance(value, list):
                    import json
                    update_fields[db_field] = json.dumps(value)
                else:
                    update_fields[db_field] = value

        if update_fields:
            updated_song = repo.update(song_id, **update_fields)
            if not updated_song:
                raise HTTPException(
                    status_code=500, detail="Failed to update song metadata"
                )
            return updated_song.to_dict()

        return db_song.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating song: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update song: {str(e)}")


@router.delete("/{song_id}")
async def delete_song(song_id: str, db: Session = Depends(get_db)):
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
        raise HTTPException(status_code=500, detail=f"Failed to get thumbnail: {str(e)}")


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
    valid_track_types = ["vocals", "instrumental", "original"]

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

        track_file = song_dir / f"{track_type}.mp3"

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
        raise HTTPException(status_code=500, detail=f"Failed to download track: {str(e)}")
