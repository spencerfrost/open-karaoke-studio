"""A full GPU makes lyrics alignment wait and retry, never store a worse result.

Separation and alignment run in separate workers that can share the GPU, so an
out-of-memory error during alignment says nothing about the song.
"""

import logging
from contextlib import ExitStack, nullcontext
from unittest.mock import Mock, patch

import pytest
import torch
from celery.exceptions import Retry

from app.db.models import JobStatus
from app.jobs._shared import TRANSIENT_RETRY_DELAYS
from app.jobs.lyrics_tasks import align_song_lyrics
from app.services.gpu_memory import is_cuda_out_of_memory, track_gpu_memory

SONG_ID = "song-gpu-full"
SYNCED = "[00:01.00]Is this the real life"
# What faster-whisper (CTranslate2) raises: a plain RuntimeError.
CT2_OOM = RuntimeError("CUDA failed with error out of memory")


@pytest.fixture
def vocals(library):
    song_dir = library / SONG_ID
    song_dir.mkdir()
    (song_dir / "vocals.mp3").write_bytes(b"fake")


def _run(*, attempt_error, retries=0):
    """Run align_song_lyrics with one stored LRC attempt that hits `attempt_error`."""
    attempt = {
        "content": SYNCED,
        "source_type": "synced",
        "source": "db:synced",
        "persist": False,
    }
    with ExitStack() as stack:
        mocks = Mock()
        mocks.update = stack.enter_context(
            patch("app.jobs.lyrics_tasks._update_lyrics_alignment_job")
        )
        mocks.complete = stack.enter_context(
            patch("app.jobs.lyrics_tasks._complete_lyrics_alignment_job")
        )
        mocks.transcribe = stack.enter_context(
            patch("app.services.lyrics_transcription.transcribe_lyrics_from_vocals")
        )
        mocks.retry = stack.enter_context(
            patch.object(align_song_lyrics, "retry", side_effect=Retry())
        )
        stack.enter_context(
            patch(
                "app.jobs.lyrics_tasks._build_alignment_attempts",
                return_value=[attempt],
            )
        )
        stack.enter_context(
            patch(
                "app.jobs.lyrics_tasks.run_alignment_attempt", side_effect=attempt_error
            )
        )
        stack.enter_context(
            patch("app.jobs.lyrics_tasks._apply_offset_correction", return_value=None)
        )
        stack.enter_context(
            patch(
                "app.jobs.lyrics_tasks.track_gpu_memory",
                side_effect=lambda *_args, **_kwargs: nullcontext(),
            )
        )
        align_song_lyrics.push_request(retries=retries)
        try:
            mocks.result = align_song_lyrics.run(SONG_ID)
        except Retry:
            mocks.result = Retry
        finally:
            align_song_lyrics.pop_request()
    return mocks


def test_a_full_gpu_parks_the_job_and_retries(add_song, fetch_song, vocals):
    add_song(SONG_ID, language="en", synced_lyrics=SYNCED)

    mocks = _run(attempt_error=CT2_OOM)

    assert mocks.result is Retry
    assert mocks.retry.call_args.kwargs["countdown"] == TRANSIENT_RETRY_DELAYS[0]
    last_update = mocks.update.call_args
    assert last_update.kwargs["status"] == JobStatus.PENDING
    assert "trying again in 1 min" in last_update.kwargs["message"]
    # It didn't fall back to transcribing, or store anything.
    mocks.transcribe.assert_not_called()
    mocks.complete.assert_not_called()
    song = fetch_song(SONG_ID)
    assert song.synced_lyrics == SYNCED
    assert song.word_synced_lyrics is None


def test_later_retries_wait_longer(add_song, vocals):
    add_song(SONG_ID, language="en", synced_lyrics=SYNCED)

    mocks = _run(attempt_error=CT2_OOM, retries=1)

    assert mocks.retry.call_args.kwargs["countdown"] == TRANSIENT_RETRY_DELAYS[1]


def test_it_gives_up_after_the_last_wait(add_song, fetch_song, vocals):
    add_song(SONG_ID, language="en", synced_lyrics=SYNCED)

    mocks = _run(attempt_error=CT2_OOM, retries=len(TRANSIENT_RETRY_DELAYS))

    assert mocks.result == {"status": "gpu_full", "song_id": SONG_ID}
    mocks.retry.assert_not_called()
    assert mocks.complete.call_args.kwargs["status"] == JobStatus.FAILED
    assert fetch_song(SONG_ID).synced_lyrics == SYNCED


def test_any_other_attempt_failure_is_not_a_retry(add_song, vocals):
    add_song(SONG_ID, language="en", synced_lyrics=SYNCED)

    mocks = _run(attempt_error=ValueError("words didn't line up"))

    mocks.retry.assert_not_called()
    assert mocks.result is not Retry


@pytest.mark.parametrize(
    "exc",
    [
        torch.cuda.OutOfMemoryError("CUDA out of memory. Tried to allocate 2.00 GiB"),
        CT2_OOM,
        RuntimeError("cuDNN error: CUDNN_STATUS_ALLOC_FAILED"),
    ],
)
def test_out_of_memory_in_any_library_is_recognised(exc):
    assert is_cuda_out_of_memory(exc)


def test_out_of_memory_is_found_under_a_wrapping_error():
    try:
        try:
            raise CT2_OOM
        except RuntimeError as inner:
            raise ValueError("alignment attempt failed") from inner
    except ValueError as outer:
        assert is_cuda_out_of_memory(outer)


def test_other_errors_are_not_out_of_memory():
    assert not is_cuda_out_of_memory(ValueError("no words"))


def test_language_detection_lets_a_full_gpu_through(tmp_path):
    from app.services.lyrics_language import detect_vocals_language

    with patch("faster_whisper.WhisperModel", side_effect=CT2_OOM):
        with pytest.raises(RuntimeError):
            detect_vocals_language(SONG_ID, tmp_path / "vocals.mp3", device="cuda")
    with patch("faster_whisper.WhisperModel", side_effect=ValueError("silent")):
        assert detect_vocals_language(SONG_ID, tmp_path / "vocals.mp3") is None


def test_measuring_logs_the_cards_peak():
    mib = 1024 * 1024
    readings = iter([3000 * mib, 7000 * mib])
    pynvml = Mock()
    pynvml.nvmlDeviceGetMemoryInfo.side_effect = lambda _handle: Mock(
        total=12288 * mib, used=next(readings, 5000 * mib)
    )

    with (
        patch.dict("sys.modules", {"pynvml": pynvml}),
        patch("app.services.gpu_memory.logger") as logger,
    ):
        with track_gpu_memory("lyrics", SONG_ID):
            pass

    level, template, *args = logger.log.call_args.args
    line = template % tuple(args)
    assert level == logging.INFO
    assert "card peaked at 7000 of 12288 MiB" in line
    assert "3000 MiB at start" in line
    assert "5288 MiB free at the tightest" in line
    pynvml.nvmlShutdown.assert_called_once()


def test_a_nearly_full_card_is_a_warning():
    mib = 1024 * 1024
    pynvml = Mock()
    pynvml.nvmlDeviceGetMemoryInfo.side_effect = lambda _handle: Mock(
        total=12288 * mib, used=11800 * mib
    )

    with (
        patch.dict("sys.modules", {"pynvml": pynvml}),
        patch("app.services.gpu_memory.logger") as logger,
    ):
        with track_gpu_memory("separation", SONG_ID):
            pass

    assert logger.log.call_args.args[0] == logging.WARNING


def test_measuring_without_a_gpu_does_nothing():
    with (
        patch.dict("sys.modules", {"pynvml": None}),
        patch("app.services.gpu_memory.logger") as logger,
    ):
        with track_gpu_memory("lyrics", SONG_ID):
            pass

    logger.log.assert_not_called()
