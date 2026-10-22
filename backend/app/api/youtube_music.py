"""
FastAPI router for YouTube Music search and browse endpoints.
"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

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
    failedSongId: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class YoutubeMusicArtistSearchResult(BaseModel):
    """Individual YouTube Music artist search result."""

    browseId: str
    name: str
    subscribers: Optional[str] = None
    thumbnails: List[dict] = []

    model_config = ConfigDict(extra="allow")


class YoutubeMusicSearchResponse(BaseModel):
    """Response model for YouTube Music search."""

    artists: List[YoutubeMusicArtistSearchResult] = []
    songs: List[dict] = []
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
    """Add existsInLibrary and failedSongId to a list of songs.

    A song is in the library only if a matching row (same video_id, or same
    artist + title, case-insensitive) isn't a failed one. When every match
    failed, failedSongId names the row to restart instead of adding a
    duplicate — so a failed copy never blocks adding the song again.
    """
    if not songs:
        return songs

    video_ids = [s.get("videoId") for s in songs if s.get("videoId")]
    # video_id -> [(song_id, status)], (artist, title) -> [(song_id, status)]
    rows_by_video_id: dict[str, list[tuple[str, str]]] = {}
    rows_by_artist_title: dict[tuple[str, str], list[tuple[str, str]]] = {}

    with get_db_session() as session:
        # Check by video_id for exact YouTube matches
        if video_ids:
            for song_id, video_id, status in (
                session.query(DbSong.id, DbSong.video_id, DbSong.status)
                .filter(DbSong.video_id.in_(video_ids))
                .all()
            ):
                rows_by_video_id.setdefault(video_id, []).append((song_id, status))

        # Check by artist + title for fuzzy matches (case-insensitive)
        for song in songs:
            artist = (song.get("artist") or "").strip()
            title = (song.get("title") or "").strip()
            if artist and title:
                rows_by_artist_title[(artist.lower(), title.lower())] = (
                    session.query(DbSong.id, DbSong.status)
                    .filter(DbSong.artist.ilike(artist), DbSong.title.ilike(title))
                    .all()
                )

    for song in songs:
        artist = (song.get("artist") or "").strip().lower()
        title = (song.get("title") or "").strip().lower()
        # video_id matches first, so a failed exact match is preferred below
        matches = rows_by_video_id.get(song.get("videoId"), []) + list(
            rows_by_artist_title.get((artist, title), [])
        )
        working = [song_id for song_id, status in matches if status != "error"]
        failed = [song_id for song_id, status in matches if status == "error"]

        song["existsInLibrary"] = bool(working)
        song["failedSongId"] = failed[0] if failed and not working else None

    return songs


@router.get("/search", response_model=YoutubeMusicSearchResponse)
async def search_youtube_music(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
):
    """
    Search YouTube Music for artists and songs.

    Returns artists (max 3) and songs matching the query, with existsInLibrary flag
    on songs indicating if they're already in the karaoke library.
    """
    try:
        service = YoutubeMusicService()
        combined = service.search_combined(q, limit=limit)

        # Add existsInLibrary flag to songs
        songs = _add_exists_in_library_flags(combined.get("songs", []))

        return YoutubeMusicSearchResponse(
            artists=combined.get("artists", []), songs=songs, error=None
        )

    except Exception as e:
        logger.error("YouTube Music search failed: %s", e, exc_info=True)
        return YoutubeMusicSearchResponse(artists=[], songs=[], error=str(e))


@router.get("/artist/{artist_id}", response_model=YoutubeMusicArtistResponse)
async def get_artist(
    artist_id: str,
    limit: int = Query(12, ge=1, le=50, description="Number of top songs to return"),
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


@router.get("/artist/{artist_id}/releases")
async def get_artist_releases(
    artist_id: str,
    channel_id: str = Query(
        ..., description="Artist channel ID from albumsMore/singlesMore"
    ),
    params: str = Query(
        ..., description="Pagination params from albumsMore/singlesMore"
    ),
):
    """
    Fetch all albums or singles for an artist (load more).

    Called when the initial artist response has albumsMore/singlesMore pagination metadata,
    indicating YouTube Music has more results than the initial 10.
    """
    try:
        service = YoutubeMusicService()
        releases = service.get_all_artist_releases(channel_id, params)
        return {"data": releases, "error": None}
    except Exception as e:
        logger.error(
            "Failed to get releases for artist %s: %s", artist_id, e, exc_info=True
        )
        return {"data": None, "error": str(e)}


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
