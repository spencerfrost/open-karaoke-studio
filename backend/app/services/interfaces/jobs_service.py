# pylint: disable=unnecessary-ellipsis
"""
Jobs Service operations.

This module defines the contract for jobs services, ensuring consistent
behavior across different implementations.
"""

from typing import Optional, Protocol

from app.db.models import Job, JobStatus


class JobsServiceInterface(Protocol):
    """Interface for jobs queue service operations."""

    def get_all_jobs(self) -> list[Job]:
        """
        Get all jobs in the queue.

        Returns:
            List of Job objects sorted by creation time (newest first)
        """
        ...

    def get_in_flight_jobs(self) -> list[Job]:
        """
        Get jobs that are actively being processed (pending, downloading, processing).

        Returns:
            List of in-flight Job objects
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

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job record from the database.

        Args:
            job_id: The unique identifier for the job to delete

        Returns:
            True if job was successfully deleted, False otherwise
        """
        ...

    def get_statistics(self) -> dict[str, int]:
        """
        Get statistics about jobs.

        Returns:
            Dictionary containing job statistics (total, pending, processing, etc.)
        """
        ...
