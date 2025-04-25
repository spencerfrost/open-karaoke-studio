# backend/app/models.py
"""
Data models for the application
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal

# Import the datetime CLASS specifically
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum

# Keep other typing imports
from typing import Dict, Any, List
import json
import os
from pathlib import Path

# SQLAlchemy imports
from sqlalchemy import Column, Integer, String, create_engine, Boolean, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, validates, relationship

# Password hashing imports
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()


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


class JobStore:
    """Simple job storage mechanism - in production, use a database instead"""

    def __init__(self, storage_dir: str = None):
        self.storage_dir = Path(
            storage_dir or os.path.join(os.path.dirname(__file__), "job_store")
        )
        os.makedirs(self.storage_dir, exist_ok=True)

    def _job_path(self, job_id: str) -> Path:
        return self.storage_dir / f"{job_id}.json"

    def save_job(self, job: Job) -> None:
        """Save job to storage"""
        try:
            with open(self._job_path(job.id), "w") as f:
                json.dump(job.to_dict(), f, indent=2)  # Add indent for readability
        except Exception as e:
            # Log error appropriately
            print(f"Error saving job {job.id}: {e}")

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        path = self._job_path(job_id)
        if not path.exists():
            return None

        try:
            with open(path, "r") as f:
                data = json.load(f)

            # Parse datetime strings back to datetime objects
            for key in ["created_at", "started_at", "completed_at"]:
                if data.get(key) and isinstance(
                    data[key], str
                ):  # Check if key exists and is string
                    try:
                        data[key] = datetime.fromisoformat(data[key])
                        # Make aware if tz info is present, otherwise assume UTC? Be consistent.
                        if data[key].tzinfo is None:
                            # If saved as UTC isoformat, it might include +00:00 or Z
                            # If not, assuming UTC might be wrong. Best practice is to always save with tz.
                            pass  # Or: data[key] = data[key].replace(tzinfo=timezone.utc) if you are sure
                    except ValueError:
                        print(
                            f"Warning: Could not parse datetime string '{data[key]}' for key '{key}' in job {job_id}"
                        )
                        data[key] = None  # Set to None if parsing fails

            # Handle potential missing optional fields during load
            job_data = {
                "id": data.get("id"),
                "filename": data.get("filename"),
                "status": data.get(
                    "status", JobStatus.PENDING.value
                ),  # Default status if missing
                "progress": data.get("progress", 0),
                "task_id": data.get("task_id"),
                "created_at": data.get("created_at"),
                "started_at": data.get("started_at"),
                "completed_at": data.get("completed_at"),
                "error": data.get("error"),
                "notes": data.get("notes"),
            }
            # Filter out None values if Job init doesn't handle them gracefully
            # filtered_job_data = {k: v for k, v in job_data.items() if v is not None}
            # return Job(**filtered_job_data)
            if not job_data["id"] or not job_data["filename"]:
                print(f"Error loading job {job_id}: missing id or filename")
                return None
            return Job(**job_data)  # Pass potentially None values

        except Exception as e:
            print(f"Error loading job {job_id}: {e}")
            traceback.print_exc()  # Print traceback for debugging
            return None

    def get_all_jobs(self) -> List[Job]:
        """Get all jobs"""
        jobs = []
        for job_file in self.storage_dir.glob("*.json"):
            job_id = job_file.stem
            job = self.get_job(job_id)
            if job:
                jobs.append(job)
        return jobs

    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """Get jobs by status"""
        return [job for job in self.get_all_jobs() if job.status == status]

    def delete_job(self, job_id: str) -> bool:
        """Delete job from storage"""
        path = self._job_path(job_id)
        if path.exists():
            try:
                path.unlink()
                return True
            except OSError as e:
                print(f"Error deleting job file {path}: {e}")
                return False
        return False

    # Job statistics
    def get_stats(self) -> Dict[str, int]:
        """Get job statistics"""
        all_jobs = self.get_all_jobs()
        stats = {status: 0 for status in JobStatus}
        for job in all_jobs:
            stats[job.status] += 1

        return {
            "total": len(all_jobs),
            "queue_length": stats[JobStatus.PENDING],
            "active_jobs": stats[JobStatus.PROCESSING],
            "completed_jobs": stats[JobStatus.COMPLETED],
            # Combine failed and cancelled for a general "failed" count
            "failed_jobs": stats[JobStatus.FAILED] + stats[JobStatus.CANCELLED],
            # Optionally provide individual counts
            "raw_failed": stats[JobStatus.FAILED],
            "raw_cancelled": stats[JobStatus.CANCELLED],
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
    channelName: Optional[str] = None  # YouTube channel name
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

    id: str  # The directory name / unique ID
    title: str
    artist: str = "Unknown Artist"
    duration: Optional[float] = None
    status: SongStatus = "processed"  # Default status for songs found in library
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
    __tablename__ = 'songs'
    
    id = Column(String, primary_key=True)  # Song directory name as ID
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False, default="Unknown Artist")
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
    channel_name = Column(String, nullable=True)  # YouTube channel name
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
    queue_items = relationship("KaraokeQueueItem", back_populates="song", cascade="all, delete-orphan")
    
    def to_pydantic(self) -> Song:
        """Convert SQLAlchemy model to Pydantic model for API responses"""
        return Song(
            id=self.id,
            title=self.title,
            artist=self.artist,
            duration=self.duration,
            status="processed",  # Default status for songs in DB
            favorite=self.favorite,
            dateAdded=self.date_added,
            coverArt=self.cover_art_path,
            vocalPath=self.vocals_path,
            instrumentalPath=self.instrumental_path,
            originalPath=self.original_path,
            thumbnail=self.thumbnail_path
        )
        
    @classmethod
    def from_metadata(cls, song_id: str, metadata: SongMetadata, 
                     vocals_path: str = None, 
                     instrumental_path: str = None,
                     original_path: str = None):
        """Create a DbSong from SongMetadata and file paths"""
        return cls(
            id=song_id,
            title=metadata.title or song_id.replace('_', ' ').title(),
            artist=metadata.artist or "Unknown Artist",
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
            channel_name=metadata.channelName,
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
            synced_lyrics=metadata.syncedLyrics
        )


class KaraokeQueueItem(Base):
    __tablename__ = 'karaoke_queue'

    id = Column(Integer, primary_key=True, autoincrement=True)
    singer_name = Column(String, nullable=False)
    song_id = Column(String, ForeignKey("songs.id"), nullable=False)
    position = Column(Integer, nullable=False)
    
    # Relationship to song
    song = relationship("DbSong", back_populates="queue_items")


class User(Base):
    __tablename__ = 'users'

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

    @validates('username')
    def validate_username(self, key, username):
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        return username


# SQLite setup
DATABASE_URL = "sqlite:///karaoke.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)
