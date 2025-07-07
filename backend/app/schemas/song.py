"""
Song API schemas for Open Karaoke Studio.

These are used for API validation and serialization only.
The actual database model is DbSong in db/models/song.py
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Song(BaseModel):
    """Main Song API model - matches frontend expectations"""

    id: str
    title: str
    artist: str
    durationMs: Optional[int] = None
    favorite: bool = False
    dateAdded: Optional[datetime] = None

    # File paths (API URLs)
    vocalPath: Optional[str] = None
    instrumentalPath: Optional[str] = None
    originalPath: Optional[str] = None
    coverArt: Optional[str] = None
    thumbnail: Optional[str] = None

    # YouTube data
    videoId: Optional[str] = None
    sourceUrl: Optional[str] = None
    uploader: Optional[str] = None
    uploaderId: Optional[str] = None
    channel: Optional[str] = None
    channelId: Optional[str] = None
    channelName: Optional[str] = None
    description: Optional[str] = None
    uploadDate: Optional[datetime] = None

    # Metadata
    mbid: Optional[str] = None
    metadataId: Optional[str] = None  # Alias for mbid
    album: Optional[str] = None
    releaseTitle: Optional[str] = None  # Legacy alias for album
    releaseId: Optional[str] = None
    releaseDate: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    language: Optional[str] = None

    # Lyrics
    lyrics: Optional[str] = None
    syncedLyrics: Optional[str] = None

    # System
    source: Optional[str] = None
    status: str = "processed"


class SongCreate(BaseModel):
    """Song creation schema - for new songs"""

    title: str
    artist: str = "Unknown Artist"
    video_id: Optional[str] = None
    source_url: Optional[str] = None
    duration: Optional[float] = None


class SongUpdate(BaseModel):
    """Song update schema - only updatable fields"""

    title: Optional[str] = None
    artist: Optional[str] = None
    favorite: Optional[bool] = None
    lyrics: Optional[str] = None
    synced_lyrics: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
