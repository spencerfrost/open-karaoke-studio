import gc
import logging
import os
import threading
import time

import torch

logger = logging.getLogger(__name__)

_DEFAULT_IDLE_SECONDS = 30 * 60
_lock = threading.Lock()
_active_gpu_users = 0
_last_gpu_activity_monotonic = 0.0
_cleanup_generation = 0
_cleanup_timer: threading.Timer | None = None


def get_gpu_idle_cleanup_seconds() -> int:
    """Return the configured idle timeout before VRAM cleanup runs."""
    raw_value = os.getenv("GPU_IDLE_CLEANUP_SECONDS", str(_DEFAULT_IDLE_SECONDS))
    try:
        return max(0, int(raw_value))
    except ValueError:
        logger.warning(
            "Invalid GPU_IDLE_CLEANUP_SECONDS=%r; defaulting to %d seconds",
            raw_value,
            _DEFAULT_IDLE_SECONDS,
        )
        return _DEFAULT_IDLE_SECONDS


def begin_gpu_activity(reason: str) -> None:
    """Mark the start of GPU work and cancel any pending idle cleanup."""
    global _active_gpu_users, _cleanup_timer, _cleanup_generation

    if not torch.cuda.is_available():
        return

    with _lock:
        _active_gpu_users += 1
        _cleanup_generation += 1
        if _cleanup_timer is not None:
            _cleanup_timer.cancel()
            _cleanup_timer = None
        active_count = _active_gpu_users

    logger.debug("GPU activity started (%s); active users=%d", reason, active_count)


def end_gpu_activity(reason: str) -> None:
    """Mark the end of GPU work and schedule idle cleanup if nothing else is active."""
    global _active_gpu_users, _last_gpu_activity_monotonic, _cleanup_timer

    if not torch.cuda.is_available():
        return

    timeout_seconds = get_gpu_idle_cleanup_seconds()
    cleanup_generation = None

    with _lock:
        _active_gpu_users = max(0, _active_gpu_users - 1)
        _last_gpu_activity_monotonic = time.monotonic()

        if _active_gpu_users > 0:
            logger.debug(
                "GPU activity ended (%s); active users remaining=%d",
                reason,
                _active_gpu_users,
            )
            return

        if _cleanup_timer is not None:
            _cleanup_timer.cancel()
            _cleanup_timer = None

        cleanup_generation = _cleanup_generation

        if timeout_seconds <= 0:
            logger.info(
                "GPU activity ended (%s); cleanup timeout disabled, skipping idle cleanup",
                reason,
            )
            return

        _cleanup_timer = threading.Timer(
            timeout_seconds,
            _run_idle_cleanup_if_still_idle,
            args=(cleanup_generation, timeout_seconds),
        )
        _cleanup_timer.daemon = True
        _cleanup_timer.start()

    logger.info(
        "GPU activity ended (%s); scheduled idle VRAM cleanup in %d seconds",
        reason,
        timeout_seconds,
    )


def _run_idle_cleanup_if_still_idle(expected_generation: int, timeout_seconds: int) -> None:
    global _cleanup_timer

    with _lock:
        _cleanup_timer = None
        idle_for = time.monotonic() - _last_gpu_activity_monotonic
        if _active_gpu_users > 0:
            logger.debug("Skipping idle GPU cleanup; active users=%d", _active_gpu_users)
            return
        if expected_generation != _cleanup_generation:
            logger.debug(
                "Skipping idle GPU cleanup; newer GPU activity observed (%d != %d)",
                expected_generation,
                _cleanup_generation,
            )
            return
        if idle_for < timeout_seconds:
            logger.debug(
                "Skipping idle GPU cleanup; idle for %.1fs which is below timeout %ds",
                idle_for,
                timeout_seconds,
            )
            return

    _release_gpu_resources(idle_for)


def _release_gpu_resources(idle_for_seconds: float) -> None:
    if not torch.cuda.is_available():
        return

    reserved_before = torch.cuda.memory_reserved()
    allocated_before = torch.cuda.memory_allocated()

    gc.collect()
    torch.cuda.empty_cache()

    if hasattr(torch.cuda, "ipc_collect"):
        try:
            torch.cuda.ipc_collect()
        except RuntimeError:
            logger.warning("torch.cuda.ipc_collect failed during idle cleanup", exc_info=True)

    reserved_after = torch.cuda.memory_reserved()
    allocated_after = torch.cuda.memory_allocated()

    logger.info(
        "Released idle GPU resources after %.1fs idle; reserved %.1f MiB -> %.1f MiB, allocated %.1f MiB -> %.1f MiB",
        idle_for_seconds,
        reserved_before / (1024 * 1024),
        reserved_after / (1024 * 1024),
        allocated_before / (1024 * 1024),
        allocated_after / (1024 * 1024),
    )