"""
Job-related models: Enum, dataclass, SQLAlchemy, and store.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import traceback
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from .base import Base
import json
import tempfile
from pathlib import Path


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
        return Job(
            id=self.id,
            filename=self.filename,
            status=JobStatus(self.status),
            progress=self.progress,
            status_message=self.status_message,
            task_id=self.task_id,
            song_id=self.song_id,
            title=self.title,
            artist=self.artist,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            error=self.error,
            notes=self.notes,
            dismissed=self.dismissed or False,
        )


class JobStore:
    def __init__(self):
        from ..database import get_db_session, SessionLocal

        self.get_db_session = get_db_session
        self.SessionLocal = SessionLocal
        from ..database import engine

        DbJob.__table__.create(bind=engine, checkfirst=True)
        
        # Initialize fallback file cache for emergency job storage
        self._init_fallback_cache()
    
    def _init_fallback_cache(self):
        """Initialize a file-based fallback cache for jobs"""
        try:
            from ...config import get_config
            config = get_config()
            self.fallback_dir = Path(config.BASE_DIR) / "temp_job_cache"
            self.fallback_dir.mkdir(exist_ok=True)
        except Exception as e:
            # Use system temp directory as last resort
            self.fallback_dir = Path(tempfile.gettempdir()) / "karaoke_job_cache"
            self.fallback_dir.mkdir(exist_ok=True)
    
    def _save_job_to_fallback(self, job: Job):
        """Save job to file-based fallback cache"""
        try:
            cache_file = self.fallback_dir / f"{job.id}.json"
            with open(cache_file, 'w') as f:
                json.dump(job.to_dict(), f)
            return True
        except Exception as e:
            print(f"Failed to save job {job.id} to fallback cache: {e}")
            return False
    
    def _get_job_from_fallback(self, job_id: str) -> Optional[Job]:
        """Retrieve job from file-based fallback cache"""
        try:
            cache_file = self.fallback_dir / f"{job_id}.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    job_data = json.load(f)
                # Convert back to Job object
                job_data['status'] = JobStatus(job_data['status'])
                # Handle datetime fields
                for date_field in ['created_at', 'started_at', 'completed_at']:
                    if job_data.get(date_field):
                        from datetime import datetime
                        job_data[date_field] = datetime.fromisoformat(job_data[date_field].replace('Z', '+00:00'))
                return Job(**job_data)
        except Exception as e:
            print(f"Failed to get job {job_id} from fallback cache: {e}")
        return None

    def save_job(self, job: Job) -> None:
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            was_created = False
            logger.info(f"Attempting to save job {job.id} to database")
            
            with self.get_db_session() as session:
                # Log database connection info
                logger.info(f"Database engine URL: {session.bind.url}")
                
                db_job = session.query(DbJob).filter(DbJob.id == job.id).first()
                if not db_job:
                    was_created = True
                    logger.info(f"Creating new job {job.id}")
                    db_job = DbJob(
                        id=job.id,
                        filename=job.filename,
                        status=job.status.value,
                        progress=job.progress,
                        status_message=job.status_message,
                        task_id=job.task_id,
                        song_id=job.song_id,
                        title=job.title,
                        artist=job.artist,
                        created_at=job.created_at,
                        started_at=job.started_at,
                        completed_at=job.completed_at,
                        error=job.error,
                        notes=job.notes,
                        dismissed=job.dismissed,
                    )
                    session.add(db_job)
                else:
                    logger.info(f"Updating existing job {job.id}")
                    db_job.filename = job.filename
                    db_job.status = job.status.value
                    db_job.progress = job.progress
                    db_job.status_message = job.status_message
                    db_job.task_id = job.task_id
                    db_job.song_id = job.song_id
                    db_job.title = job.title
                    db_job.artist = job.artist
                    db_job.started_at = job.started_at
                    db_job.completed_at = job.completed_at
                    db_job.error = job.error
                    db_job.notes = job.notes
                    db_job.dismissed = job.dismissed
                
                # Ensure the data is flushed to database before commit
                logger.info(f"Flushing session for job {job.id}")
                session.flush()
                
                logger.info(f"Committing session for job {job.id}")
                session.commit()
                
                # Force database synchronization for SQLite
                try:
                    from ..database import force_db_sync
                    logger.info(f"Forcing database sync for job {job.id}")
                    force_db_sync()
                except Exception as sync_error:
                    logger.warning(f"Failed to force database sync: {sync_error}")
                
                # Additional verification that the job was saved properly
                logger.info(f"Verifying job {job.id} was saved")
                verification = session.query(DbJob).filter(DbJob.id == job.id).first()
                if not verification:
                    logger.error(f"CRITICAL: Job {job.id} failed verification after commit!")
                    raise Exception(f"Job {job.id} failed to save properly")
                else:
                    logger.info(f"SUCCESS: Job {job.id} verified in database with status {verification.status}")
                
                from ...jobs.jobs import _broadcast_job_event
                _broadcast_job_event(job, was_created)
                
                # Also save to fallback cache as emergency backup
                self._save_job_to_fallback(job)
                
        except Exception as e:
            logger.error(f"Error saving job {job.id}: {e}")
            traceback.print_exc()
            
            # Try to save to fallback cache if database save failed
            logger.warning(f"Attempting to save job {job.id} to fallback cache")
            if self._save_job_to_fallback(job):
                logger.info(f"Job {job.id} saved to fallback cache successfully")
            
            raise  # Re-raise to ensure calling code knows about the failure

    def get_job(self, job_id):
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"Attempting to retrieve job {job_id} from database")
            
            with self.get_db_session() as session:
                # Log database connection info
                logger.info(f"Database engine URL: {session.bind.url}")
                
                # First, let's check how many jobs exist in total
                total_jobs = session.query(DbJob).count()
                logger.info(f"Total jobs in database: {total_jobs}")
                
                # Check for jobs with similar IDs (for debugging)
                all_job_ids = session.query(DbJob.id).all()
                logger.info(f"All job IDs in database: {[job.id for job in all_job_ids[:5]]}...")  # Log first 5
                
                db_job = session.query(DbJob).filter(DbJob.id == job_id).first()
                if not db_job:
                    logger.warning(f"Job {job_id} NOT FOUND in database, checking fallback cache")
                    # Try fallback cache
                    fallback_job = self._get_job_from_fallback(job_id)
                    if fallback_job:
                        logger.info(f"SUCCESS: Found job {job_id} in fallback cache")
                        return fallback_job
                    else:
                        logger.warning(f"Job {job_id} not found in fallback cache either")
                        return None
                else:
                    logger.info(f"SUCCESS: Found job {job_id} with status {db_job.status}")
                    return db_job.to_job()
                    
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {e}")
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

    def dismiss_job(self, job_id: str) -> bool:
        """Mark a job as dismissed (hidden from UI but kept in database)."""
        try:
            with self.get_db_session() as session:
                db_job = session.query(DbJob).filter(DbJob.id == job_id).first()
                if db_job:
                    db_job.dismissed = True
                    session.commit()
                    # Broadcast the update
                    job = db_job.to_job()
                    from ...jobs.jobs import _broadcast_job_event

                    _broadcast_job_event(job, False)
                    return True
                return False
        except Exception as e:
            print(f"Error dismissing job {job_id}: {e}")
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

    def get_active_jobs(self) -> List[Job]:
        """Get all non-dismissed jobs for the main UI."""
        try:
            with self.get_db_session() as session:
                db_jobs = session.query(DbJob).filter(DbJob.dismissed == False).all()
                return [db_job.to_job() for db_job in db_jobs]
        except Exception as e:
            print(f"Error getting active jobs: {e}")
            return []

    def get_dismissed_jobs(self) -> List[Job]:
        """Get all dismissed jobs for management/history view."""
        try:
            with self.get_db_session() as session:
                db_jobs = session.query(DbJob).filter(DbJob.dismissed == True).all()
                return [db_job.to_job() for db_job in db_jobs]
        except Exception as e:
            print(f"Error getting dismissed jobs: {e}")
            return []
