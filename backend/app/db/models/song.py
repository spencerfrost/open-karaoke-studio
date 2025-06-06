"""
Song-related models: Pydantic, SQLAlchemy, and helpers.
"""
from typing import Optional, Literal
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
    channelId: Optional[str] = None
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
    description: Optional[str] = None
    uploadDate: Optional[datetime] = None
    mbid: Optional[str] = None
    releaseTitle: Optional[str] = None
    releaseId: Optional[str] = None
    releaseDate: Optional[str] = None
    genre: Optional[str] = None
    favorite: bool = False
    dateAdded: Optional[datetime] = None
    coverArt: Optional[str] = None
    vocalPath: Optional[str] = None
    instrumentalPath: Optional[str] = None
    originalPath: Optional[str] = None
    thumbnail: Optional[str] = None
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
    channel_id = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    upload_date = Column(DateTime, nullable=True)
    mbid = Column(String, nullable=True)
    release_title = Column(String, nullable=True)
    release_id = Column(String, nullable=True)
    release_date = Column(String, nullable=True)
    genre = Column(String, nullable=True)
    language = Column(String, nullable=True)
    lyrics = Column(Text, nullable=True)
    synced_lyrics = Column(Text, nullable=True)
    queue_items = relationship("KaraokeQueueItem", back_populates="song", cascade="all, delete-orphan")
    def to_pydantic(self) -> Song:
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
            description=self.description,
            uploadDate=self.upload_date,
            mbid=self.mbid,
            releaseTitle=self.release_title,
            releaseId=self.release_id,
            releaseDate=self.release_date,
            genre=self.genre,
            language=self.language,
            lyrics=self.lyrics,
            syncedLyrics=self.synced_lyrics,
            source=self.source,
            sourceUrl=self.source_url,
            favorite=self.favorite,
            dateAdded=self.date_added,
            coverArt=self.cover_art_path,
            vocalPath=self.vocals_path,
            instrumentalPath=self.instrumental_path,
            originalPath=self.original_path,
            thumbnail=self.thumbnail_path,
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
            release_title=metadata.releaseTitle,
            release_id=metadata.releaseId,
            release_date=metadata.releaseDate,
            genre=metadata.genre,
            language=metadata.language,
            lyrics=metadata.lyrics,
            synced_lyrics=metadata.syncedLyrics,
        )
