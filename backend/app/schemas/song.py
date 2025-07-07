from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class Song(BaseModel):
    id: str
    title: str
    artist: str
    durationMs: Optional[int] = None
    dateAdded: Optional[datetime] = None

    # File paths (API URLs)
    vocalPath: Optional[str] = None
    instrumentalPath: Optional[str] = None
    originalPath: Optional[str] = None
    coverArt: Optional[str] = None
    thumbnail: Optional[str] = None

    # Source
    source: Optional[str] = None
    sourceUrl: Optional[str] = None
    videoId: Optional[str] = None

    # YouTube data
    uploader: Optional[str] = None
    uploaderId: Optional[str] = None
    channel: Optional[str] = None
    channelId: Optional[str] = None
    channelName: Optional[str] = None
    description: Optional[str] = None
    uploadDate: Optional[datetime] = None
    youtubeThumbnailUrls: Optional[List[str]] = None
    youtubeTags: Optional[List[str]] = None
    youtubeCategories: Optional[List[str]] = None
    youtubeChannelId: Optional[str] = None
    youtubeChannelName: Optional[str] = None
    youtubeRawMetadata: Optional[Any] = None  # JSON object

    # Metadata
    mbid: Optional[str] = None
    album: Optional[str] = None
    releaseId: Optional[str] = None
    releaseDate: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    language: Optional[str] = None

    # Lyrics
    lyrics: Optional[str] = None
    syncedLyrics: Optional[str] = None

    # iTunes data
    itunesArtistId: Optional[int] = None
    itunesCollectionId: Optional[int] = None
    trackTimeMillis: Optional[int] = None
    itunesExplicit: Optional[bool] = None
    itunesPreviewUrl: Optional[str] = None
    itunesArtworkUrls: Optional[List[str]] = None  # JSON array

    status: str = "processed"

    class Config:
        orm_mode = True


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
    lyrics: Optional[str] = None
    synced_lyrics: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
