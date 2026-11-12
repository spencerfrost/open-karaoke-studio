"""Finished downloads keep counting against the demo download quotas.

The quotas count `jobs` rows, so a download must leave its row behind when it
finishes. Runs process_youtube_job to completion against the test database,
mocking only the download, the separation engine and Celery dispatch, then asks
the quota check whether the demo session may download again.
"""

import uuid
from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.api.dependencies import RequesterContext
from app.db.models import DbJob, Job, JobStatus, KaraokeSession, User
from app.jobs.audio_tasks import process_youtube_job
from app.repositories import JobRepository
from app.repositories.song_repository import SongRepository
from app.services.demo_service import (
    DEMO_DAILY_DOWNLOAD_LIMIT,
    DEMO_SESSION_DOWNLOAD_LIMIT,
    enforce_demo_download_quota,
)
from app.utils.clock import utc_now

VIDEO_ID = "JCf7lKL1UQ4"
METADATA = {"artist": "Hanumankind", "title": "Big Dawgs"}


@pytest.fixture
def demo_session(db):
    user = User(username="demo-pool-1", display_name="Demo Host")
    user.set_password("secret")
    user.is_host = True
    user.is_demo = True
    db.add(user)
    db.commit()
    session = KaraokeSession(
        session_id="DEMO",
        display_code="DEMO",
        host_device_id="demo_device",
        host_user_id=user.id,
        expires_at=utc_now() + timedelta(minutes=15),
        is_active=True,
    )
    db.add(session)
    db.commit()
    return session.session_id


@pytest.fixture
def pipeline(library):
    """Patch the pipeline's edges; the download writes a fake original.mp3."""

    def fake_download(**kwargs):
        song_dir = library / kwargs["song_id"]
        song_dir.mkdir(parents=True, exist_ok=True)
        (song_dir / "original.mp3").write_bytes(b"fake")
        return kwargs["song_id"], {}

    youtube_service = Mock()
    youtube_service.download_video.side_effect = fake_download
    with (
        patch(
            "app.services.youtube_service.YouTubeService", return_value=youtube_service
        ),
        patch(
            "app.jobs.audio_tasks.run_separation_with_fallback",
            return_value=(True, "three_track"),
        ),
        patch("app.jobs.audio_tasks.celery.send_task"),
        patch.object(process_youtube_job, "update_state"),
        patch("librosa.get_duration", return_value=191.0),
        patch("torch.cuda.empty_cache"),
    ):
        yield


def _finish_download(db, session_id):
    """Queue a download for the session the way the API does, and run it."""
    song_id = str(uuid.uuid4())
    SongRepository(db).create(
        {
            "id": song_id,
            "title": "Big Dawgs",
            "artist": "Hanumankind",
            "video_id": VIDEO_ID,
            "status": "processing",
        }
    )
    job_id = str(uuid.uuid4())
    JobRepository().create(
        Job(
            id=job_id,
            filename="original.mp3",
            status=JobStatus.PENDING,
            song_id=song_id,
            session_id=session_id,
        ),
        skip_events=True,
    )
    process_youtube_job.push_request(retries=0)
    try:
        result = process_youtube_job.run(job_id, VIDEO_ID, METADATA)
    finally:
        process_youtube_job.pop_request()
    assert result["status"] == "success"
    return job_id


def test_finished_download_keeps_its_job_row(db, demo_session, pipeline):
    job_id = _finish_download(db, demo_session)

    job = JobRepository().get_by_id(job_id)
    assert job is not None
    assert job.status == JobStatus.COMPLETED
    assert job.session_id == demo_session


def test_finished_downloads_count_toward_the_session_cap(db, demo_session, pipeline):
    for _ in range(DEMO_SESSION_DOWNLOAD_LIMIT):
        _finish_download(db, demo_session)

    with pytest.raises(HTTPException) as exc:
        enforce_demo_download_quota(db, RequesterContext(session_id=demo_session))

    assert exc.value.status_code == 429
    assert f"{DEMO_SESSION_DOWNLOAD_LIMIT} new songs" in exc.value.detail


def test_finished_downloads_count_toward_the_daily_cap(db, demo_session, pipeline):
    # Earlier visitors' finished downloads, on another session in the pool.
    earlier = KaraokeSession(
        session_id="PAST",
        display_code="PAST",
        host_device_id="demo_device",
        host_user_id=db.query(KaraokeSession).one().host_user_id,
        expires_at=utc_now() - timedelta(minutes=1),
        is_active=False,
    )
    earlier.created_at = utc_now() - timedelta(hours=2)
    db.add(earlier)
    db.commit()
    for _ in range(DEMO_DAILY_DOWNLOAD_LIMIT):
        _finish_download(db, "PAST")
    assert db.query(DbJob).filter(DbJob.session_id == "PAST").count() == (
        DEMO_DAILY_DOWNLOAD_LIMIT
    )

    with pytest.raises(HTTPException) as exc:
        enforce_demo_download_quota(db, RequesterContext(session_id=demo_session))

    assert exc.value.status_code == 429
    assert "daily" in exc.value.detail
