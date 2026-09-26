"""Integration tests for JobRepository against the throwaway test DB.

Uses the module-level `_global_engine` / autouse table-truncation fixture
from tests/conftest.py — JobRepository() talks to SessionLocal directly, so
it hits the same throwaway SQLite DB the rest of the suite uses.
"""

import uuid

import pytest

from app.db.models import Job, JobStatus
from app.repositories.job_repository import JobRepository


@pytest.fixture
def repo():
    return JobRepository()


def _make_job(status: JobStatus, song_id: str | None = None) -> Job:
    return Job(
        id=str(uuid.uuid4()),
        filename="original.mp3",
        status=status,
        song_id=song_id,
    )


class TestGetInFlightJobs:
    def test_excludes_failed_jobs(self, repo):
        failed = _make_job(JobStatus.FAILED)
        pending = _make_job(JobStatus.PENDING)
        repo.create(failed)
        repo.create(pending)

        in_flight = repo.get_in_flight_jobs()

        in_flight_ids = {j.id for j in in_flight}
        assert pending.id in in_flight_ids
        assert failed.id not in in_flight_ids

    def test_includes_all_in_flight_statuses(self, repo):
        jobs = [
            _make_job(JobStatus.PENDING),
            _make_job(JobStatus.DOWNLOADING),
            _make_job(JobStatus.PROCESSING),
        ]
        for job in jobs:
            repo.create(job)
        completed = _make_job(JobStatus.COMPLETED)
        cancelled = _make_job(JobStatus.CANCELLED)
        repo.create(completed)
        repo.create(cancelled)

        in_flight_ids = {j.id for j in repo.get_in_flight_jobs()}

        for job in jobs:
            assert job.id in in_flight_ids
        assert completed.id not in in_flight_ids
        assert cancelled.id not in in_flight_ids

    def test_empty_when_no_jobs(self, repo):
        assert repo.get_in_flight_jobs() == []


class TestCreateUpsert:
    def test_create_then_update_via_create(self, repo):
        job = _make_job(JobStatus.PENDING)
        repo.create(job)

        job.status = JobStatus.PROCESSING
        job.progress = 42
        repo.create(job)

        fetched = repo.get_job(job.id)
        assert fetched is not None
        assert fetched.status == JobStatus.PROCESSING
        assert fetched.progress == 42


class TestDeleteJob:
    def test_delete_removes_job(self, repo):
        job = _make_job(JobStatus.FAILED)
        repo.create(job)
        assert repo.get_job(job.id) is not None

        result = repo.delete_job(job.id)

        assert result is True
        assert repo.get_job(job.id) is None

    def test_delete_nonexistent_job_returns_false(self, repo):
        assert repo.delete_job(str(uuid.uuid4())) is False
