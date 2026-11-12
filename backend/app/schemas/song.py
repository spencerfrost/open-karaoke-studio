"""
Pydantic Schemas for Song objects.
"""

from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============================================================================
# Pydantic Models for Songs
# ============================================================================


class SongArtistRef(BaseModel):
    """Structured artist credit on a song."""

    id: int
    name: str
    role: str  # 'primary' | 'featured'
    # The name as this recording prints it, when it differs from `name`
    creditedAs: Optional[str] = None


class SongArtistCredit(BaseModel):
    """One artist credit a person sets: on a song, or splitting a collab."""

    name: str = Field(..., min_length=1, max_length=200)
    role: Literal["primary", "featured"]

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Artist name cannot be empty")
        return v


class AcoustIdSuggestion(BaseModel):
    """The recording AcoustID found when it named the song differently."""

    recordingId: str
    title: Optional[str] = None
    artist: Optional[str] = None


class SongResponse(BaseModel):
    """Full song response model"""

    id: str
    title: str
    artist: str
    duration: Optional[float] = None
    dateAdded: Optional[datetime] = None

    # Only three-track songs have a separate backing vocal stem
    backingVocalPath: Optional[str] = None
    thumbnail: Optional[str] = None

    # Source
    source: Optional[str] = None
    sourceUrl: Optional[str] = None
    videoId: Optional[str] = None
    # The video's picture is the album cover (an album track upload)
    videoIsAlbumArt: Optional[bool] = None

    # Metadata
    album: Optional[str] = None
    releaseDate: Optional[str] = None
    year: Optional[int] = None
    showName: Optional[str] = None  # Musical/soundtrack, e.g. "Wicked"
    language: Optional[str] = None  # Sung language, Whisper code ("en", "fr")
    # Lyrics
    # A person saved the lyrics; automatic runs only time them
    lyricsHandPicked: bool = False
    plainLyrics: Optional[str] = None
    syncedLyrics: Optional[str] = None
    wordSyncedLyrics: Optional[str] = None

    explicit: Optional[bool] = None
    # A person set the album name; automatic album lookups skip the song
    albumHandSet: bool = False

    # Relational IDs and computed cover URL
    artistId: Optional[int] = None
    albumId: Optional[int] = None
    albumCoverUrl: Optional[str] = None

    # Processing metadata
    engineType: Optional[str] = None  # Separation engine used
    vocalRangeLow: Optional[str] = None  # Lowest sung note, e.g. "G2"
    vocalRangeHigh: Optional[str] = None  # Highest sung note, e.g. "E5"

    # Loudness normalization
    loudnessLufs: Optional[float] = None  # EBU R128 integrated loudness
    truePeakDbtp: Optional[float] = None  # Loudest instant, in dB true peak
    gainDb: Optional[float] = None  # Correction the player applies

    # AcoustID fingerprinting
    musicbrainzRecordingId: Optional[str] = None
    acoustidScore: Optional[float] = None
    acoustidFingerprintStatus: Optional[str] = None
    acoustidSuggestion: Optional[AcoustIdSuggestion] = None
    metadataConfirmed: bool = False  # A person set the title/artist

    # Structured artist credits
    artists: List[SongArtistRef] = []

    status: str = "processed"
    errorMessage: Optional[str] = None
    failedAt: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SongCreateRequest(BaseModel):
    """Request model for creating a new song"""

    id: Optional[str] = Field(
        None, description="Optional song ID, will be generated if not provided"
    )
    title: str = Field(..., min_length=1, max_length=200, description="Song title")
    artist: str = Field(..., min_length=1, max_length=200, description="Artist name")
    album: Optional[str] = Field(None, max_length=200, description="Album name")
    show_name: Optional[str] = Field(
        None, max_length=200, description="Musical/soundtrack name, e.g. 'Wicked'"
    )
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
    year: Optional[int] = Field(None, ge=1800, le=2100)
    releaseDate: Optional[str] = Field(None, max_length=50)
    showName: Optional[str] = Field(None, max_length=200)
    # Whisper code ("fr"); an empty string clears it so it's detected again
    language: Optional[str] = Field(None, max_length=8)
    # The credit list, primaries first. Replaces `artist`: the text is rebuilt
    # from it.
    artists: Optional[List[SongArtistCredit]] = Field(None, min_length=1, max_length=20)

    # Lyrics
    plainLyrics: Optional[str] = None
    syncedLyrics: Optional[str] = None
    wordSyncedLyrics: Optional[str] = None

    # Audio analysis
    loudnessLufs: Optional[float] = Field(
        None, description="EBU R128 integrated loudness"
    )
    truePeakDbtp: Optional[float] = Field(None, description="True peak in dBTP")
    gainDb: Optional[float] = Field(
        None, ge=-20, le=20, description="Gain correction in dB"
    )

    @field_validator("title", "artist")
    def validate_non_empty_strings(cls, v):
        if v is not None and (not v or v.strip() == ""):
            raise ValueError("Field cannot be empty")
        return v.strip() if v else v


class SongReprocessRequest(BaseModel):
    """Request model for reprocessing a song with a different engine"""

    engine_type: str = Field(
        default="three_track",
        description=(
            "Separation engine to use "
            "(three_track, three_track_duality_v2, three_track_mel1143, "
            "demucs, roformer, hybrid, clean_backing)"
        ),
    )

    @field_validator("engine_type")
    @classmethod
    def validate_engine_type(cls, v: str) -> str:
        valid_engines = {
            "demucs",
            "roformer",
            "hybrid",
            "clean_backing",
            "three_track",
            "three_track_duality_v2",
            "three_track_mel1143",
        }
        if v not in valid_engines:
            raise ValueError(
                f"Invalid engine_type. Must be one of: {', '.join(sorted(valid_engines))}"
            )
        return v


class SongReplaceYouTubeRequest(BaseModel):
    """Request model for replacing a song's source with a YouTube Music track"""

    video_id: str = Field(..., min_length=1, max_length=100)
    title: Optional[str] = Field(None, max_length=200)
    artist: Optional[str] = Field(None, max_length=200)
    engine_type: str = Field(default="three_track")

    @field_validator("engine_type")
    @classmethod
    def validate_engine_type(cls, v: str) -> str:
        valid_engines = {
            "demucs",
            "roformer",
            "hybrid",
            "clean_backing",
            "three_track",
            "three_track_duality_v2",
            "three_track_mel1143",
        }
        if v not in valid_engines:
            raise ValueError(
                f"Invalid engine_type. Must be one of: {', '.join(sorted(valid_engines))}"
            )
        return v


class BulkDeleteOrphansRequest(BaseModel):
    """Request model for bulk-deleting orphaned library directories."""

    dir_names: List[str] = Field(..., min_length=1)


class BulkDeleteGhostsRequest(BaseModel):
    """Request model for bulk-deleting ghost DB records."""

    song_ids: List[str] = Field(..., min_length=1)


class FingerprintApplyRequest(BaseModel):
    """Request model for applying a selected AcoustID candidate to a song."""

    recording_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=200)
    artist: str = Field(..., min_length=1, max_length=200)
    score: float = Field(..., ge=0.0, le=1.0)


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


class MetadataIssue(BaseModel):
    """A single metadata quality issue detected on a song."""

    type: str
    label: str
    severity: Literal["error", "warning", "info"]


class FlaggedSong(BaseModel):
    """A song with one or more metadata quality issues."""

    id: str
    title: str
    artist: str
    date_added: Optional[str] = None
    source: Optional[str] = None
    status: str = "processed"
    issues: List[MetadataIssue]


class MetadataAuditResponse(BaseModel):
    """Response for the metadata quality audit endpoint."""

    flagged_songs: List[FlaggedSong]
    summary: dict
    total_songs_scanned: int
    total_flagged: int


class ReplacementValidationResponse(BaseModel):
    """Response for replacement audio validation with AcoustID"""

    validated: bool
    audioPath: Optional[str] = None  # Temp path if validation was successful
    acoustidStatus: str  # "matched" | "no_match" | "failed"
    acoustidScore: Optional[float] = None
    musicbrainzId: Optional[str] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    message: str  # Human-readable status message


class SplitArtistCreditsRequest(BaseModel):
    """Request body for POST /api/artists/{artist_id}/split-credits."""

    credits: List[SongArtistCredit] = Field(..., min_length=1)
