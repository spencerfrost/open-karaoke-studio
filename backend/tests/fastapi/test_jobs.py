"""FastAPI tests for /api/jobs endpoints."""
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.api.dependencies import get_current_user
from app.db.models import JobStatus
from tests.conftest import create_test_app
from fastapi.testclient import TestClient


def _get_mock_user():
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "testuser"
    mock_user.is_admin = True
    mock_user.is_host = True
    return mock_user


def _make_job(
    job_id="job-1",
    status=JobStatus.COMPLETED,
    song_id="song-1",
    dismissed=False,
    task_id=None,
):
    job = Mock()
    job.id = job_id
    job.song_id = song_id
    job.task_id = task_id
    job.status = status
    job.dismissed = dismissed
    job.progress = 0
    job.error_message = None
    job.created_at = None
    job.updated_at = None
    job.to_dict.return_value = {
        "id": job_id,
        "song_id": song_id,
        "status": status.value,
        "progress": 0,
        "dismissed": dismissed,
    }
    return job


@pytest.fixture(scope="module")
def app():
    app = create_test_app()
    app.dependency_overrides[get_current_user] = _get_mock_user
    return app


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_jobs_service(app):
    svc = MagicMock()
    svc.get_statistics.return_value = {
        "total": 5,
        "queue_length": 1,
        "active_jobs": 1,
        "completed_jobs": 2,
        "raw_failed": 1,
        "raw_cancelled": 0,
    }
    svc.get_all_jobs.return_value = [_make_job()]
    svc.get_active_jobs.return_value = [_make_job()]
    svc.get_dismissed_jobs.return_value = []
    svc.get_jobs_by_status.return_value = [_make_job()]
    svc.get_job.return_value = _make_job()
    svc.get_job_with_details.return_value = {"id": "job-1", "status": "completed"}
    svc.cancel_job.return_value = True
    svc.dismiss_job.return_value = True

    from app.api.jobs import get_jobs_service
    app.dependency_overrides[get_jobs_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_jobs_service, None)


class TestGetJobStatus:
    def test_returns_statistics(self, client, mock_jobs_service):
        response = client.get("/api/jobs/status")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert data["pending"] == 1
        assert data["processing"] == 1
        assert data["completed"] == 2
        assert data["failed"] == 1
        assert data["cancelled"] == 0


class TestGetJobs:
    def test_returns_active_jobs_by_default(self, client, mock_jobs_service):
        response = client.get("/api/jobs")
        assert response.status_code == 200
        assert "jobs" in response.json()
        mock_jobs_service.get_active_jobs.assert_called()

    def test_include_dismissed_calls_get_all(self, client, mock_jobs_service):
        mock_jobs_service.reset_mock()
        response = client.get("/api/jobs?include_dismissed=true")
        assert response.status_code == 200
        mock_jobs_service.get_all_jobs.assert_called_once_with(include_dismissed=True)

    def test_filter_by_valid_status(self, client, mock_jobs_service):
        mock_jobs_service.reset_mock()
        response = client.get("/api/jobs?status=completed")
        assert response.status_code == 200
        mock_jobs_service.get_jobs_by_status.assert_called_once_with(JobStatus.COMPLETED)

    def test_filter_by_invalid_status_returns_400(self, client, mock_jobs_service):
        response = client.get("/api/jobs?status=not_a_status")
        assert response.status_code == 400

    def test_filter_status_excludes_dismissed_by_default(self, client, mock_jobs_service):
        job = _make_job(dismissed=True)
        mock_jobs_service.get_jobs_by_status.return_value = [job, _make_job()]
        response = client.get("/api/jobs?status=completed")
        assert response.status_code == 200
        # Only the non-dismissed job should appear
        assert len(response.json()["jobs"]) == 1

    def test_service_error_returns_500(self, client, mock_jobs_service):
        mock_jobs_service.get_active_jobs.side_effect = RuntimeError("db down")
        response = client.get("/api/jobs")
        assert response.status_code == 500
        mock_jobs_service.get_active_jobs.side_effect = None


class TestGetDismissedJobs:
    def test_returns_dismissed_list(self, client, mock_jobs_service):
        dismissed = _make_job(dismissed=True)
        mock_jobs_service.get_dismissed_jobs.return_value = [dismissed]
        response = client.get("/api/jobs/dismissed")
        assert response.status_code == 200
        assert len(response.json()["jobs"]) == 1

    def test_service_error_returns_500(self, client, mock_jobs_service):
        mock_jobs_service.get_dismissed_jobs.side_effect = RuntimeError("fail")
        response = client.get("/api/jobs/dismissed")
        assert response.status_code == 500
        mock_jobs_service.get_dismissed_jobs.side_effect = None


class TestGetJob:
    def test_returns_job_details(self, client, mock_jobs_service):
        mock_jobs_service.get_job_with_details.return_value = {"id": "job-1", "status": "completed"}
        response = client.get("/api/jobs/job-1")
        assert response.status_code == 200
        assert response.json()["id"] == "job-1"

    def test_not_found_returns_404(self, client, mock_jobs_service):
        mock_jobs_service.get_job_with_details.return_value = None
        response = client.get("/api/jobs/no-such-job")
        assert response.status_code == 404
        mock_jobs_service.get_job_with_details.return_value = {"id": "job-1", "status": "completed"}


class TestCancelJob:
    def test_cancel_pending_job_succeeds(self, client, mock_jobs_service):
        mock_jobs_service.get_job.return_value = _make_job(status=JobStatus.PENDING)
        mock_jobs_service.cancel_job.return_value = True
        response = client.post("/api/jobs/job-1/cancel")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_cancel_nonexistent_job_returns_404(self, client, mock_jobs_service):
        mock_jobs_service.get_job.return_value = None
        response = client.post("/api/jobs/ghost/cancel")
        assert response.status_code == 404

    def test_cancel_completed_job_returns_400(self, client, mock_jobs_service):
        mock_jobs_service.get_job.return_value = _make_job(status=JobStatus.COMPLETED)
        response = client.post("/api/jobs/job-1/cancel")
        assert response.status_code == 400

    def test_cancel_service_failure_returns_500(self, client, mock_jobs_service):
        mock_jobs_service.get_job.return_value = _make_job(status=JobStatus.PENDING)
        mock_jobs_service.cancel_job.return_value = False
        response = client.post("/api/jobs/job-1/cancel")
        assert response.status_code == 500
        mock_jobs_service.cancel_job.return_value = True


class TestDismissJob:
    def test_dismiss_completed_job_succeeds(self, client, mock_jobs_service):
        mock_jobs_service.get_job.return_value = _make_job(status=JobStatus.COMPLETED)
        mock_jobs_service.dismiss_job.return_value = True
        response = client.post("/api/jobs/job-1/dismiss")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_dismiss_nonexistent_returns_404(self, client, mock_jobs_service):
        mock_jobs_service.get_job.return_value = None
        response = client.post("/api/jobs/ghost/dismiss")
        assert response.status_code == 404

    def test_dismiss_pending_job_returns_400(self, client, mock_jobs_service):
        mock_jobs_service.get_job.return_value = _make_job(status=JobStatus.PENDING)
        response = client.post("/api/jobs/job-1/dismiss")
        assert response.status_code == 400

    def test_dismiss_service_failure_returns_500(self, client, mock_jobs_service):
        mock_jobs_service.get_job.return_value = _make_job(status=JobStatus.FAILED)
        mock_jobs_service.dismiss_job.return_value = False
        response = client.post("/api/jobs/job-1/dismiss")
        assert response.status_code == 500
        mock_jobs_service.dismiss_job.return_value = True


class TestStartAudioProcessing:
    def test_returns_queued_job(self, client, mock_jobs_service):
        response = client.post("/api/jobs/process-audio", json={"song_id": "s-1"})
        assert response.status_code == 200
        assert response.json()["status"] == "queued"
        assert response.json()["id"] == "s-1"
