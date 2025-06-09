"""
Jobs Service implementation.

This module handles all jobs-related business logic, providing a clean
separation between API controllers and data management.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .interfaces.jobs_service import JobsServiceInterface
from ..db.models import Job, JobStatus, JobStore
from . import file_management, FileService


class JobsService(JobsServiceInterface):
    """Service for managing jobs operations."""

    def __init__(self, job_store: Optional[JobStore] = None):
        """
        Initialize the Jobs service.
        
        Args:
            job_store: Optional JobStore instance. If None, creates a new one.
        """
        self.job_store = job_store or JobStore()
        self.file_service = FileService()

    def get_all_jobs(self, include_dismissed: bool = False) -> List[Job]:
        """Get all jobs sorted by creation time (newest first)."""
        if include_dismissed:
            jobs = self.job_store.get_all_jobs()
        else:
            jobs = self.job_store.get_active_jobs()
        
        def get_created_time(job):
            if job.created_at is None:
                # Return minimum datetime so None values sort last when reverse=True
                return datetime.min.replace(tzinfo=timezone.utc)

            if job.created_at.tzinfo is None:
                return job.created_at.replace(tzinfo=timezone.utc)
            return job.created_at

        return sorted(jobs, key=get_created_time, reverse=True)

    def get_active_jobs(self) -> List[Job]:
        """Get all non-dismissed jobs (for main queue display)."""
        return self.get_all_jobs(include_dismissed=False)

    def get_dismissed_jobs(self) -> List[Job]:
        """Get all dismissed jobs."""
        jobs = self.job_store.get_dismissed_jobs()
        
        def get_created_time(job):
            if job.created_at is None:
                return datetime.min.replace(tzinfo=timezone.utc)
            if job.created_at.tzinfo is None:
                return job.created_at.replace(tzinfo=timezone.utc)
            return job.created_at

        return sorted(jobs, key=get_created_time, reverse=True)

    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """Get all jobs with a specific status."""
        return self.job_store.get_jobs_by_status(status)

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by its ID."""
        return self.job_store.get_job(job_id)

    def get_job_with_details(self, job_id: str) -> Optional[Dict]:
        """
        Get a job by its ID with additional details like file paths and completion estimates.
        """
        job = self.job_store.get_job(job_id)
        if not job:
            return None

        response = job.to_dict()

        # Add additional info for completed jobs
        if job.status == JobStatus.COMPLETED:
            song_dir = self.file_service.get_song_directory(Path(job.filename).stem)
            vocals_path = file_management.get_vocals_path_stem(song_dir).with_suffix(".mp3")
            instrumental_path = file_management.get_instrumental_path_stem(song_dir).with_suffix(".mp3")

            response.update({
                "vocals_path": str(vocals_path),
                "instrumental_path": str(instrumental_path),
            })

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
            True if job was successfully cancelled, False if job not found or cannot be cancelled
        """
        job = self.job_store.get_job(job_id)
        if not job:
            return False

        # Check if job can be cancelled
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False

        # Update job status
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now()
        job.error = "Cancelled by user"
        self.job_store.save_job(job)

        # TODO: Implement actual job cancellation in Celery
        # This would involve celery.control.revoke(task_id, terminate=True)

        return True

    def dismiss_job(self, job_id: str) -> bool:
        """
        Dismiss a completed, failed, or cancelled job from the UI.
        Job is hidden but kept in database for potential retry.
        
        Returns:
            True if job was successfully dismissed, False if job not found or cannot be dismissed
        """
        job = self.job_store.get_job(job_id)
        if not job:
            return False

        # Check if job can be dismissed (only final states)
        if job.status not in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False

        # Use the job store's dismiss method
        return self.job_store.dismiss_job(job_id)

    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about jobs."""
        return self.job_store.get_stats()

    def _estimate_completion_time(self, job: Job) -> Optional[datetime]:
        """
        Estimate completion time for a processing job based on current progress.
        
        Args:
            job: The job to estimate completion time for
            
        Returns:
            Estimated completion datetime, or None if cannot be estimated
        """
        if not job.started_at or job.progress <= 0:
            return None

        elapsed_time = (datetime.now() - job.started_at).total_seconds()
        if elapsed_time <= 0:
            return None

        # Estimate based on current progress
        time_per_percent = elapsed_time / job.progress
        remaining_percent = 100 - job.progress
        estimated_remaining = remaining_percent * time_per_percent

        return datetime.now() + timedelta(seconds=estimated_remaining)

    def _broadcast_job_event(self, job: Job, was_created: bool = False):
        """
        Broadcast a job event via WebSocket if available.
        
        Args:
            job: The job object
            was_created: Whether this is a newly created job
        """
        try:
            from ..websockets.jobs_ws import (
                broadcast_job_update,
                broadcast_job_created,
                broadcast_job_completed,
                broadcast_job_failed,
                broadcast_job_cancelled
            )
            
            job_data = job.to_dict()
            
            # Determine the appropriate broadcast function
            if was_created:
                broadcast_job_created(job_data)
            else:
                # Map job status to appropriate event type
                if job.status == JobStatus.COMPLETED:
                    broadcast_job_completed(job_data)
                elif job.status == JobStatus.FAILED:
                    broadcast_job_failed(job_data)
                elif job.status == JobStatus.CANCELLED:
                    broadcast_job_cancelled(job_data)
                else:
                    # For PENDING, PROCESSING, or other statuses
                    broadcast_job_update(job_data)
                    
        except ImportError:
            # WebSocket module not available, skip broadcasting
            pass
        except Exception as e:
            # Log error but don't fail the operation
            import logging
            logging.getLogger(__name__).warning(f"Failed to broadcast job event: {e}")
