"""
Job-related models: Enum, dataclass, SQLAlchemy, and store.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import traceback
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from .base import Base

class JobStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Job:
    id: str
    filename: str
    status: JobStatus
    progress: int = 0
    status_message: Optional[str] = None
    task_id: Optional[str] = None
    song_id: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if isinstance(self.status, str):
            self.status = JobStatus(self.status)

    def to_dict(self) -> Dict[str, Any]:
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
    __tablename__ = "jobs"
    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    status = Column(String, nullable=False, default=JobStatus.PENDING.value)
    progress = Column(Integer, default=0)
    status_message = Column(Text, nullable=True)
    task_id = Column(String, nullable=True)
    song_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    def to_job(self) -> Job:
        return Job(
            id=self.id,
            filename=self.filename,
            status=JobStatus(self.status),
            progress=self.progress,
            status_message=self.status_message,
            task_id=self.task_id,
            song_id=self.song_id,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            error=self.error,
            notes=self.notes,
        )

class JobStore:
    def __init__(self):
        from ..database import get_db_session, SessionLocal
        self.get_db_session = get_db_session
        self.SessionLocal = SessionLocal
        from ..database import engine
        DbJob.__table__.create(bind=engine, checkfirst=True)

    def save_job(self, job: Job) -> None:
        try:
            was_created = False
            with self.get_db_session() as session:
                db_job = session.query(DbJob).filter(DbJob.id == job.id).first()
                if not db_job:
                    was_created = True
                    db_job = DbJob(
                        id=job.id,
                        filename=job.filename,
                        status=job.status.value,
                        progress=job.progress,
                        status_message=job.status_message,
                        task_id=job.task_id,
                        song_id=job.song_id,
                        created_at=job.created_at,
                        started_at=job.started_at,
                        completed_at=job.completed_at,
                        error=job.error,
                        notes=job.notes,
                    )
                    session.add(db_job)
                else:
                    db_job.filename = job.filename
                    db_job.status = job.status.value
                    db_job.progress = job.progress
                    db_job.status_message = job.status_message
                    db_job.task_id = job.task_id
                    db_job.song_id = job.song_id
                    db_job.started_at = job.started_at
                    db_job.completed_at = job.completed_at
                    db_job.error = job.error
                    db_job.notes = job.notes
                session.commit()
                from ..jobs.jobs import _broadcast_job_event
                _broadcast_job_event(job, was_created)
        except Exception as e:
            print(f"Error saving job {job.id}: {e}")
            traceback.print_exc()

    def get_job(self, job_id):
        try:
            with self.get_db_session() as session:
                db_job = session.query(DbJob).filter(DbJob.id == job_id).first()
                if not db_job:
                    return None
                return db_job.to_job()
        except Exception as e:
            print(f"Error getting job {job_id}: {e}")
            traceback.print_exc()
            return None

    def get_all_jobs(self) -> List[Job]:
        try:
            with self.get_db_session() as session:
                db_jobs = session.query(DbJob).all()
                return [db_job.to_job() for db_job in db_jobs]
        except Exception as e:
            print(f"Error getting all jobs: {e}")
            return []

    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
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

    def get_stats(self) -> Dict[str, int]:
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
