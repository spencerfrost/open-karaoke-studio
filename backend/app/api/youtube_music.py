"""
FastAPI router for YouTube Music search and browse endpoints.
"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


from app.db.database import get_db_session
from app.db.models.song import DbSong
from app.services.youtube_music_service import YoutubeMusicService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/youtube-music", tags=["youtube-music"])


class YoutubeMusicSearchResult(BaseModel):
    """Individual YouTube Music search result."""
    videoId: Optional[str] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    artistId: Optional[str] = None
    album: Optional[str] = None
    albumId: Optional[str] = None
    thumbnailUrl: Optional[str] = None
    duration: Optional[str] = None
    existsInLibrary: bool = False

    class Config:
        extra = "allow"


class YoutubeMusicSearchResponse(BaseModel):
    """Response model for YouTube Music search."""
    results: List[dict]
    error: Optional[str] = None


class YoutubeMusicArtistResponse(BaseModel):
    """Response model for YouTube Music artist details."""
    data: Optional[dict] = None
    error: Optional[str] = None


class YoutubeMusicAlbumResponse(BaseModel):
    """Response model for YouTube Music album tracks."""
    data: Optional[dict] = None
    error: Optional[str] = None


def _add_exists_in_library_flags(songs: List[dict]) -> List[dict]:
    """Add existsInLibrary flag to a list of songs."""
    if not songs:
        return songs

    video_ids = [s.get("videoId") for s in songs if s.get("videoId")]
    existing_video_ids: set = set()
    existing_songs_by_artist_title: set = set()

    with get_db_session() as session:
        # Check by video_id for exact YouTube matches
        if video_ids:
            existing_songs = session.query(DbSong.video_id).filter(
                DbSong.video_id.in_(video_ids)
            ).all()
            existing_video_ids = {song.video_id for song in existing_songs}

        # Check by artist + title for fuzzy matches (case-insensitive)
        for song in songs:
            artist = song.get("artist", "")
            if artist:
                artist = artist.strip()
            title = song.get("title", "")
            if title:
                title = title.strip()
            if artist and title:
                existing = session.query(DbSong.id).filter(
                    DbSong.artist.ilike(artist),
                    DbSong.title.ilike(title)
                ).first()
                if existing:
                    existing_songs_by_artist_title.add((artist.lower(), title.lower()))

    # Add existsInLibrary flag to each song
    for song in songs:
        video_id = song.get("videoId")
        artist = song.get("artist", "")
        if artist:
            artist = artist.strip().lower()
        title = song.get("title", "")
        if title:
            title = title.strip().lower()

        song["existsInLibrary"] = (
            video_id in existing_video_ids or
            (artist, title) in existing_songs_by_artist_title
        )

    return songs


@router.get("/search", response_model=YoutubeMusicSearchResponse)
async def search_youtube_music(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results")
):
    """
    Search YouTube Music for songs.
    
    Returns a list of song results matching the query, with existsInLibrary flag
    indicating if the song is already in the karaoke library.
    """
    try:
        service = YoutubeMusicService()
        results = service.search_songs(q, limit=limit)

        # Check which songs already exist in library
        video_ids = [r.get("videoId") for r in results if r.get("videoId")]
        existing_video_ids: set = set()
        existing_songs_by_artist_title: set = set()

        if video_ids or results:
            with get_db_session() as session:
                # Check by video_id for exact YouTube matches
                if video_ids:
                    existing_songs = session.query(DbSong.video_id).filter(
                        DbSong.video_id.in_(video_ids)
                    ).all()
                    existing_video_ids = {song.video_id for song in existing_songs}

                # Check by artist + title for fuzzy matches (case-insensitive)
                for result in results:
                    artist = result.get("artist", "")
                    if artist:
                        artist = artist.strip()
                    title = result.get("title", "")
                    if title:
                        title = title.strip()
                    if artist and title:
                        existing = session.query(DbSong.id).filter(
                            DbSong.artist.ilike(artist),
                            DbSong.title.ilike(title)
                        ).first()
                        if existing:
                            existing_songs_by_artist_title.add((artist.lower(), title.lower()))

        # Add existsInLibrary flag to each result
        for result in results:
            video_id = result.get("videoId")
            artist = result.get("artist", "")
            if artist:
                artist = artist.strip().lower()
            title = result.get("title", "")
            if title:
                title = title.strip().lower()

            result["existsInLibrary"] = (
                video_id in existing_video_ids or
                (artist, title) in existing_songs_by_artist_title
            )

        return YoutubeMusicSearchResponse(results=results, error=None)

    except Exception as e:
        logger.error("YouTube Music search failed: %s", e, exc_info=True)
        return YoutubeMusicSearchResponse(results=[], error=str(e))


@router.get("/artist/{artist_id}", response_model=YoutubeMusicArtistResponse)
async def get_artist(
    artist_id: str,
    limit: int = Query(12, ge=1, le=50, description="Number of top songs to return")
):
    """
    Get artist details including top songs and albums.
    
    Returns artist information with existsInLibrary flags on top songs.
    """
    try:
        service = YoutubeMusicService()
        result = service.get_artist(artist_id, top_songs_limit=limit)

        # Add existsInLibrary flag to top songs
        result["topSongs"] = _add_exists_in_library_flags(result.get("topSongs", []))

        return YoutubeMusicArtistResponse(data=result, error=None)

    except Exception as e:
        logger.error("Failed to get artist %s: %s", artist_id, e, exc_info=True)
        return YoutubeMusicArtistResponse(data=None, error=str(e))


@router.get("/album/{album_id}/tracks", response_model=YoutubeMusicAlbumResponse)
async def get_album_tracks(album_id: str):
    """
    Get all tracks from an album.
    
    Returns album track list with existsInLibrary flags.
    """
    try:
        service = YoutubeMusicService()
        result = service.get_album_tracks(album_id)

        # Add existsInLibrary flag to tracks
        result["tracks"] = _add_exists_in_library_flags(result.get("tracks", []))

        return YoutubeMusicAlbumResponse(data=result, error=None)

    except Exception as e:
        logger.error("Failed to get album tracks %s: %s", album_id, e, exc_info=True)
        return YoutubeMusicAlbumResponse(data=None, error=str(e))
