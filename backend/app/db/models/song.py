"""
Song-related models: Pydantic, SQLAlchemy, and helpers.
"""
from typing import Optional, Literal, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, UNKNOWN_ARTIST

SongStatus = Literal["processing", "queued", "processed", "error"]

class SongMetadata(BaseModel):
    title: Optional[str] = None
    artist: Optional[str] = None
    duration: Optional[float] = None
    favorite: bool = False
    dateAdded: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    coverArt: Optional[str] = None
    thumbnail: Optional[str] = None
    source: Optional[str] = None
    sourceUrl: Optional[str] = None
    videoId: Optional[str] = None
    videoTitle: Optional[str] = None
    uploader: Optional[str] = None
    uploaderId: Optional[str] = None
    channel: Optional[str] = None
    channelId: Optional[str] = None  # Phase 1A: Key YouTube field for karaoke
    description: Optional[str] = None
    uploadDate: Optional[datetime] = None
    mbid: Optional[str] = None
    releaseTitle: Optional[str] = None
    releaseId: Optional[str] = None
    releaseDate: Optional[str] = None
    genre: Optional[str] = None
    language: Optional[str] = None
    lyrics: Optional[str] = None
    syncedLyrics: Optional[str] = None
    
    # Phase 1B: iTunes "True Song Metadata" Fields
    itunesTrackId: Optional[int] = None          # iTunes track identifier
    itunesArtistId: Optional[int] = None         # iTunes artist identifier  
    itunesCollectionId: Optional[int] = None     # iTunes collection identifier
    trackTimeMillis: Optional[int] = None        # Official iTunes track duration (ms)
    itunesExplicit: Optional[bool] = None        # Content explicitness flag
    itunesPreviewUrl: Optional[str] = None       # Official preview URL
    itunesArtworkUrls: Optional[List[str]] = None # [artworkUrl30, artworkUrl60, artworkUrl100]
    
    # Phase 1B: YouTube "Video Source Context" Fields  
    youtubeDuration: Optional[float] = None      # Video duration (seconds) - separate from track duration
    youtubeThumbnailUrls: Optional[List[str]] = None # Selected thumbnail URLs
    youtubeTags: Optional[List[str]] = None      # Video tags for search/categorization
    youtubeCategories: Optional[List[str]] = None # Video categories
    youtubeChannelId: Optional[str] = None       # Channel ID for URL construction
    youtubeChannelName: Optional[str] = None     # Channel display name
    
    # Phase 1B: Raw JSON Backup Storage
    itunesRawMetadata: Optional[str] = None      # Complete iTunes response (JSON string)
    youtubeRawMetadata: Optional[str] = None     # Filtered YouTube response (JSON string)
    
    class Config:
        model_config = {"json_encoders": {datetime: lambda v: v.isoformat() if v else None}}

class Song(BaseModel):
    id: str
    title: str
    artist: str = UNKNOWN_ARTIST
    duration: Optional[float] = None
    status: SongStatus = "processed"
    videoId: Optional[str] = None
    uploader: Optional[str] = None
    uploaderId: Optional[str] = None
    channel: Optional[str] = None
    channelId: Optional[str] = None
    channelName: Optional[str] = None
    description: Optional[str] = None
    uploadDate: Optional[datetime] = None
    mbid: Optional[str] = None
    metadataId: Optional[str] = None  # Alias for mbid for frontend compatibility
    releaseTitle: Optional[str] = None
    releaseId: Optional[str] = None
    releaseDate: Optional[str] = None
    genre: Optional[str] = None
    language: Optional[str] = None
    lyrics: Optional[str] = None
    syncedLyrics: Optional[str] = None
    source: Optional[str] = None
    sourceUrl: Optional[str] = None
    year: Optional[int] = None
    favorite: bool = False
    dateAdded: Optional[datetime] = None
    coverArt: Optional[str] = None
    vocalPath: Optional[str] = None
    instrumentalPath: Optional[str] = None
    originalPath: Optional[str] = None
    thumbnail: Optional[str] = None
    album: Optional[str] = None  # Alias for releaseTitle for frontend compatibility
    
    class Config:
        model_config = {"json_encoders": {datetime: lambda v: v.isoformat() if v else None}}

class DbSong(Base):
    __tablename__ = "songs"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False, default=UNKNOWN_ARTIST)
    duration = Column(Float, nullable=True)
    favorite = Column(Boolean, default=False)
    date_added = Column(DateTime, default=datetime.now(timezone.utc))
    vocals_path = Column(String, nullable=True)
    instrumental_path = Column(String, nullable=True)
    original_path = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)
    cover_art_path = Column(String, nullable=True)
    source = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    video_id = Column(String, nullable=True)
    uploader = Column(String, nullable=True)
    uploader_id = Column(String, nullable=True)
    channel = Column(String, nullable=True)
    channel_id = Column(String, nullable=True)  # Phase 1A: Key YouTube field for karaoke
    description = Column(Text, nullable=True)
    upload_date = Column(DateTime, nullable=True)
    mbid = Column(String, nullable=True)
    album = Column(String, nullable=True)  # Renamed from release_title for better UX
    release_id = Column(String, nullable=True)
    release_date = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    genre = Column(String, nullable=True)
    language = Column(String, nullable=True)
    lyrics = Column(Text, nullable=True)
    synced_lyrics = Column(Text, nullable=True)
    channel_name = Column(String, nullable=True)  # Legacy field
    
    # Phase 1B: iTunes integration columns
    itunes_track_id = Column(Integer, nullable=True)
    itunes_artist_id = Column(Integer, nullable=True)  
    itunes_collection_id = Column(Integer, nullable=True)
    track_time_millis = Column(Integer, nullable=True)
    itunes_explicit = Column(Boolean, nullable=True)
    itunes_preview_url = Column(String, nullable=True)
    itunes_artwork_urls = Column(Text, nullable=True)    # JSON array as string

    # Phase 1B: Enhanced YouTube columns
    youtube_duration = Column(Integer, nullable=True)
    youtube_thumbnail_urls = Column(Text, nullable=True) # JSON array as string  
    youtube_tags = Column(Text, nullable=True)           # JSON array as string
    youtube_categories = Column(Text, nullable=True)     # JSON array as string
    youtube_channel_id = Column(String, nullable=True)
    youtube_channel_name = Column(String, nullable=True)

    # Phase 1B: Raw metadata storage
    itunes_raw_metadata = Column(Text, nullable=True)    # JSON string
    youtube_raw_metadata = Column(Text, nullable=True)   # JSON string
    
    queue_items = relationship("KaraokeQueueItem", back_populates="song", cascade="all, delete-orphan")
    def to_pydantic(self) -> Song:
        # Extract year from release_date if available
        year_value = None
        if self.year:
            year_value = self.year
        elif self.release_date:
            try:
                year_value = int(self.release_date.split('-')[0]) if '-' in str(self.release_date) else int(self.release_date)
            except (ValueError, AttributeError):
                year_value = None
        
        return Song(
            id=self.id,
            title=self.title,
            artist=self.artist,
            duration=self.duration,
            status="processed",
            videoId=self.video_id,
            uploader=self.uploader,
            uploaderId=self.uploader_id,
            channel=self.channel,
            channelId=self.channel_id,
            channelName=self.youtube_channel_name or self.channel_name,  # Prefer new field
            description=self.description,
            uploadDate=self.upload_date,
            mbid=self.mbid,
            metadataId=self.mbid,  # Alias for frontend compatibility
            releaseTitle=self.album,  # Keeping for backwards compatibility
            releaseId=self.release_id,
            releaseDate=self.release_date,
            genre=self.genre,
            language=self.language,
            lyrics=self.lyrics,
            syncedLyrics=self.synced_lyrics,
            source=self.source,
            sourceUrl=self.source_url,
            year=year_value,
            favorite=self.favorite,
            dateAdded=self.date_added,
            coverArt=self.cover_art_path,
            vocalPath=self.vocals_path,
            instrumentalPath=self.instrumental_path,
            originalPath=self.original_path,
            thumbnail=self.thumbnail_path,
            album=self.album,
        )
    @classmethod
    def from_metadata(
        cls,
        song_id: str,
        metadata: SongMetadata,
        vocals_path: str = None,
        instrumental_path: str = None,
        original_path: str = None,
    ):
        import json  # Import here to avoid circular imports
        
        return cls(
            id=song_id,
            title=metadata.title or song_id.replace("_", " ").title(),
            artist=metadata.artist or UNKNOWN_ARTIST,
            duration=metadata.duration,
            favorite=metadata.favorite,
            date_added=metadata.dateAdded,
            vocals_path=vocals_path,
            instrumental_path=instrumental_path,
            original_path=original_path,
            thumbnail_path=metadata.thumbnail,
            cover_art_path=metadata.coverArt,
            source=metadata.source,
            source_url=metadata.sourceUrl,
            video_id=metadata.videoId,
            uploader=metadata.uploader,
            uploader_id=metadata.uploaderId,
            channel=metadata.channel,
            channel_id=metadata.channelId,
            description=metadata.description,
            upload_date=metadata.uploadDate,
            mbid=metadata.mbid,
            album=metadata.releaseTitle,
            release_id=metadata.releaseId,
            release_date=metadata.releaseDate,
            year=getattr(metadata, 'year', None),
            genre=metadata.genre,
            language=metadata.language,
            lyrics=metadata.lyrics,
            synced_lyrics=metadata.syncedLyrics,
            
            # Phase 1B: iTunes integration fields
            itunes_track_id=getattr(metadata, 'itunesTrackId', None),
            itunes_artist_id=getattr(metadata, 'itunesArtistId', None),
            itunes_collection_id=getattr(metadata, 'itunesCollectionId', None),
            track_time_millis=getattr(metadata, 'trackTimeMillis', None),
            itunes_explicit=getattr(metadata, 'itunesExplicit', None),
            itunes_preview_url=getattr(metadata, 'itunesPreviewUrl', None),
            itunes_artwork_urls=json.dumps(getattr(metadata, 'itunesArtworkUrls', None)) if getattr(metadata, 'itunesArtworkUrls', None) else None,
            
            # Phase 1B: Enhanced YouTube fields
            youtube_duration=getattr(metadata, 'youtubeDuration', None),
            youtube_thumbnail_urls=json.dumps(getattr(metadata, 'youtubeThumbnailUrls', None)) if getattr(metadata, 'youtubeThumbnailUrls', None) else None,
            youtube_tags=json.dumps(getattr(metadata, 'youtubeTags', None)) if getattr(metadata, 'youtubeTags', None) else None,
            youtube_categories=json.dumps(getattr(metadata, 'youtubeCategories', None)) if getattr(metadata, 'youtubeCategories', None) else None,
            youtube_channel_id=getattr(metadata, 'youtubeChannelId', None),
            youtube_channel_name=getattr(metadata, 'youtubeChannelName', None),
            
            # Phase 1B: Raw metadata storage
            itunes_raw_metadata=getattr(metadata, 'itunesRawMetadata', None),
            youtube_raw_metadata=getattr(metadata, 'youtubeRawMetadata', None),
        )
