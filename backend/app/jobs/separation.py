"""Audio separation helpers shared by Celery tasks."""

import threading
from pathlib import Path
from typing import Callable, Optional

from app.services.gpu_idle_cleanup import begin_gpu_activity, end_gpu_activity
from app.services.separation_engines import (
    separate_with_clean_backing,
    separate_with_demucs,
    separate_with_hybrid,
    separate_with_roformer,
    separate_with_three_track,
)
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


def select_and_run_separation_engine(
    engine_type: str,
    input_path: Path,
    song_dir: Path,
    status_callback: Callable[[str], None],
    stop_event: threading.Event,
    on_vocals_ready: Optional[Callable[[Path], None]] = None,
) -> bool:
    """Select and run the configured source-separation engine."""
    logger.info("Using separation engine: %s", engine_type)

    engine_map = {
        "roformer": separate_with_roformer,
        "hybrid": separate_with_hybrid,
        "clean_backing": separate_with_clean_backing,
        "three_track": separate_with_three_track,
    }

    separator_fn = engine_map.get(engine_type, separate_with_demucs)

    kwargs: dict = {
        "input_path": input_path,
        "song_dir": song_dir,
        "status_callback": status_callback,
        "stop_event": stop_event,
    }

    if engine_type == "three_track" and on_vocals_ready is not None:
        kwargs["on_vocals_ready"] = on_vocals_ready

    return separator_fn(**kwargs)


def run_separation_with_fallback(
    engine_type: str,
    input_path: Path,
    song_dir: Path,
    status_callback: Callable[[str], None],
    stop_event: threading.Event,
    on_vocals_ready: Optional[Callable[[Path], None]] = None,
) -> tuple[bool, str]:
    """Run requested engine and fall back to demucs when three_track fails."""
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
        if success or engine_type != "three_track":
            return success, engine_type

        logger.warning(
            "three_track separation failed for %s; retrying with demucs fallback",
            input_path,
        )
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
