"""
Tests for JobsService implementation.

This module verifies that the JobsService correctly implements the business logic
that was extracted from the API controllers.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from pathlib import Path

from app.services.jobs_service import JobsService
from app.db.models import Job, JobStatus, JobStore


class TestJobsService:
    """Test the JobsService implementation."""

    def test_jobs_service_initialization(self):
        """Test that JobsService can be initialized correctly."""
        service = JobsService()
        assert service.job_store is not None
        assert service.file_service is not None

    def test_jobs_service_initialization_with_custom_job_store(self):
        """Test that JobsService can be initialized with a custom JobStore."""
        mock_job_store = Mock(spec=JobStore)
        service = JobsService(job_store=mock_job_store)
        assert service.job_store is mock_job_store

    def test_get_all_jobs_sorting(self):
        """Test that get_all_jobs returns jobs sorted by creation time."""
        mock_job_store = Mock(spec=JobStore)

        # Create mock jobs with different creation times
        job1 = Job(
            id="job1",
            filename="test1.mp3",
            status=JobStatus.PENDING,
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        )
        job2 = Job(
            id="job2",
            filename="test2.mp3",
            status=JobStatus.PENDING,
            created_at=datetime(2023, 1, 2, tzinfo=timezone.utc),
        )
        job3 = Job(
            id="job3",
            filename="test3.mp3",
            status=JobStatus.PENDING,
            created_at=datetime(2022, 12, 31, tzinfo=timezone.utc),  # Older date
        )

        # Mock both methods that could be called
        mock_job_store.get_active_jobs.return_value = [job1, job3, job2]
        mock_job_store.get_all_jobs.return_value = [job1, job3, job2]

        service = JobsService(job_store=mock_job_store)
        result = service.get_all_jobs()

        # Should be sorted newest first
        assert len(result) == 3
        assert result[0].id == "job2"  # Most recent (2023-01-02)
        assert result[1].id == "job1"  # Older (2023-01-01)
        assert result[2].id == "job3"  # Oldest (2022-12-31)

    def test_get_job_with_details_completed_job(self):
        """Test that get_job_with_details adds file paths for completed jobs."""
        mock_job_store = Mock(spec=JobStore)
        mock_file_service = Mock()

        completed_job = Job(
            id="completed_job", filename="test.mp3", status=JobStatus.COMPLETED
        )

        mock_job_store.get_job.return_value = completed_job
        mock_file_service.get_song_directory.return_value = Path("/test/library/test")

        with patch("app.services.jobs_service.file_management") as mock_file_mgmt:
            mock_file_mgmt.get_vocals_path_stem.return_value = Path(
                "/test/library/test/vocals"
            )
            mock_file_mgmt.get_instrumental_path_stem.return_value = Path(
                "/test/library/test/instrumental"
            )

            service = JobsService(job_store=mock_job_store)
            service.file_service = mock_file_service

            result = service.get_job_with_details("completed_job")

            assert result is not None
            assert "vocals_path" in result
            assert "instrumental_path" in result
            assert result["vocals_path"] == "/test/library/test/vocals.mp3"
            assert result["instrumental_path"] == "/test/library/test/instrumental.mp3"

    def test_cancel_job_success(self):
        """Test that cancel_job successfully cancels a pending job."""
        mock_job_store = Mock(spec=JobStore)

        pending_job = Job(
            id="pending_job", filename="test.mp3", status=JobStatus.PENDING
        )

        mock_job_store.get_job.return_value = pending_job

        service = JobsService(job_store=mock_job_store)
        result = service.cancel_job("pending_job")

        assert result is True
        assert pending_job.status == JobStatus.CANCELLED
        assert pending_job.error == "Cancelled by user"
        assert pending_job.completed_at is not None
        mock_job_store.save_job.assert_called_once_with(pending_job)

    def test_cancel_job_already_completed(self):
        """Test that cancel_job returns False for already completed jobs."""
        mock_job_store = Mock(spec=JobStore)

        completed_job = Job(
            id="completed_job", filename="test.mp3", status=JobStatus.COMPLETED
        )

        mock_job_store.get_job.return_value = completed_job

        service = JobsService(job_store=mock_job_store)
        result = service.cancel_job("completed_job")

        assert result is False
        mock_job_store.save_job.assert_not_called()

    def test_cancel_job_not_found(self):
        """Test that cancel_job returns False for non-existent jobs."""
        mock_job_store = Mock(spec=JobStore)
        mock_job_store.get_job.return_value = None

        service = JobsService(job_store=mock_job_store)
        result = service.cancel_job("nonexistent_job")

        assert result is False
        mock_job_store.save_job.assert_not_called()

    def test_get_statistics_delegates_to_job_store(self):
        """Test that get_statistics properly delegates to the job store."""
        mock_job_store = Mock(spec=JobStore)
        expected_stats = {
            "total": 10,
            "queue_length": 2,
            "active_jobs": 1,
            "completed_jobs": 7,
            "failed_jobs": 0,
        }
        mock_job_store.get_stats.return_value = expected_stats

        service = JobsService(job_store=mock_job_store)
        result = service.get_statistics()

        assert result == expected_stats
        mock_job_store.get_stats.assert_called_once()
