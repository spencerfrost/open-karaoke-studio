"""
Pydantic Schemas for Song objects.
"""
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Pydantic Models for Songs
# ============================================================================

class SongResponse(BaseModel):
    """Full song response model"""

    id: str
    title: str
    artist: str
    duration: Optional[float] = None
    dateAdded: Optional[datetime] = None

    # File paths (API URLs)
    vocalPath: Optional[str] = None
    instrumentalPath: Optional[str] = None
    originalPath: Optional[str] = None
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
    youtubeRawMetadata: Optional[Any] = None

    # Metadata
    mbid: Optional[str] = None
    album: Optional[str] = None
    releaseId: Optional[str] = None
    releaseDate: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    language: Optional[str] = None

    # Lyrics
    plainLyrics: Optional[str] = None
    syncedLyrics: Optional[str] = None

    # iTunes data
    itunesArtistId: Optional[int] = None
    itunesCollectionId: Optional[int] = None
    trackTimeMillis: Optional[int] = None
    itunesExplicit: Optional[bool] = None
    itunesPreviewUrl: Optional[str] = None

    status: str = "processed"

    class Config:
        from_attributes = True


class SongCreateRequest(BaseModel):
    """Request model for creating a new song"""

    id: Optional[str] = Field(None, description="Optional song ID, will be generated if not provided")
    title: str = Field(..., min_length=1, max_length=200, description="Song title")
    artist: str = Field(..., min_length=1, max_length=200, description="Artist name")
    album: Optional[str] = Field(None, max_length=200, description="Album name")
    duration: Optional[float] = Field(None, ge=0, description="Song duration in seconds")
    source: Optional[str] = Field(None, max_length=50, description="Source of the song")
    video_id: Optional[str] = Field(None, max_length=100, description="YouTube video ID")

    @field_validator("title", "artist")
    def validate_non_empty_strings(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Field cannot be empty")
        return v.strip()


class SongUpdateRequest(BaseModel):
    """Request model for updating a song"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    artist: Optional[str] = Field(None, min_length=1, max_length=200)
    album: Optional[str] = Field(None, max_length=200)
    duration: Optional[float] = Field(None, ge=0)
    genre: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=50)
    plainLyrics: Optional[str] = None
    syncedLyrics: Optional[str] = None

    @field_validator("title", "artist")
    def validate_non_empty_strings(cls, v):
        if v is not None and (not v or v.strip() == ""):
            raise ValueError("Field cannot be empty")
        return v.strip() if v else v


class PaginationInfo(BaseModel):
    """Pagination metadata"""

    total: int
    limit: int
    offset: int
    hasMore: bool


class SongSearchResponse(BaseModel):
    """Response model for song search"""

    songs: List[SongResponse]
    pagination: PaginationInfo


class ArtistInfo(BaseModel):
    """Artist information with song count"""

    artist: str
    songCount: int
    songs: List[SongResponse]


class ArtistSearchResponse(BaseModel):
    """Response model for artist-grouped search"""

    artists: List[ArtistInfo]
    totalSongs: int
    totalArtists: int
    pagination: PaginationInfo