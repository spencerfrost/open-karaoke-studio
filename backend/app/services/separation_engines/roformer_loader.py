"""
Shared construction for audio-separator ``Separator`` instances.

Every engine that runs an audio-separator model builds it here, so inference
settings (autocast, torch.compile, chunking) and load-failure handling live
in one place.
"""

import gc
import logging

import torch
from audio_separator.separator import Separator

from app.config import get_config

logger = logging.getLogger(__name__)

# One pass per model-sized chunk (8 s for our Roformers), no overlap between
# chunks. audio-separator 0.47 otherwise reads num_overlap from the model YAML
# (4 for ours): 4x the work, no audible gain.
MDXC_PARAMS = {
    "segment_size": 256,
    "override_model_segment_size": False,
    "batch_size": None,
    "overlap": 1,
    "pitch_shift": 0,
}


def load_separator(
    model_filename: str, output_dir: str, output_format: str = "wav"
) -> Separator:
    """
    Build a ``Separator`` and load ``model_filename`` into it.

    Raises:
        torch.cuda.OutOfMemoryError: the model didn't fit on the GPU, so the
            job's OOM retry can handle it.
        RuntimeError: any other model load failure.
    """
    config = get_config()
    separator = Separator(
        output_dir=output_dir,
        output_format=output_format,
        use_autocast=config.SEPARATION_USE_AUTOCAST,
        use_torch_compile=config.SEPARATION_TORCH_COMPILE,
        mdxc_params=MDXC_PARAMS,
    )
    try:
        separator.load_model(model_filename=model_filename)
    except SystemExit as exc:
        # audio-separator turns a RuntimeError during load (CUDA OOM included)
        # into sys.exit(1), which would slip past the engines' handlers.
        cause = exc.__context__
        if (
            isinstance(cause, torch.cuda.OutOfMemoryError)
            or "out of memory" in str(cause).lower()
        ):
            raise torch.cuda.OutOfMemoryError(
                f"Out of memory loading {model_filename}: {cause}"
            ) from cause
        raise RuntimeError(f"Failed to load {model_filename}: {cause}") from cause
    return separator


def release_gpu_memory() -> None:
    """Return cached CUDA memory once the caller has dropped its model references."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
