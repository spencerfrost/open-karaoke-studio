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

    class Config:
        model_config = {
            "json_encoders": {datetime: lambda v: v.isoformat() if v else None}
        }
