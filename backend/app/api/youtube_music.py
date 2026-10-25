"""
FastAPI router for YouTube Music search and browse endpoints.

The routes are plain `def`: ytmusicapi blocks, so FastAPI runs them in its
threadpool instead of on the event loop every other request shares.

YouTube Music failing is a 502; an unknown artist or album is a 404.
"""

import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.exceptions import NotFoundError
from app.services.song_intake_service import attach_library_entries
from app.services.youtube_music_service import (
    YoutubeMusicService,
    group_search_songs,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/youtube-music", tags=["youtube-music"])

YOUTUBE_MUSIC_FAILED = "YouTube Music isn't answering right now. Try again in a moment."


class Thumbnail(BaseModel):
    url: str
    width: Optional[int] = None
    height: Optional[int] = None


class ArtistCredit(BaseModel):
    name: str
    id: Optional[str] = None


class LibraryEntry(BaseModel):
    """A song's copy in the library: ready, still processing, or failed."""

    status: Literal["ready", "processing", "failed"]
    songId: str


class YoutubeMusicSong(BaseModel):
    """One song, the same shape in search, popular songs and album tracks."""

    videoId: Optional[str] = None
    title: Optional[str] = None
    artists: List[ArtistCredit] = []
    # The artists as the one credit line the library stores
    artist: Optional[str] = None
    album: Optional[str] = None
    albumId: Optional[str] = None
    durationSeconds: Optional[int] = None
    isExplicit: bool = False
    thumbnails: List[Thumbnail] = []
    trackNumber: Optional[int] = None
    library: Optional[LibraryEntry] = None


class YoutubeMusicArtistResult(BaseModel):
    browseId: str
    name: str
    subscribers: Optional[str] = None
    thumbnails: List[Thumbnail] = []


class YoutubeMusicSearchResponse(BaseModel):
    """Song results sorted by what a guest is looking for."""

    bestMatch: Optional[YoutubeMusicSong] = None
    # The best match's song by other artists, or live, acoustic, remixed...
    otherVersions: List[YoutubeMusicSong] = []
    otherSongs: List[YoutubeMusicSong] = []
    artists: List[YoutubeMusicArtistResult] = []
    # Set when YouTube Music's top result for the query is this artist
    topArtistId: Optional[str] = None


class YoutubeMusicRelease(BaseModel):
    browseId: Optional[str] = None
    title: Optional[str] = None
    year: Optional[str] = None
    type: str
    thumbnails: List[Thumbnail] = []


class YoutubeMusicArtistInfo(BaseModel):
    id: str
    name: Optional[str] = None
    thumbnails: List[Thumbnail] = []
    description: Optional[str] = None
    subscribers: Optional[str] = None


class YoutubeMusicArtistResponse(BaseModel):
    artist: YoutubeMusicArtistInfo
    topSongs: List[YoutubeMusicSong] = []
    # More popular songs than topSongs: GET /artist/{id}/songs has them all
    hasMoreSongs: bool = False
    # Every album, oldest first
    albums: List[YoutubeMusicRelease] = []
    # Every single, oldest first
    singles: List[YoutubeMusicRelease] = []
    # Remix collections from the albums and singles, oldest first
    remixes: List[YoutubeMusicRelease] = []


class YoutubeMusicAlbumInfo(BaseModel):
    browseId: str
    title: Optional[str] = None
    artists: List[ArtistCredit] = []
    # "Album", "Single", "EP"
    type: Optional[str] = None
    year: Optional[str] = None
    thumbnails: List[Thumbnail] = []
    trackCount: int = 0


class YoutubeMusicAlbumResponse(BaseModel):
    album: YoutubeMusicAlbumInfo
    tracks: List[YoutubeMusicSong] = []


def _youtube_music_failed(what: str, e: Exception) -> HTTPException:
    logger.error("YouTube Music %s failed: %s", what, e, exc_info=True)
    return HTTPException(status_code=502, detail=YOUTUBE_MUSIC_FAILED)


@router.get("/search", response_model=YoutubeMusicSearchResponse)
def search_youtube_music(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of songs"),
    db: Session = Depends(get_db),
):
    """
    Search YouTube Music for songs and artists (up to 3).

    Songs come back as the best match, other versions of it, and other songs,
    each with its library copy's state.
    """
    try:
        results = YoutubeMusicService().search(q, limit=limit)
    except Exception as e:
        raise _youtube_music_failed(f"search for {q!r}", e)

    # Copies, so the cached results never carry one request's library state
    songs = [dict(song) for song in results["songs"]]
    attach_library_entries(db, songs)

    return YoutubeMusicSearchResponse(
        **group_search_songs(songs),
        artists=results["artists"],
        topArtistId=results.get("topArtistId"),
    )


@router.get("/suggestions", response_model=List[str])
def get_search_suggestions(
    q: str = Query(..., min_length=1, description="What's been typed so far"),
):
    """Search suggestions for a partly typed query."""
    try:
        return YoutubeMusicService().get_suggestions(q)
    except Exception as e:
        raise _youtube_music_failed(f"suggestions for {q!r}", e)


@router.get("/artist/{artist_id}", response_model=YoutubeMusicArtistResponse)
def get_artist(artist_id: str, db: Session = Depends(get_db)):
    """
    An artist's info, first popular songs, and every album, single and remix
    collection.

    `hasMoreSongs` says whether /artist/{id}/songs has more than these.
    """
    try:
        result = YoutubeMusicService().get_artist(artist_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise _youtube_music_failed(f"artist {artist_id}", e)

    result = {**result, "topSongs": [dict(s) for s in result["topSongs"]]}
    attach_library_entries(db, result["topSongs"])
    return result


@router.get("/artist/{artist_id}/songs", response_model=List[YoutubeMusicSong])
def get_artist_songs(artist_id: str, db: Session = Depends(get_db)):
    """Every one of the artist's popular songs, for "Show all popular songs"."""
    try:
        songs = YoutubeMusicService().get_artist_songs(artist_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise _youtube_music_failed(f"songs for artist {artist_id}", e)

    songs = [dict(s) for s in songs]
    attach_library_entries(db, songs)
    return songs


@router.get("/album/{album_id}/tracks", response_model=YoutubeMusicAlbumResponse)
def get_album_tracks(album_id: str, db: Session = Depends(get_db)):
    """An album's info and tracks, each with its library copy's state."""
    try:
        result = YoutubeMusicService().get_album_tracks(album_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise _youtube_music_failed(f"album {album_id}", e)

    result = {**result, "tracks": [dict(t) for t in result["tracks"]]}
    attach_library_entries(db, result["tracks"])
    return result
