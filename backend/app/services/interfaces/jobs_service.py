"""
Jobs Service operations.

This module defines the contract for jobs services, ensuring consistent
behavior across different implementations.
"""

from typing import Optional, Protocol

from ...db.models import Job, JobStatus


class JobsServiceInterface(Protocol):
    """Interface for jobs queue service operations."""

    def get_all_jobs(self) -> list[Job]:
        """
        Get all jobs in the queue.

        Returns:
            List of Job objects sorted by creation time (newest first)
        """
        ...

    def get_jobs_by_status(self, status: JobStatus) -> list[Job]:
        """
        Get all jobs with a specific status.

        Args:
            status: The JobStatus to filter by

        Returns:
            List of Job objects with the specified status
        """
        ...

    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get a job by its ID.

        Args:
            job_id: The unique identifier for the job

        Returns:
            Job object if found, None otherwise
        """
        ...

    def get_job_with_details(self, job_id: str) -> Optional[dict]:
        """
        Get a job by its ID with additional details like file paths and completion estimates.

        Args:
            job_id: The unique identifier for the job

        Returns:
            Job dictionary with additional details if found, None otherwise
        """
        ...

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job by its ID.

        Args:
            job_id: The unique identifier for the job to cancel

        Returns:
            True if job was successfully cancelled, False otherwise
        """
        ...

    def dismiss_job(self, job_id: str) -> bool:
        """
        Dismiss a completed, failed, or cancelled job from the UI.

        Args:
            job_id: The unique identifier for the job to dismiss

        Returns:
            True if job was successfully dismissed, False otherwise
        """
        ...

    def get_active_jobs(self) -> list[Job]:
        """
        Get all non-dismissed jobs (for main queue display).

        Returns:
            List of non-dismissed jobs
        """
        ...

    def get_dismissed_jobs(self) -> list[Job]:
        """
        Get all dismissed jobs.

        Returns:
            List of dismissed jobs
        """
        ...

    def get_statistics(self) -> dict[str, int]:
        """
        Get statistics about jobs.

        Returns:
            Dictionary containing job statistics (total, pending, processing, etc.)
        """
        ...
