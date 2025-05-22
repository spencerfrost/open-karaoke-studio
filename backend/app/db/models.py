# backend/app/db/models.py
"""
Data models for the application
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List

# Import the datetime CLASS specifically
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import json
import os
from pathlib import Path

# SQLAlchemy imports
from sqlalchemy import (
    Column,
    Integer,
    String,
    create_engine,
    Boolean,
    Float,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import traceback
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, validates, relationship

# Password hashing imports
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()

# Constants
UNKNOWN_ARTIST = "Unknown Artist"


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    id: str
    filename: str
    status: JobStatus
    progress: int = 0
    task_id: Optional[str] = None  # Added field to store Celery task ID
    created_at: Optional[datetime] = None  # Will be set in post_init
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    notes: Optional[str] = None  # Added for extra info like fallback notice

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

        # Convert string status to Enum if needed
        if isinstance(self.status, str):
            self.status = JobStatus(self.status)

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary with datetime serialization"""
        data = asdict(self)

        # Convert datetime objects to ISO format strings
        for key in ["created_at", "started_at", "completed_at"]:
            if data[key] is not None and isinstance(data[key], datetime):
                # Ensure it's aware before converting, or handle naive properly
                if data[key].tzinfo is None:
                    # Assuming naive datetimes were intended as UTC
                    data[key] = data[key].replace(tzinfo=timezone.utc).isoformat()
                else:
                    data[key] = data[key].isoformat()

        # Convert Enum to string
        data["status"] = self.status.value

        return data


class DbJob(Base):
    """SQLAlchemy model for storing jobs in the database"""

    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    status = Column(String, nullable=False, default=JobStatus.PENDING.value)
    progress = Column(Integer, default=0)
    task_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    def to_job(self) -> Job:
        """Convert SQLAlchemy model to Job dataclass"""
        return Job(
            id=self.id,
            filename=self.filename,
            status=JobStatus(self.status),
            progress=self.progress,
            task_id=self.task_id,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            error=self.error,
            notes=self.notes,
        )


class JobStore:
    """Database-backed job storage mechanism using SQLAlchemy"""

    def __init__(self):
        """No need for a storage_dir anymore as we're using the database"""
        from .database import get_db_session, SessionLocal

        self.get_db_session = get_db_session
        self.SessionLocal = SessionLocal

        # Ensure table exists
        from .database import engine

        DbJob.__table__.create(bind=engine, checkfirst=True)

    def save_job(self, job: Job) -> None:
        """Save job to database"""
        try:
            with self.get_db_session() as session:
                db_job = session.query(DbJob).filter(DbJob.id == job.id).first()

                if not db_job:
                    # Create new job
                    print(f"Creating new job in DB: {job.id}")
                    db_job = DbJob(
                        id=job.id,
                        filename=job.filename,
                        status=job.status.value,
                        progress=job.progress,
                        task_id=job.task_id,
                        created_at=job.created_at,
                        started_at=job.started_at,
                        completed_at=job.completed_at,
                        error=job.error,
                        notes=job.notes,
                    )
                    session.add(db_job)
                else:
                    # Update existing job
                    db_job.filename = job.filename
                    db_job.status = job.status.value
                    db_job.progress = job.progress
                    db_job.task_id = job.task_id
                    db_job.started_at = job.started_at
                    db_job.completed_at = job.completed_at
                    db_job.error = job.error
                    db_job.notes = job.notes

                session.commit()
        except Exception as e:
            print(f"Error saving job {job.id}: {e}")
            traceback.print_exc()

    def get_job(self, job_id):
        """Get job by ID"""
        try:
            with self.get_db_session() as session:
                print(f"Looking for job {job_id} in database")
                db_job = session.query(DbJob).filter(DbJob.id == job_id).first()
                print(f"Query result: {db_job}")
                if not db_job:
                    return None
                # Use the to_job method already defined in DbJob
                return db_job.to_job()
        except Exception as e:
            print(f"Error getting job {job_id}: {e}")
            traceback.print_exc()
            return None

    def get_all_jobs(self) -> List[Job]:
        """Get all jobs"""
        try:
            with self.get_db_session() as session:
                db_jobs = session.query(DbJob).all()
                return [db_job.to_job() for db_job in db_jobs]
        except Exception as e:
            print(f"Error getting all jobs: {e}")
            return []

    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """Get jobs by status"""
        try:
            with self.get_db_session() as session:
                db_jobs = (
                    session.query(DbJob).filter(DbJob.status == status.value).all()
                )
                return [db_job.to_job() for db_job in db_jobs]
        except Exception as e:
            print(f"Error getting jobs by status {status}: {e}")
            return []

    def delete_job(self, job_id: str) -> bool:
        """Delete job from storage"""
        try:
            with self.get_db_session() as session:
                db_job = session.query(DbJob).filter(DbJob.id == job_id).first()
                if db_job:
                    session.delete(db_job)
                    session.commit()
                    return True
                return False
        except Exception as e:
            print(f"Error deleting job {job_id}: {e}")
            return False

    # Job statistics
    def get_stats(self) -> Dict[str, int]:
        """Get job statistics"""
        try:
            with self.get_db_session() as session:
                total = session.query(DbJob).count()
                pending = (
                    session.query(DbJob)
                    .filter(DbJob.status == JobStatus.PENDING.value)
                    .count()
                )
                processing = (
                    session.query(DbJob)
                    .filter(DbJob.status == JobStatus.PROCESSING.value)
                    .count()
                )
                completed = (
                    session.query(DbJob)
                    .filter(DbJob.status == JobStatus.COMPLETED.value)
                    .count()
                )
                failed = (
                    session.query(DbJob)
                    .filter(DbJob.status == JobStatus.FAILED.value)
                    .count()
                )
                cancelled = (
                    session.query(DbJob)
                    .filter(DbJob.status == JobStatus.CANCELLED.value)
                    .count()
                )

                return {
                    "total": total,
                    "queue_length": pending,
                    "active_jobs": processing,
                    "completed_jobs": completed,
                    "failed_jobs": failed + cancelled,
                    "raw_failed": failed,
                    "raw_cancelled": cancelled,
                }
        except Exception as e:
            print(f"Error getting job statistics: {e}")
            return {
                "total": 0,
                "queue_length": 0,
                "active_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "raw_failed": 0,
                "raw_cancelled": 0,
            }


# --- Song Models (Pydantic - unchanged from previous state) ---
SongStatus = Literal["processing", "queued", "processed", "error"]


class SongMetadata(BaseModel):
    """
    Represents the data stored in metadata.json for a song.
    Fields that are typically known *after* upload/initial processing.
    """

    title: Optional[str] = None
    artist: Optional[str] = None
    duration: Optional[float] = None  # Duration in seconds
    favorite: bool = False
    dateAdded: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    coverArt: Optional[str] = None  # URL or path to cover art
    thumbnail: Optional[str] = None  # Path to YouTube thumbnail

    # Source information
    source: Optional[str] = None  # "youtube", "upload", etc.
    sourceUrl: Optional[str] = None  # Original URL (YouTube URL, etc.)

    # YouTube-specific fields
    videoId: Optional[str] = None  # YouTube video ID
    videoTitle: Optional[str] = None  # YouTube video title
    uploader: Optional[str] = None  # Uploader name
    uploaderId: Optional[str] = None  # Uploader ID
    channel: Optional[str] = None  # YouTube channel name
    channelId: Optional[str] = None  # YouTube channel ID
    description: Optional[str] = None  # Video description (truncated)
    uploadDate: Optional[datetime] = None  # When video was published

    # MusicBrainz fields
    mbid: Optional[str] = None  # MusicBrainz recording ID
    releaseTitle: Optional[str] = None  # Album title
    releaseId: Optional[str] = None  # MusicBrainz release ID
    releaseDate: Optional[str] = None  # Release date

    # Additional metadata fields
    genre: Optional[str] = None  # Music genre
    language: Optional[str] = None  # Language of the lyrics

    # Lyrics fields
    lyrics: Optional[str] = None  # Plain text lyrics
    syncedLyrics: Optional[str] = None  # LRC format synchronized lyrics

    class Config:
        model_config = {
            "json_encoders": {datetime: lambda v: v.isoformat() if v else None}
        }


class Song(BaseModel):
    """
    Represents the full Song object returned by the API.
    Combines metadata with derived/runtime information.
    Matches frontend/src/types/Song.ts
    """

    id: str
    title: str
    artist: str = UNKNOWN_ARTIST
    duration: Optional[float] = None
    status: SongStatus = "processed"

    videoId: Optional[str] = None  # YouTube video ID
    uploader: Optional[str] = None  # Uploader name
    uploaderId: Optional[str] = None  # Uploader ID
    channel: Optional[str] = None  # YouTube channel name
    channelId: Optional[str] = None  # YouTube channel ID
    description: Optional[str] = None  # Video description
    uploadDate: Optional[datetime] = None  # When video was published

    mbid: Optional[str] = None  # MusicBrainz recording ID
    releaseTitle: Optional[str] = None  # Album title
    releaseId: Optional[str] = None  # MusicBrainz release ID
    releaseDate: Optional[str] = None  # Release date
    genre: Optional[str] = None  # Music genre

    favorite: bool = False
    dateAdded: Optional[datetime] = None
    coverArt: Optional[str] = None
    vocalPath: Optional[str] = None  # Relative path/URL for frontend
    instrumentalPath: Optional[str] = None  # Relative path/URL for frontend
    originalPath: Optional[str] = None  # Relative path/URL for frontend
    thumbnail: Optional[str] = None  # Path to YouTube thumbnail

    class Config:
        model_config = {
            "json_encoders": {datetime: lambda v: v.isoformat() if v else None}
        }


# --- SQLAlchemy Models for Database Storage ---


class DbSong(Base):
    """SQLAlchemy model for storing songs in the database"""

    __tablename__ = "songs"

    id = Column(String, primary_key=True)  # Song directory name as ID
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False, default=UNKNOWN_ARTIST)
    duration = Column(Float, nullable=True)
    favorite = Column(Boolean, default=False)
    date_added = Column(DateTime, default=datetime.now(timezone.utc))

    # File paths (relative to library directory)
    vocals_path = Column(String, nullable=True)
    instrumental_path = Column(String, nullable=True)
    original_path = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)
    cover_art_path = Column(String, nullable=True)

    # Source information
    source = Column(String, nullable=True)  # "youtube", "upload", etc.
    source_url = Column(String, nullable=True)  # Original URL

    # YouTube-specific fields
    video_id = Column(String, nullable=True)  # YouTube video ID
    uploader = Column(String, nullable=True)  # Uploader name
    uploader_id = Column(String, nullable=True)  # Uploader ID
    channel = Column(String, nullable=True)  # YouTube channel name
    channel_id = Column(String, nullable=True)  # YouTube channel ID
    description = Column(Text, nullable=True)  # Video description
    upload_date = Column(DateTime, nullable=True)  # When video was published

    # MusicBrainz fields
    mbid = Column(String, nullable=True)  # MusicBrainz recording ID
    release_title = Column(String, nullable=True)  # Album title
    release_id = Column(String, nullable=True)  # MusicBrainz release ID
    release_date = Column(String, nullable=True)  # Release date string

    # Additional metadata fields
    genre = Column(String, nullable=True)  # Music genre
    language = Column(String, nullable=True)  # Language of the lyrics

    # Lyrics fields
    lyrics = Column(Text, nullable=True)  # Plain text lyrics
    synced_lyrics = Column(Text, nullable=True)  # LRC format synchronized lyrics

    # Relationships
    queue_items = relationship(
        "KaraokeQueueItem", back_populates="song", cascade="all, delete-orphan"
    )

    def to_pydantic(self) -> Song:
        """Convert SQLAlchemy model to Pydantic model for API responses"""
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
        """Create a DbSong from SongMetadata and file paths"""
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


class KaraokeQueueItem(Base):
    __tablename__ = "karaoke_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    singer_name = Column(String, nullable=False)
    song_id = Column(String, ForeignKey("songs.id"), nullable=False)
    position = Column(Integer, nullable=False)

    # Relationship to song
    song = relationship("DbSong", back_populates="queue_items")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)  # Optional password
    display_name = Column(String, nullable=True)
    theme = Column(String, nullable=True)  # Field for UI theme selection
    color = Column(String, nullable=True)  # Field for user-specific color
    is_admin = Column(Boolean, default=False)

    def set_password(self, password):
        if password:
            self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        return False

    @validates("username")
    def validate_username(self, key, username):
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        return username


# Note: Database engine is now defined in database.py to avoid circular imports
