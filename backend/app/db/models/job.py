"""
Job-related models: Enum, dataclass, SQLAlchemy, and store.
"""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from .base import Base

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Enumeration of possible job statuses."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Data class representing a job with its current status and progress."""

    id: str
    filename: str
    status: JobStatus
    progress: int = 0
    status_message: Optional[str] = None
    task_id: Optional[str] = None
    song_id: Optional[str] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    notes: Optional[str] = None
    dismissed: bool = False  # Track if job is dismissed from UI

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if isinstance(self.status, str):
            self.status = JobStatus(self.status)

    """Convert the job to a dictionary representation for serialization."""
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ["created_at", "started_at", "completed_at"]:
            if data[key] is not None and isinstance(data[key], datetime):
                if data[key].tzinfo is None:
                    data[key] = data[key].replace(tzinfo=timezone.utc).isoformat()
                else:
                    data[key] = data[key].isoformat()
        data["status"] = self.status.value
        return data


class DbJob(Base):
    """Database model for storing job information and status."""

    __tablename__ = "jobs"
    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    status = Column(String, nullable=False, default=JobStatus.PENDING.value)
    progress = Column(Integer, default=0)
    status_message = Column(Text, nullable=True)
    task_id = Column(String, nullable=True)
    song_id = Column(String, nullable=True)
    title = Column(String, nullable=True)
    artist = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    dismissed = Column(Boolean, default=False)  # Track if job is dismissed from UI

    # Legacy fields that exist in database
    phase_message = Column(Text, nullable=True)
    phase = Column(String, nullable=False, default="created")
    retry_count = Column(Integer, default=0)

    def to_job(self) -> Job:
        """Convert database job to domain job object."""
        return Job(
            id=self.id, # type: ignore[assignment]
            filename=self.filename, # type: ignore[assignment]
            status=JobStatus(self.status), # type: ignore[assignment]
            progress=self.progress, # type: ignore[assignment]
            status_message=self.status_message, # type: ignore[assignment]
            task_id=self.task_id, # type: ignore[assignment]
            song_id=self.song_id, # type: ignore[assignment]
            title=self.title, # type: ignore[assignment]
            artist=self.artist, # type: ignore[assignment]
            created_at=self.created_at, # type: ignore[assignment]
            started_at=self.started_at, # type: ignore[assignment]
            completed_at=self.completed_at, # type: ignore[assignment]
            error=self.error, # type: ignore[assignment]
            notes=self.notes, # type: ignore[assignment]
            dismissed=self.dismissed or False, # type: ignore[assignment]
        )
