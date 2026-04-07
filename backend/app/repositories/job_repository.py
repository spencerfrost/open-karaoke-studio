"""
Repository for job data access operations.
"""

import logging
import traceback
from typing import List, Optional

from app.db.models import DbJob, Job, JobStatus

logger = logging.getLogger(__name__)


class JobRepository:
    """Repository class for managing job persistence in the database."""

    def __init__(self):
        from app.db.database import SessionLocal, engine, get_db_session

        self.get_db_session = get_db_session
        self.SessionLocal = SessionLocal

        DbJob.__table__.create(bind=engine, checkfirst=True)

    def create(self, job: Job, skip_events: bool = False) -> None:
        """Create or update a job in the database.

        Args:
            job: The job to save
            skip_events: If True, skip database logging and event publishing
                        (useful for frequent progress updates)
        """
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
                        title=job.title,
                        artist=job.artist,
                        created_at=job.created_at,
                        started_at=job.started_at,
                        completed_at=job.completed_at,
                        error=job.error,
                        engine_type=job.engine_type,
                    )
                    session.add(db_job)
                else:
                    db_job.filename = job.filename  # type: ignore
                    db_job.status = job.status.value  # type: ignore
                    db_job.progress = job.progress  # type: ignore
                    db_job.status_message = job.status_message  # type: ignore
                    db_job.task_id = job.task_id  # type: ignore
                    db_job.song_id = job.song_id  # type: ignore
                    db_job.title = job.title  # type: ignore
                    db_job.artist = job.artist  # type: ignore
                    db_job.started_at = job.started_at  # type: ignore
                    db_job.completed_at = job.completed_at  # type: ignore
                    db_job.error = job.error  # type: ignore
                    db_job.engine_type = job.engine_type  # type: ignore

                session.flush()
                session.commit()

                # Force database synchronization for SQLite
                try:
                    from app.db.database import force_db_sync

                    force_db_sync()
                except Exception as sync_error:
                    logger.warning("Failed to force database sync: %s", sync_error)

                # Verify the job was saved properly
                verification = session.query(DbJob).filter(DbJob.id == job.id).first()
                if not verification:
                    logger.error(
                        "CRITICAL: Job %s failed verification after commit!", job.id
                    )
                    raise Exception(f"Job {job.id} failed to save properly")

                # Only log and publish events if not skipped (to reduce noise)
                if not skip_events:
                    from app.utils.events import publish_job_event

                    logger.debug(
                        "📝 Job %s saved to database - created=%s - status=%s",
                        job.id,
                        was_created,
                        job.status.value,
                    )
                    publish_job_event(job.id, job.to_dict(), was_created)

        except Exception as e:
            logger.error("Error saving job %s: %s", job.id, e)
            traceback.print_exc()
            raise

    def get_job(self, job_id: str) -> Optional[Job]:
        """Retrieve a job from the database by its ID."""
        try:
            logger.debug("Attempting to retrieve job %s from database", job_id)

            with self.get_db_session() as session:
                db_job = session.query(DbJob).filter(DbJob.id == job_id).first()
                if not db_job:
                    logger.debug("Job %s not found in database", job_id)
                    return None
                else:
                    logger.debug("Found job %s with status %s", job_id, db_job.status)
                    return db_job.to_job()

        except Exception as e:
            logger.error("Error getting job %s: %s", job_id, e)
            traceback.print_exc()
            return None

    def get_by_id(self, job_id: str) -> Optional[Job]:
        """Retrieve a job from the database by its ID (standard naming convention)."""
        return self.get_job(job_id)

    def update(self, job: Job, skip_events: bool = False) -> None:
        """Update an existing job in the database.

        Args:
            job: The job to update
            skip_events: If True, skip database logging and event publishing
                        (useful for frequent progress updates)
        """
        return self.create(job, skip_events=skip_events)

    def get_all_jobs(self) -> List[Job]:
        """Retrieve all jobs from the database."""
        try:
            with self.get_db_session() as session:
                db_jobs = session.query(DbJob).all()
                return [db_job.to_job() for db_job in db_jobs]
        except Exception as e:
            logger.error("Error getting all jobs: %s", e, exc_info=True)
            return []

    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """Get jobs filtered by status."""
        try:
            with self.get_db_session() as session:
                db_jobs = (
                    session.query(DbJob).filter(DbJob.status == status.value).all()
                )
                return [db_job.to_job() for db_job in db_jobs]
        except Exception as e:
            logger.error(
                "Error getting jobs by status %s: %s", status, e, exc_info=True
            )
            return []

    def get_in_flight_jobs(self) -> List[Job]:
        """Get jobs that are actively being processed (pending, downloading, processing)."""
        try:
            in_flight_statuses = [
                JobStatus.PENDING.value,
                JobStatus.DOWNLOADING.value,
                JobStatus.PROCESSING.value,
            ]
            with self.get_db_session() as session:
                db_jobs = (
                    session.query(DbJob)
                    .filter(DbJob.status.in_(in_flight_statuses))
                    .all()
                )
                return [db_job.to_job() for db_job in db_jobs]
        except Exception as e:
            logger.error("Error getting in-flight jobs: %s", e, exc_info=True)
            return []

    def delete_job(self, job_id: str) -> bool:
        """Delete a job from the database."""
        try:
            with self.get_db_session() as session:
                db_job = session.query(DbJob).filter(DbJob.id == job_id).first()
                if db_job:
                    session.delete(db_job)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error("Error deleting job %s: %s", job_id, e, exc_info=True)
            return False

    def get_stats(self) -> dict[str, int]:
        """Get job statistics."""
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
            logger.error("Error getting job statistics: %s", e, exc_info=True)
            return {
                "total": 0,
                "queue_length": 0,
                "active_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "raw_failed": 0,
                "raw_cancelled": 0,
            }
