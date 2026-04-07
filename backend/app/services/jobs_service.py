"""
Jobs Service implementation.

This module handles all jobs-related business logic, providing a clean
separation between API controllers and data management.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.db.models import Job, JobStatus
from app.jobs.celery_app import celery
from app.repositories import JobRepository
from .interfaces.jobs_service import JobsServiceInterface

logger = logging.getLogger(__name__)


class JobsService(JobsServiceInterface):
    """Service for managing jobs operations."""

    def __init__(self, job_repository: Optional[JobRepository] = None):
        """
        Initialize the Jobs service.

        Args:
            job_repository: Optional JobRepository instance. If None, creates a new one.
        """
        self.job_repository = job_repository or JobRepository()

    def get_all_jobs(self) -> list[Job]:
        """Get all jobs sorted by creation time (newest first)."""
        jobs = self.job_repository.get_all_jobs()
        return sorted(jobs, key=self._get_created_time, reverse=True)

    def get_in_flight_jobs(self) -> list[Job]:
        """Get jobs that are actively being processed (pending, downloading, processing)."""
        jobs = self.job_repository.get_in_flight_jobs()
        return sorted(jobs, key=self._get_created_time, reverse=True)

    def get_jobs_by_status(self, status: JobStatus) -> list[Job]:
        """Get all jobs with a specific status."""
        return self.job_repository.get_jobs_by_status(status)

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by its ID."""
        return self.job_repository.get_job(job_id)

    def get_job_with_details(self, job_id: str) -> Optional[dict]:
        """
        Get a job by its ID with additional details like file paths and
        completion estimates.
        """
        job = self.job_repository.get_job(job_id)
        if not job:
            return None

        response = job.to_dict()

        # Estimate completion time if processing
        if job.status == JobStatus.PROCESSING and job.started_at:
            estimated_completion = self._estimate_completion_time(job)
            if estimated_completion:
                response["expected_completion"] = estimated_completion.isoformat()

        return response

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job by its ID.

        Returns:
            True if job was successfully cancelled
            False if job not found or cannot be cancelled
        """
        job = self.job_repository.get_job(job_id)
        if not job:
            return False

        # Check if job can be cancelled
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False

        # Revoke the Celery task if it has a task_id
        if job.task_id:
            try:
                celery.control.revoke(job.task_id, terminate=True, signal="SIGTERM")
                logger.info("Revoked Celery task %s for job %s", job.task_id, job_id)
            except Exception as e:
                logger.warning(
                    "Failed to revoke Celery task %s: %s", job.task_id, e, exc_info=True
                )

        # Update job status
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now(timezone.utc)
        job.error = "Cancelled by user"
        self.job_repository.update(job)

        return True

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job record from the database.

        Returns:
            True if job was successfully deleted, False otherwise
        """
        return self.job_repository.delete_job(job_id)

    def get_statistics(self) -> "dict[str, int]":
        """Get statistics about jobs."""
        if hasattr(self.job_repository, "get_stats"):
            return self.job_repository.get_stats()
        jobs = self.job_repository.get_all_jobs()
        stats = {
            "total": len(jobs),
            "queue_length": len([j for j in jobs if j.status == JobStatus.PENDING]),
            "active_jobs": len([j for j in jobs if j.status == JobStatus.PROCESSING]),
            "completed_jobs": len([j for j in jobs if j.status == JobStatus.COMPLETED]),
            "failed_jobs": len(
                [j for j in jobs if j.status in [JobStatus.FAILED, JobStatus.CANCELLED]]
            ),
            "raw_failed": len([j for j in jobs if j.status == JobStatus.FAILED]),
            "raw_cancelled": len([j for j in jobs if j.status == JobStatus.CANCELLED]),
        }
        return stats

    @staticmethod
    def _get_created_time(job: Job) -> datetime:
        if job.created_at is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if job.created_at.tzinfo is None:
            return job.created_at.replace(tzinfo=timezone.utc)
        return job.created_at

    def _estimate_completion_time(self, job: Job) -> Optional[datetime]:
        """
        Estimate completion time for a processing job based on current progress.
        """
        if not job.started_at or job.progress <= 0:
            return None

        elapsed_time = (datetime.now() - job.started_at).total_seconds()
        if elapsed_time <= 0:
            return None

        time_per_percent = elapsed_time / job.progress
        remaining_percent = 100 - job.progress
        estimated_remaining = remaining_percent * time_per_percent

        return datetime.now() + timedelta(seconds=estimated_remaining)
