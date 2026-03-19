"""Extended tests for JobsService covering paths not in test_jobs_service.py."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.db.models import Job, JobStatus
from app.services.jobs_service import JobsService


def _make_mock_job(
    job_id="job-1",
    status=JobStatus.COMPLETED,
    created_at=None,
    started_at=None,
    progress=50,
    task_id=None,
):
    job = MagicMock()
    job.id = job_id
    job.status = status
    job.created_at = created_at or datetime(2026, 1, 1, tzinfo=timezone.utc)
    job.started_at = started_at
    job.progress = progress
    job.task_id = task_id
    job.to_dict.return_value = {"id": job_id, "status": status.value}
    return job


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def service(mock_repo):
    return JobsService(job_repository=mock_repo)


def test_get_jobs_by_status_delegates_to_repo(service, mock_repo):
    expected = [_make_mock_job(status=JobStatus.PENDING)]
    mock_repo.get_jobs_by_status.return_value = expected
    result = service.get_jobs_by_status(JobStatus.PENDING)
    assert result == expected
    mock_repo.get_jobs_by_status.assert_called_once_with(JobStatus.PENDING)


def test_get_dismissed_jobs_sorted_newest_first(service, mock_repo):
    older = _make_mock_job("old", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    newer = _make_mock_job("new", created_at=datetime(2026, 6, 1, tzinfo=timezone.utc))
    mock_repo.get_dismissed_jobs.return_value = [older, newer]
    result = service.get_dismissed_jobs()
    assert result[0].id == "new"
    assert result[1].id == "old"


def test_get_dismissed_jobs_handles_none_created_at(service, mock_repo):
    job = _make_mock_job("j1")
    job.created_at = None
    mock_repo.get_dismissed_jobs.return_value = [job]
    result = service.get_dismissed_jobs()
    assert len(result) == 1


def test_cancel_job_already_cancelled_returns_false(service, mock_repo):
    mock_repo.get_job.return_value = _make_mock_job(status=JobStatus.CANCELLED)
    assert service.cancel_job("job-1") is False


def test_cancel_job_with_task_id_revokes_celery(service, mock_repo):
    job = _make_mock_job(status=JobStatus.PENDING, task_id="celery-abc")
    mock_repo.get_job.return_value = job
    with patch("app.services.jobs_service.celery") as mock_celery:
        result = service.cancel_job("job-1")
    assert result is True
    mock_celery.control.revoke.assert_called_once_with(
        "celery-abc", terminate=True, signal="SIGTERM"
    )


def test_cancel_job_celery_failure_still_cancels_job(service, mock_repo):
    job = _make_mock_job(status=JobStatus.PENDING, task_id="celery-abc")
    mock_repo.get_job.return_value = job
    with patch("app.services.jobs_service.celery") as mock_celery:
        mock_celery.control.revoke.side_effect = Exception("Celery error")
        result = service.cancel_job("job-1")
    assert result is True
    assert job.status == JobStatus.CANCELLED


def test_dismiss_job_returns_false_for_missing_job(service, mock_repo):
    mock_repo.get_job.return_value = None
    assert service.dismiss_job("missing") is False


def test_dismiss_job_returns_false_for_pending(service, mock_repo):
    mock_repo.get_job.return_value = _make_mock_job(status=JobStatus.PENDING)
    assert service.dismiss_job("job-1") is False


def test_dismiss_job_returns_false_for_processing(service, mock_repo):
    mock_repo.get_job.return_value = _make_mock_job(status=JobStatus.PROCESSING)
    assert service.dismiss_job("job-1") is False


def test_dismiss_job_completed_delegates_to_repo(service, mock_repo):
    mock_repo.get_job.return_value = _make_mock_job(status=JobStatus.COMPLETED)
    mock_repo.dismiss_job.return_value = True
    assert service.dismiss_job("job-1") is True
    mock_repo.dismiss_job.assert_called_once_with("job-1")


def test_dismiss_job_failed_succeeds(service, mock_repo):
    mock_repo.get_job.return_value = _make_mock_job(status=JobStatus.FAILED)
    mock_repo.dismiss_job.return_value = True
    assert service.dismiss_job("job-1") is True


def test_get_statistics_manual_computation_when_no_get_stats(service, mock_repo):
    # Remove get_stats attribute so service computes manually
    del mock_repo.get_stats
    jobs = [
        _make_mock_job("1", status=JobStatus.PENDING),
        _make_mock_job("2", status=JobStatus.PROCESSING),
        _make_mock_job("3", status=JobStatus.COMPLETED),
        _make_mock_job("4", status=JobStatus.FAILED),
        _make_mock_job("5", status=JobStatus.CANCELLED),
    ]
    mock_repo.get_all_jobs.return_value = jobs
    result = service.get_statistics()
    assert result["total"] == 5
    assert result["queue_length"] == 1
    assert result["active_jobs"] == 1
    assert result["completed_jobs"] == 1
    assert result["failed_jobs"] == 2
    assert result["raw_failed"] == 1
    assert result["raw_cancelled"] == 1


def test_estimate_completion_time_returns_none_when_no_started_at(service):
    job = _make_mock_job(started_at=None, progress=50)
    assert service._estimate_completion_time(job) is None


def test_estimate_completion_time_returns_none_when_zero_progress(service):
    job = _make_mock_job(started_at=datetime.now() - timedelta(seconds=60), progress=0)
    assert service._estimate_completion_time(job) is None


def test_estimate_completion_time_returns_future_datetime(service):
    started = datetime.now() - timedelta(seconds=60)
    job = _make_mock_job(started_at=started, progress=50)
    result = service._estimate_completion_time(job)
    assert result is not None
    assert result > datetime.now()


def test_get_job_with_details_adds_estimate_when_processing(service, mock_repo):
    started = datetime.now() - timedelta(seconds=60)
    job = _make_mock_job(status=JobStatus.PROCESSING, started_at=started, progress=50)
    mock_repo.get_job.return_value = job
    result = service.get_job_with_details("job-1")
    assert "expected_completion" in result


def test_get_job_with_details_no_estimate_when_progress_zero(service, mock_repo):
    started = datetime.now() - timedelta(seconds=60)
    job = _make_mock_job(status=JobStatus.PROCESSING, started_at=started, progress=0)
    mock_repo.get_job.return_value = job
    result = service.get_job_with_details("job-1")
    assert "expected_completion" not in result


def test_get_all_jobs_include_dismissed_calls_get_all(service, mock_repo):
    mock_repo.get_all_jobs.return_value = []
    service.get_all_jobs(include_dismissed=True)
    mock_repo.get_all_jobs.assert_called_once()
    mock_repo.get_active_jobs.assert_not_called()


def test_get_all_jobs_handles_naive_datetime(service, mock_repo):
    job = _make_mock_job(created_at=datetime(2026, 1, 1))  # no tzinfo
    mock_repo.get_active_jobs.return_value = [job]
    result = service.get_all_jobs()
    assert len(result) == 1
