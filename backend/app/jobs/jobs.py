"""Backward-compatible exports for job tasks and helpers.

This module intentionally re-exports task functions from the split job modules so
existing imports (for API endpoints and tests) keep working.
"""

from pathlib import Path
from typing import Callable, Optional

from app.services.gpu_idle_cleanup import begin_gpu_activity, end_gpu_activity
from app.services.separation_engines import (
    separate_with_clean_backing,
    separate_with_demucs,
    separate_with_hybrid,
    separate_with_roformer,
    separate_with_three_track,
    separate_with_three_track_duality_v2,
    separate_with_three_track_mel1143,
)

from ._events import setup_event_subscriptions as _setup_event_subscriptions
from .audio_tasks import process_audio_job, process_youtube_job
from .batch_tasks import (
    batch_align_lyrics,
    batch_backfill_artwork,
    batch_backfill_duration,
    batch_fingerprint_songs,
)
from .enrichment_tasks import cleanup_old_jobs, post_process_song
from .exceptions import AudioProcessingError
from .lyrics_tasks import align_song_lyrics
from .metadata_tasks import (
    detect_song_chords,
    detect_song_loudness,
    detect_song_vocal_range,
    enrich_song_artist_credits,
    fetch_song_artwork,
    fingerprint_single_song,
)


def select_and_run_separation_engine(
    engine_type: str,
    input_path: Path,
    song_dir: Path,
    status_callback: Callable[[str], None],
    stop_event,
    on_vocals_ready: Optional[Callable[[Path], None]] = None,
) -> bool:
    """Compatibility wrapper used by tests and older imports."""
    engine_map = {
        "roformer": separate_with_roformer,
        "hybrid": separate_with_hybrid,
        "clean_backing": separate_with_clean_backing,
        "three_track": separate_with_three_track,
        "three_track_duality_v2": separate_with_three_track_duality_v2,
        "three_track_mel1143": separate_with_three_track_mel1143,
    }

    separator_fn = engine_map.get(engine_type, separate_with_demucs)

    kwargs = {
        "input_path": input_path,
        "song_dir": song_dir,
        "status_callback": status_callback,
        "stop_event": stop_event,
    }
    if engine_type.startswith("three_track") and on_vocals_ready is not None:
        kwargs["on_vocals_ready"] = on_vocals_ready

    return separator_fn(**kwargs)


def run_separation_with_fallback(
    engine_type: str,
    input_path: Path,
    song_dir: Path,
    status_callback: Callable[[str], None],
    stop_event,
    on_vocals_ready: Optional[Callable[[Path], None]] = None,
) -> tuple[bool, str]:
    """Compatibility wrapper for legacy imports."""
    begin_gpu_activity(f"audio-separation:{engine_type}")
    try:
        success = select_and_run_separation_engine(
            engine_type=engine_type,
            input_path=input_path,
            song_dir=song_dir,
            status_callback=status_callback,
            stop_event=stop_event,
            on_vocals_ready=on_vocals_ready,
        )
        if success or not engine_type.startswith("three_track"):
            return success, engine_type

        status_callback("Three-track separation failed, retrying with demucs fallback...")
        fallback_success = select_and_run_separation_engine(
            engine_type="demucs",
            input_path=input_path,
            song_dir=song_dir,
            status_callback=status_callback,
            stop_event=stop_event,
        )
        return fallback_success, "demucs"
    finally:
        end_gpu_activity(f"audio-separation:{engine_type}")


def _get_lyrics_job_id(song_id: str) -> str:
    from ._shared import _get_lyrics_job_id as _impl

    return _impl(song_id)


def _make_alignment_cache_key(*, source_type: str, content: str, language: str, alignment_mode: str):
    from ._shared import _make_alignment_cache_key as _impl

    return _impl(
        source_type=source_type,
        content=content,
        language=language,
        alignment_mode=alignment_mode,
    )


def _create_lyrics_alignment_job(
    song_id: str,
    title: Optional[str] = None,
    artist: Optional[str] = None,
    task_id: Optional[str] = None,
    status_message: str = "Queued lyrics alignment",
):
    from ._shared import _create_lyrics_alignment_job as _impl

    return _impl(
        song_id=song_id,
        title=title,
        artist=artist,
        task_id=task_id,
        status_message=status_message,
    )


def _update_lyrics_alignment_job(*, song_id: str, status, progress: int, message: str, error: Optional[str] = None):
    from ._shared import _update_lyrics_alignment_job as _impl

    return _impl(song_id=song_id, status=status, progress=progress, message=message, error=error)


def _complete_lyrics_alignment_job(*, song_id: str, status, message: str, error: Optional[str] = None):
    from ._shared import _complete_lyrics_alignment_job as _impl

    return _impl(song_id=song_id, status=status, message=message, error=error)


class _LazyJobRepository:
    """Lazy proxy to avoid importing _shared during module import."""

    def __getattr__(self, name):
        from ._shared import job_repository as _repo

        return getattr(_repo, name)


job_repository = _LazyJobRepository()

__all__ = [
    "AudioProcessingError",
    "_complete_lyrics_alignment_job",
    "_create_lyrics_alignment_job",
    "_get_lyrics_job_id",
    "_make_alignment_cache_key",
    "_update_lyrics_alignment_job",
    "align_song_lyrics",
    "batch_align_lyrics",
    "batch_backfill_artwork",
    "batch_backfill_duration",
    "batch_fingerprint_songs",
    "cleanup_old_jobs",
    "detect_song_chords",
    "detect_song_loudness",
    "detect_song_vocal_range",
    "enrich_song_artist_credits",
    "fetch_song_artwork",
    "fingerprint_single_song",
    "job_repository",
    "post_process_song",
    "process_audio_job",
    "process_youtube_job",
    "separate_with_clean_backing",
    "separate_with_demucs",
    "separate_with_hybrid",
    "separate_with_roformer",
    "separate_with_three_track",
    "separate_with_three_track_duality_v2",
    "separate_with_three_track_mel1143",
    "run_separation_with_fallback",
    "select_and_run_separation_engine",
]

_setup_event_subscriptions()
