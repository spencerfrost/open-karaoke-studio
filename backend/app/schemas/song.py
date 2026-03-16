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

    thumbnail: Optional[str] = None

    # Source
    source: Optional[str] = None
    sourceUrl: Optional[str] = None
    videoId: Optional[str] = None

    # Metadata
    album: Optional[str] = None
    releaseDate: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None

    # Lyrics
    plainLyrics: Optional[str] = None
    syncedLyrics: Optional[str] = None

    # iTunes metadata
    itunesTrackId: Optional[int] = None
    itunesExplicit: Optional[bool] = None
    itunesPreviewUrl: Optional[str] = None  # 30-sec preview for song identification
    itunesArtworkUrls: Optional[str] = None  # JSON string

    # YouTube thumbnail URLs (fallback for artwork)
    youtubeThumbnailUrls: Optional[str] = None  # JSON string

    # Processing metadata
    engineType: Optional[str] = None  # Separation engine used
    bpm: Optional[float] = None  # Beats per minute for count-in timing
    chordsData: Optional[list] = None  # Chord detection data
    vocalRangeLow: Optional[str] = None  # Lowest sung note, e.g. "G2"
    vocalRangeHigh: Optional[str] = None  # Highest sung note, e.g. "E5"

    # Loudness normalization
    loudnessDbfs: Optional[float] = None  # RMS loudness in dBFS
    gainDb: Optional[float] = None  # Gain correction to reach -14 dBFS target

    status: str = "processed"

    class Config:
        from_attributes = True


class SongCreateRequest(BaseModel):
    """Request model for creating a new song"""

    id: Optional[str] = Field(
        None, description="Optional song ID, will be generated if not provided"
    )
    title: str = Field(..., min_length=1, max_length=200, description="Song title")
    artist: str = Field(..., min_length=1, max_length=200, description="Artist name")
    album: Optional[str] = Field(None, max_length=200, description="Album name")
    duration: Optional[float] = Field(
        None, ge=0, description="Song duration in seconds"
    )
    source: Optional[str] = Field(None, max_length=50, description="Source of the song")
    video_id: Optional[str] = Field(
        None, max_length=100, description="YouTube video ID"
    )

    @field_validator("title", "artist")
    def validate_non_empty_strings(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Field cannot be empty")
        return v.strip()


class SongUpdateRequest(BaseModel):
    """Request model for updating a song"""

    # Basic metadata
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    artist: Optional[str] = Field(None, min_length=1, max_length=200)
    album: Optional[str] = Field(None, max_length=200)
    duration: Optional[float] = Field(None, ge=0)
    genre: Optional[str] = Field(None, max_length=100)
    year: Optional[int] = Field(None, ge=1800, le=2100)
    releaseDate: Optional[str] = Field(None, max_length=50)

    # Lyrics
    plainLyrics: Optional[str] = None
    syncedLyrics: Optional[str] = None

    # iTunes metadata
    itunesTrackId: Optional[int] = Field(None, description="iTunes track ID")
    itunesArtworkUrls: Optional[List[str]] = Field(
        None, description="iTunes artwork URLs"
    )
    itunesExplicit: Optional[bool] = Field(
        None, description="iTunes explicit content flag"
    )
    itunesPreviewUrl: Optional[str] = Field(
        None, max_length=500, description="iTunes 30-sec preview URL"
    )

    # Audio analysis
    bpm: Optional[float] = Field(None, ge=30, le=300, description="Beats per minute")
    loudnessDbfs: Optional[float] = Field(None, description="RMS loudness in dBFS")
    gainDb: Optional[float] = Field(None, ge=-20, le=20, description="Gain correction in dB")

    @field_validator("title", "artist")
    def validate_non_empty_strings(cls, v):
        if v is not None and (not v or v.strip() == ""):
            raise ValueError("Field cannot be empty")
        return v.strip() if v else v


class SongReprocessRequest(BaseModel):
    """Request model for reprocessing a song with a different engine"""

    engine_type: str = Field(
        default="three_track",
        description="Separation engine to use (three_track, demucs, roformer, hybrid, clean_backing)",
    )

    @field_validator("engine_type")
    @classmethod
    def validate_engine_type(cls, v: str) -> str:
        valid_engines = {"demucs", "roformer", "hybrid", "clean_backing", "three_track"}
        if v not in valid_engines:
            raise ValueError(
                f"Invalid engine_type. Must be one of: {', '.join(sorted(valid_engines))}"
            )
        return v


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
