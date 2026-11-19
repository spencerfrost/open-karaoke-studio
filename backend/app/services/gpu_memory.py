"""Telling a full GPU apart from other failures, and measuring how full it gets.

Separation and lyrics run in separate worker processes that can be on the GPU
at the same time, alongside whatever else shares the card. A full card is a
reason to wait and try again, never a verdict on the song.

torch is imported lazily so the API process can use these without it.
"""

import logging
import os
import sys
import threading
from collections.abc import Generator
from contextlib import contextmanager
from time import perf_counter

from app.services.lyrics_timing import log_lyrics_event

logger = logging.getLogger(__name__)

# How often the card's memory is read while a GPU task runs.
_SAMPLE_INTERVAL_SECONDS = 0.5
# Less free memory than this at the tightest moment is worth a warning.
_LOW_FREE_MIB = 1024


def is_cuda_out_of_memory(exc: BaseException) -> bool:
    """Whether `exc`, or anything it was raised from, is the GPU running out of memory.

    torch raises its own OutOfMemoryError; faster-whisper (CTranslate2), cuDNN
    and cuBLAS raise plain RuntimeErrors that only say so in the message. The
    message has to name CUDA, so the machine's own RAM running out doesn't
    count. Only `raise ... from` is followed: an unrelated error raised while a
    full GPU was being handled is reported as itself.
    """
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        torch = sys.modules.get("torch")
        if torch is not None and isinstance(current, torch.cuda.OutOfMemoryError):
            return True
        message = str(current).lower()
        if "alloc_failed" in message or (
            "out of memory" in message and "cuda" in message
        ):
            return True
        current = current.__cause__
    return False


def free_cached_gpu_memory() -> None:
    """Hand torch's cached blocks back to the card, so a retry starts clean."""
    torch = sys.modules.get("torch")
    if torch is not None and torch.cuda.is_available() and torch.cuda.is_initialized():
        torch.cuda.empty_cache()


def _nvml_device_index() -> int:
    """The card CUDA sees as device 0. NVML ignores CUDA_VISIBLE_DEVICES."""
    visible = os.getenv("CUDA_VISIBLE_DEVICES", "").split(",")[0].strip()
    return int(visible) if visible.isdigit() else 0


class _CardSampler:
    """Reads the whole card's used memory in the background until stopped.

    Uses NVML, which doesn't create a CUDA context, so measuring a task that
    never touches the GPU costs nothing on it. Whole-card numbers include the
    other workers and anything else on the card, which is the point: they show
    how close the card came to full while this task ran.
    """

    def __init__(self) -> None:
        import pynvml

        self._nvml = pynvml
        pynvml.nvmlInit()
        self._handle = pynvml.nvmlDeviceGetHandleByIndex(_nvml_device_index())
        info = pynvml.nvmlDeviceGetMemoryInfo(self._handle)
        self.total = int(info.total)
        self.start_used = int(info.used)
        self.peak_used = int(info.used)
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="gpu-memory-sampler", daemon=True
        )
        self._thread.start()

    def _sample(self) -> None:
        used = int(self._nvml.nvmlDeviceGetMemoryInfo(self._handle).used)
        self.peak_used = max(self.peak_used, used)

    def _run(self) -> None:
        while not self._stop.wait(_SAMPLE_INTERVAL_SECONDS):
            try:
                self._sample()
            except Exception:
                logger.debug("GPU memory sample failed", exc_info=True)
                return

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
        try:
            self._sample()
        except Exception:
            logger.debug("GPU memory sample failed", exc_info=True)
        try:
            self._nvml.nvmlShutdown()
        except Exception:
            logger.debug("NVML shutdown failed", exc_info=True)


def _start_sampler() -> _CardSampler | None:
    try:
        return _CardSampler()
    except Exception:
        # No NVIDIA driver, no card, or no pynvml: nothing to measure.
        logger.debug("GPU memory tracking unavailable", exc_info=True)
        return None


def _torch_cuda_ready():
    """torch, if this process already has a CUDA context; never creates one."""
    torch = sys.modules.get("torch")
    if torch is not None and torch.cuda.is_available() and torch.cuda.is_initialized():
        return torch
    return None


@contextmanager
def track_gpu_memory(label: str, song_id: str | None = None) -> Generator[None]:
    """Log how full the card got while the block ran.

    One line per task: the card's peak use and its tightest free memory, plus
    torch's own peak in this process (CTranslate2 models don't count there, so
    the card number is the one that predicts an out-of-memory error). The same
    numbers go to the lyrics event log as `gpu_memory_peak`, which is kept
    whatever the console's log level.
    """
    sampler = _start_sampler()
    torch = _torch_cuda_ready()
    if torch is not None:
        torch.cuda.reset_peak_memory_stats()
    started_at = perf_counter()
    try:
        yield
    finally:
        if sampler is not None:
            sampler.stop()
            mib = 1024 * 1024
            torch = _torch_cuda_ready()
            torch_peak_mib = (
                torch.cuda.max_memory_reserved() // mib if torch is not None else None
            )
            torch_peak = f"{torch_peak_mib} MiB" if torch is not None else "none"
            tightest_free = (sampler.total - sampler.peak_used) // mib
            elapsed = perf_counter() - started_at
            logger.log(
                logging.WARNING if tightest_free < _LOW_FREE_MIB else logging.INFO,
                "[GPU] %s for song %s: card peaked at %d of %d MiB "
                "(%d MiB at start, %d MiB free at the tightest) over %.1fs; "
                "torch peak in this process %s",
                label,
                song_id,
                sampler.peak_used // mib,
                sampler.total // mib,
                sampler.start_used // mib,
                tightest_free,
                elapsed,
                torch_peak,
            )
            if song_id is not None:
                log_lyrics_event(
                    song_id,
                    "gpu_memory_peak",
                    task=label,
                    card_peak_mib=sampler.peak_used // mib,
                    card_total_mib=sampler.total // mib,
                    card_start_mib=sampler.start_used // mib,
                    tightest_free_mib=tightest_free,
                    torch_peak_mib=torch_peak_mib,
                    elapsed_seconds=round(elapsed, 1),
                )
