"""Transient processing failures (full GPU, network blip) retry instead of failing.

Runs process_youtube_job against the throwaway test database, mocking only
the download, the separation engine, and Celery dispatch.
"""

import uuid
from unittest.mock import Mock, patch

import pytest
import torch
from celery.exceptions import Retry

from app.db.database import get_db_session
from app.db.models import Job, JobStatus
from app.exceptions import ServiceError
from app.jobs.audio_tasks import TRANSIENT_RETRY_DELAYS, process_youtube_job
from app.jobs.exceptions import is_transient_processing_error
from app.repositories import JobRepository
from app.repositories.song_repository import SongRepository

VIDEO_ID = "JCf7lKL1UQ4"
METADATA = {"artist": "Hanumankind", "title": "Big Dawgs"}


@pytest.fixture
def song_and_job(tmp_path):
    song_id = str(uuid.uuid4())
    with get_db_session() as session:
        SongRepository(session).create(
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
        ),
        skip_events=True,
    )
    return song_id, job_id, tmp_path


@pytest.fixture
def pipeline(song_and_job):
    """Patch the pipeline's edges; the download writes a fake original.mp3."""
    song_id, _, library = song_and_job

    def fake_download(**kwargs):
        song_dir = library / song_id
        song_dir.mkdir(parents=True, exist_ok=True)
        (song_dir / "original.mp3").write_bytes(b"fake")
        return song_id, {}

    youtube_service = Mock()
    youtube_service.download_video.side_effect = fake_download
    with (
        patch(
            "app.config.get_config", return_value=Mock(BASE_LIBRARY_DIR=str(library))
        ),
        patch(
            "app.services.youtube_service.YouTubeService", return_value=youtube_service
        ),
        patch("app.jobs.audio_tasks.run_separation_with_fallback") as separation,
        patch("app.jobs.audio_tasks.celery.send_task") as send_task,
        patch.object(process_youtube_job, "retry", side_effect=Retry()) as retry,
        patch.object(process_youtube_job, "update_state"),
        patch("torch.cuda.empty_cache"),
    ):
        yield Mock(
            youtube=youtube_service,
            separation=separation,
            send_task=send_task,
            retry=retry,
        )


def _run(job_id, retries=0):
    process_youtube_job.push_request(retries=retries)
    try:
        return process_youtube_job.run(job_id, VIDEO_ID, METADATA)
    finally:
        process_youtube_job.pop_request()


def _song_status(song_id):
    with get_db_session() as session:
        song = SongRepository(session).fetch(song_id)
        return song.status, song.error_message


def test_gpu_out_of_memory_schedules_a_retry(song_and_job, pipeline):
    song_id, job_id, _ = song_and_job
    pipeline.separation.side_effect = torch.cuda.OutOfMemoryError("CUDA out of memory.")

    with pytest.raises(Retry):
        _run(job_id)

    assert pipeline.retry.call_args.kwargs["countdown"] == TRANSIENT_RETRY_DELAYS[0]
    assert _song_status(song_id) == ("processing", None)
    job = JobRepository().get_by_id(job_id)
    assert job.status == JobStatus.PENDING
    assert "trying again" in job.status_message


def test_retry_reuses_the_downloaded_audio(song_and_job, pipeline):
    song_id, job_id, library = song_and_job
    (library / song_id).mkdir(parents=True)
    (library / song_id / "original.mp3").write_bytes(b"fake")
    pipeline.separation.return_value = (True, "three_track")

    with patch("librosa.get_duration", return_value=191.0):
        result = _run(job_id, retries=1)

    assert result["status"] == "success"
    pipeline.youtube.download_video.assert_not_called()
    dispatched = [c.args[0] for c in pipeline.send_task.call_args_list]
    assert "fingerprint_single_song" not in dispatched
    assert _song_status(song_id)[0] == "processed"


def test_first_attempt_always_downloads(song_and_job, pipeline):
    song_id, job_id, library = song_and_job
    (library / song_id).mkdir(parents=True)
    (library / song_id / "original.mp3").write_bytes(b"stale")
    pipeline.separation.return_value = (True, "three_track")

    with patch("librosa.get_duration", return_value=191.0):
        _run(job_id, retries=0)

    pipeline.youtube.download_video.assert_called_once()


def test_out_of_retries_marks_the_song_failed_with_the_real_cause(
    song_and_job, pipeline
):
    song_id, job_id, _ = song_and_job
    pipeline.separation.side_effect = torch.cuda.OutOfMemoryError("CUDA out of memory.")

    result = _run(job_id, retries=process_youtube_job.max_retries)

    assert result["status"] == "error"
    pipeline.retry.assert_not_called()
    status, error_message = _song_status(song_id)
    assert status == "error"
    assert "CUDA out of memory" in error_message


def test_permanent_failure_does_not_retry(song_and_job, pipeline):
    song_id, job_id, _ = song_and_job
    pipeline.youtube.download_video.side_effect = ServiceError(
        "Failed to download YouTube video: Sign in to confirm your age"
    )

    result = _run(job_id)

    assert result["status"] == "error"
    pipeline.retry.assert_not_called()
    assert _song_status(song_id)[0] == "error"


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (torch.cuda.OutOfMemoryError("CUDA out of memory."), True),
        (
            ServiceError(
                "Failed to download YouTube video: Failed to resolve 'rr1---sn.googlevideo.com' "
                "([Errno -3] Temporary failure in name resolution)"
            ),
            True,
        ),
        (
            ServiceError(
                "Failed to download YouTube video: HTTP Error 503: Service Unavailable"
            ),
            True,
        ),
        (ServiceError("Failed to download YouTube video: Video unavailable"), False),
        (
            ServiceError("Failed to download YouTube video: HTTP Error 403: Forbidden"),
            False,
        ),
        (RuntimeError("Audio separation failed"), False),
    ],
)
def test_is_transient_processing_error(exc, expected):
    assert is_transient_processing_error(exc) is expected
