"""The LRC offset sweep job's per-song work: sweep and store, or apply.

See app/services/lrc_offset_layer.py for what's stored and why. Both run
inside the batch task (batch_sweep_lrc_offsets) one song at a time, on the
lead + backing mix the aligner hears.
"""

import json
import time
from typing import Any, Callable, Optional, TypeVar

from celery.utils.log import get_task_logger

from app.services.lrc_offset_layer import (
    SWEEP_FINE_REACH_SECONDS,
    SWEEP_FINE_STEP_SECONDS,
    SWEEP_MAX_SECONDS,
    SWEEP_STEP_SECONDS,
    is_current,
    lrc_md5,
    read_layer,
)
from app.services.processing_versions import LRC_OFFSET_VERSION, WORD_TIMING_VERSION
from app.utils.clock import utc_now

logger = get_task_logger(__name__)

# A full GPU (a song being separated, say) isn't the song's fault: wait and try
# again a few times before counting it failed.
GPU_FULL_RETRIES = 3
GPU_FULL_WAIT_SECONDS = 60

T = TypeVar("T")


def _song_inputs(song_id: str) -> Optional[dict[str, Any]]:
    from app.db.database import get_db_session
    from app.db.models import DbSong

    with get_db_session() as session:
        song = session.get(DbSong, song_id)
        if song is None or not song.synced_lyrics:
            return None
        return {
            "lrc": song.synced_lyrics,
            "language": song.language or "en",
            "pending_shift": song.lrc_offset_pending_shift,
            "version": song.lrc_offset_version,
            "md5": song.lrc_offset_lrc_md5,
        }


def _vocals(song_id: str):
    from app.services.file_service import FileService

    path = FileService().get_vocals_path(song_id, ".mp3")
    return path if path.exists() else None


def _retrying_full_gpu(song_id: str, work: Callable[[], T]) -> T:
    from app.services.gpu_idle_cleanup import release_gpu_memory_now
    from app.services.gpu_memory import is_cuda_out_of_memory

    for attempt in range(GPU_FULL_RETRIES + 1):
        try:
            return work()
        except Exception as exc:
            if not is_cuda_out_of_memory(exc) or attempt == GPU_FULL_RETRIES:
                raise
            logger.warning(
                "LRC offset sweep: GPU full on song %s; trying again in %ds",
                song_id,
                GPU_FULL_WAIT_SECONDS,
            )
            release_gpu_memory_now("GPU full during the LRC offset sweep")
            time.sleep(GPU_FULL_WAIT_SECONDS)
    raise AssertionError("unreachable")


def _write_layer(
    song_id: str,
    measured_md5: str,
    layer: dict[str, Any],
    pending_shift: Optional[float],
) -> bool:
    """Store the layer, unless the lyrics changed while the song was swept."""
    from app.db.database import get_db_session
    from app.db.models import DbSong

    with get_db_session() as session:
        song = session.get(DbSong, song_id)
        if song is None or lrc_md5(song.synced_lyrics) != measured_md5:
            return False
        old = read_layer(song) or {}
        if old.get("answers") and old.get("shift") == layer.get("shift"):
            layer["answers"] = old["answers"]  # same shift heard: keep what was said
        song.lrc_offset_sweep = json.dumps(layer)
        song.lrc_offset_version = LRC_OFFSET_VERSION
        song.lrc_offset_lrc_md5 = measured_md5
        song.lrc_offset_pending_shift = pending_shift
        session.commit()
    return True


def sweep_and_store(song_id: str) -> str:
    """Sweep one song's LRC and store the layer. Changes nothing the TV shows.

    Returns "shift" (a shift passed the gate and waits for Apply shifts),
    "no_shift", "no_lyrics", "no_audio", "changed" (the lyrics changed while
    it ran; swept again next time) or "error".
    """
    from app.jobs.lyrics_tasks import MIN_ALIGNMENT_SCORE, _offset_rejection_reason
    from app.services.lyrics_alignment import align_lyrics_to_vocals
    from app.services.lyrics_offset import shift_lrc_timestamps, sweep_lrc_offset

    inputs = _song_inputs(song_id)
    if inputs is None:
        return "no_lyrics"
    vocals = _vocals(song_id)
    if vocals is None:
        return "no_audio"
    lrc, language = inputs["lrc"], inputs["language"]
    measured_md5 = lrc_md5(lrc)
    assert measured_md5 is not None
    started = time.perf_counter()

    sweep = _retrying_full_gpu(
        song_id,
        lambda: sweep_lrc_offset(
            lrc,
            vocals,
            language=language,
            max_shift=SWEEP_MAX_SECONDS,
            step=SWEEP_STEP_SECONDS,
            fine_step=SWEEP_FINE_STEP_SECONDS,
            fine_reach=SWEEP_FINE_REACH_SECONDS,
            fine_around_zero=False,
        ),
    )
    base = {
        "version": LRC_OFFSET_VERSION,
        "measured_at": utc_now().isoformat() + "Z",
        "max_shift": SWEEP_MAX_SECONDS,
        "step": SWEEP_STEP_SECONDS,
        "fine_step": SWEEP_FINE_STEP_SECONDS,
    }
    if sweep is None:
        # Stored, so "missing" doesn't retry it every run; "all" tries again.
        _write_layer(song_id, measured_md5, {**base, "failed": True}, None)
        return "error"

    rejection = _offset_rejection_reason(sweep)
    layer: dict[str, Any] = {
        **base,
        "shift": sweep["shift"],
        "score": float(sweep["score"]),
        "baseline_score": float(sweep["baseline_score"]),
        "gain": float(sweep["gain"]),
        "scores": {str(k): float(v) for k, v in sorted(sweep["scores"].items())},
        "passes": rejection is None,
        "rejection": rejection,
        "seconds": round(time.perf_counter() - started, 1),
    }
    pending_shift = None
    if rejection is None:
        # The words at the shift, for Compare word timing. Shifting moves only
        # timestamps, so the lines match today's timing line for line.
        shifted = _retrying_full_gpu(
            song_id,
            lambda: align_lyrics_to_vocals(
                shift_lrc_timestamps(lrc, sweep["shift"]),
                vocals,
                language=language,
                alignment_mode="offset_corrected",
            ),
        )
        if shifted and shifted["mean_score"] >= MIN_ALIGNMENT_SCORE:
            layer["shifted"] = {
                "words": shifted["words"],
                "mean_score": shifted["mean_score"],
            }
            pending_shift = sweep["shift"]
        else:
            layer["passes"] = False
            layer["rejection"] = "realign_failed"

    if not _write_layer(song_id, measured_md5, layer, pending_shift):
        return "changed"
    logger.info(
        "LRC offset sweep, song %s: best %+.1fs gain %+.3f (%s)",
        song_id,
        sweep["shift"],
        sweep["gain"],
        "waits to be applied" if pending_shift is not None else rejection or "no shift",
    )
    return "shift" if pending_shift is not None else "no_shift"


def apply_pending_shift(song_id: str) -> str:
    """Shift the song's LRC by its waiting shift and re-align it, as the
    pipeline stores an offset correction.

    Returns "applied", "stale" (no current sweep with a shift waiting),
    "no_audio" or "rejected" (the shifted LRC didn't align well enough).
    """
    from app.db.database import get_db_session
    from app.db.models import DbSong
    from app.jobs.lyrics_tasks import store_offset_corrected_lrc

    inputs = _song_inputs(song_id)
    if inputs is None or inputs["pending_shift"] is None:
        return "stale"
    if not is_current(lrc_md5(inputs["lrc"]), inputs["version"], inputs["md5"]):
        return "stale"
    vocals = _vocals(song_id)
    if vocals is None:
        return "no_audio"
    shift = inputs["pending_shift"]

    result = _retrying_full_gpu(
        song_id,
        lambda: store_offset_corrected_lrc(
            song_id,
            content=inputs["lrc"],
            shift=shift,
            vocals_path=vocals,
            language=inputs["language"],
            source="db:synced",
            attempt_index=1,
        ),
    )
    if result is None:
        return "rejected"

    with get_db_session() as session:
        song = session.get(DbSong, song_id)
        if song is not None:
            layer = read_layer(song) or {}
            layer.pop("shifted", None)
            layer["applied_at"] = utc_now().isoformat() + "Z"
            layer["applied_shift"] = shift
            song.lrc_offset_sweep = json.dumps(layer)
            # The layer now describes the shifted LRC, so it isn't swept again.
            song.lrc_offset_lrc_md5 = lrc_md5(song.synced_lyrics)
            song.lrc_offset_pending_shift = None
            song.word_timing_version = WORD_TIMING_VERSION
            session.commit()
    logger.info("LRC offset sweep: applied %+.1fs to song %s", shift, song_id)
    return "applied"
