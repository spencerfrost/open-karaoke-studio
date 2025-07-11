import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

import torch
from app.config import get_config
from demucs.api import Separator
from demucs.audio import save_audio

from . import file_management

logger = logging.getLogger(__name__)


class StopProcessingError(Exception):
    """Custom exception raised when processing is stopped by user."""


# --- Helper Functions ---
def select_device_and_log(status_callback: Callable[[str], None]) -> str:
    """Selects CUDA or CPU, logs and reports status, and returns device string."""
    use_cuda = torch.cuda.is_available()
    if use_cuda:
        try:
            device_name = torch.cuda.get_device_name(0)
            status_callback(f"Looking for CUDA: Found GPU: {device_name}")
        except RuntimeError as e:
            status_callback(f"CUDA initialization error: {e}")
            status_callback("Falling back to CPU processing...")
            os.environ["CUDA_VISIBLE_DEVICES"] = ""
            return "cpu"
        return "cuda"
    else:
        status_callback("Looking for CUDA: No GPU detected. Using CPU for processing.")
        return "cpu"


def init_separator(
    model_name: str,
    device: str,
    progress_callback: Callable[[Dict[str, Any]], None],
    status_callback: Callable[[str], None],
) -> Separator:
    """Initializes Demucs Separator with error handling."""
    try:
        separator = Separator(
            model=model_name,
            device=device,
            callback=progress_callback,
        )
        return separator
    except (torch.cuda.CudaError, RuntimeError) as e:
        error_msg = f"Error initializing Demucs: {e}"
        status_callback(error_msg)
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error during Demucs init: {e}"
        status_callback(error_msg)
        raise Exception(error_msg)


def make_progress_callback(
    status_callback: Callable[[str], None], stop_event: Optional[threading.Event]
) -> Callable[[Dict[str, Any]], None]:
    """Returns a Demucs progress callback with stop event and throttling."""
    last_update_time = [0.0]

    def _callback(data):
        if stop_event and stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")
        current_time = time.time()
        if current_time - last_update_time[0] < 0.5 and data["state"] != "end":
            return
        total_segments = data.get("audio_length", 0)
        processed_segments = data.get("segment_offset", 0)
        model_idx = data.get("model_idx_in_bag", 0)
        models_count = data.get("models", 1)
        progress_current_model = (
            (processed_segments / total_segments) if total_segments > 0 else 0
        )
        overall_progress = (
            ((model_idx + progress_current_model) / models_count)
            if models_count > 0
            else 0
        )
        if data["state"] == "end":
            progress_percent = overall_progress * 100
            status_msg = (
                f"Separating: Model {model_idx + 1}/{models_count} "
                f"(Overall {progress_percent:.1f}%)"
            )
            status_callback(status_msg)
            last_update_time[0] = current_time

    return _callback


def calculate_instrumental(
    separated: Dict[str, torch.Tensor],
    status_callback: Callable[[str], None],
    stop_event: Optional[threading.Event],
) -> torch.Tensor:
    """Sums all non-vocal stems to create the instrumental tensor."""
    instr_msg = "Calculating instrumental track..."
    logger.info(instr_msg)
    status_callback(instr_msg)
    instrumental_stems = [s_name for s_name in separated if s_name != "vocals"]
    if not instrumental_stems:
        error_msg = "No non-vocal stems found!"
        status_callback(error_msg)
        raise Exception(error_msg)
    first_stem_name = instrumental_stems[0]
    # Ensure key is a string
    if not isinstance(first_stem_name, str):
        first_stem_name = str(first_stem_name)
    if stop_event and stop_event.is_set():
        raise StopProcessingError("Processing stopped by user")
    instrumental_tensor = torch.zeros_like(separated[first_stem_name])
    for stem_name in instrumental_stems:
        instrumental_tensor += separated[stem_name]
    return instrumental_tensor


def get_output_paths(song_dir: Path, output_extension: str) -> Tuple[Path, Path]:
    """Returns (vocals_path, instrumental_path) with correct extension."""
    vocals_path = file_management.get_vocals_path_stem(song_dir).with_suffix(
        output_extension
    )
    instrumental_path = file_management.get_instrumental_path_stem(
        song_dir
    ).with_suffix(output_extension)
    return vocals_path, instrumental_path


def save_stem(
    tensor: torch.Tensor,
    path: Path,
    output_extension: str,
    separator_samplerate: int,
    status_callback: Callable[[str], None],
    stem_type: str,
    config: Any,
    logger: logging.Logger,
):
    """
    Handles saving a single stem (vocals or instrumental) with logging and error
    handling.
    """
    save_msg = f"Saving {stem_type} ({output_extension.upper().lstrip('.')})..."
    logger.info(save_msg)
    status_callback(save_msg)
    logger.info(f"[AUDIO DEBUG] Attempting to save {stem_type} to: {path}")
    try:
        if output_extension == ".mp3":
            save_audio(
                tensor,
                str(path),
                separator_samplerate,
                int(config.DEFAULT_MP3_BITRATE),
                "rescale",
                16,
                False,
                2,
            )
        elif output_extension == ".wav":
            save_audio(
                tensor, str(path), separator_samplerate, 320, "rescale", 16, False, 2
            )
        else:
            save_audio(tensor, str(path), separator_samplerate)
        logger.info(f"[AUDIO DEBUG] Saved {stem_type} to: {path}")
    except Exception as e:
        logger.error(f"[AUDIO DEBUG] Exception occurred while saving {stem_type}: {e}")
        status_callback(f"** Error saving {stem_type}: {e} **")
        raise


# --- Main Function ---
def separate_audio(input_path: Path, song_dir: Path, status_callback, stop_event=None):
    """
    Separates the audio file into vocals and instrumental tracks,
    matching the input file format and reporting progress.

    Args:
        input_path: Path to the input audio file.
        song_dir: Path to the directory where processed files will be saved.
        status_callback: Function to call with status updates.
        stop_event: A threading.Event to check for stop requests. Can be None.

    Returns:
        True on success, False on failure.

    Raises:
        StopProcessingError: If processing is stopped by the user.
        Exception: For other errors during processing.
    """
    if status_callback is None:
        def default_status_callback(msg):
            logger.info(msg)
        status_callback = default_status_callback
    if stop_event is None:
        stop_event = threading.Event()
    try:
        device = select_device_and_log(status_callback)
        progress_callback = make_progress_callback(status_callback, stop_event)
        config = get_config()
        model_name = config.DEFAULT_MODEL
        separator = init_separator(
            model_name, device, progress_callback, status_callback
        )
        input_extension = input_path.suffix.lower()
        output_extension = (
            input_extension if input_extension in [".wav", ".mp3"] else ".wav"
        )
        output_format_str = "MP3" if output_extension == ".mp3" else "WAV"
        format_msg = f"Input: {input_extension}, Output: {output_format_str}"
        logger.info(format_msg)
        status_callback(format_msg)
        status_callback(f"Loading audio file: {input_path.name}...")
        origin_wave, separated = separator.separate_audio_file(input_path)
        status_callback("Separation models finished.")
        instrumental_tensor = calculate_instrumental(
            separated, status_callback, stop_event
        )
        vocals_path, instrumental_path = get_output_paths(song_dir, output_extension)
        vocals_tensor = separated.get("vocals")
        if vocals_tensor is not None:
            save_stem(
                vocals_tensor,
                vocals_path,
                output_extension,
                separator.samplerate,
                status_callback,
                "vocals",
                config,
                logger,
            )
        else:
            warning_msg = "** Warning: Vocals stem not found in model output. **"
            logger.warning(warning_msg)
            status_callback(warning_msg)
        save_stem(
            instrumental_tensor,
            instrumental_path,
            output_extension,
            separator.samplerate,
            status_callback,
            "instrumental",
            config,
            logger,
        )
        complete_msg = f"Processing complete for {input_path.name}!"
        logger.info(complete_msg)
        status_callback(complete_msg)
        return True
    except StopProcessingError:
        raise
    except Exception as e:
        logger.error(
            f"Error during separation for {input_path.name}: {e}", exc_info=True
        )
        status_callback(f"** Error during separation: {e} **")
        return False
