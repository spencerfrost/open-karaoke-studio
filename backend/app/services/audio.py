import json
import logging
import math
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, NamedTuple, Optional, Tuple

import librosa
import numpy as np
import torch
from demucs.api import Separator
from demucs.audio import save_audio

from app.config import get_config

from . import file_management

logger = logging.getLogger(__name__)


class StopProcessingError(Exception):
    """Custom exception raised when processing is stopped by user."""


# --- Progress Tracking Helper ---
def create_audio_progress_mapper(
    engine_type: str, base_start: int, base_end: int, update_fn
):
    """
    Creates a progress callback that maps engine-specific progress to job progress.

    This function is designed to handle progress updates from audio separation engines
    that report their own progress (like Demucs), and map that progress to the
    appropriate range within the overall job progress.

    Args:
        engine_type: Type of separation engine ('demucs', 'roformer', 'hybrid', 'clean_backing')
        base_start: Starting job progress percentage (e.g., 35)
        base_end: Ending job progress percentage (e.g., 85)
        update_fn: Function to call with (progress, message)

    Returns:
        Callback function for the engine

    Example:
        >>> mapper = create_audio_progress_mapper('demucs', 35, 85, update_progress)
        >>> mapper("Separating: Model 1/2 (Overall 50.0%)")
        # This would call update_progress(60, "Separating: Model 1/2 (Overall 50.0%)")
        # Because 35 + (50 / 100 * 50) = 60
    """
    progress_range = base_end - base_start

    def callback(msg):
        # Try to extract percentage from Demucs-style messages
        # Demucs-style: "Separating: Model 1/2 (Overall 45.3%)" — map to base_start..base_end range
        match = re.search(r"\(Overall (\d+(?:\.\d+)?)\%\)", msg)
        if match:
            engine_progress = float(match.group(1))
            job_progress = int(base_start + (engine_progress / 100.0) * progress_range)
            update_fn(job_progress, msg)
            return

        # three_track stage markers: "Progress: 50% - Step 2/4 ..." — use value directly
        match2 = re.search(r"\bProgress:\s*(\d+(?:\.\d+)?)\s*%", msg, re.IGNORECASE)
        if match2:
            update_fn(int(float(match2.group(1))), msg)

    return callback


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


def detect_vocal_range(
    vocals_path: Path,
    status_callback: Callable[[str], None],
) -> Optional[Tuple[str, str]]:
    """
    Detect the vocal range (lowest and highest note) from a vocals audio file.

    Uses probabilistic YIN (pyin) pitch detection on the isolated vocal track.
    Returns note names in scientific pitch notation (e.g., "G2", "E5").

    Args:
        vocals_path: Path to the vocals audio file (ideally isolated by Demucs)
        status_callback: Function to call with status updates

    Returns:
        Tuple of (low_note, high_note) strings, or None if detection fails
    """
    try:
        status_callback("Detecting vocal range...")
        y, sr = librosa.load(str(vocals_path), sr=22050, mono=True)

        f0, voiced_flag, voiced_probs = librosa.pyin(
            y,
            fmin=librosa.note_to_hz("C2"),  # ~65 Hz, below bass vocal range
            fmax=librosa.note_to_hz("C7"),  # ~2093 Hz, above soprano range
            sr=sr,
        )

        # Filter: only voiced frames with high confidence, no NaN
        mask = voiced_flag & (voiced_probs > 0.75) & ~np.isnan(f0)
        confident_f0 = f0[mask]

        if len(confident_f0) < 10:
            status_callback(
                "Warning: insufficient voiced frames for vocal range detection"
            )
            return None

        midi_notes = librosa.hz_to_midi(confident_f0)
        low_note = librosa.midi_to_note(int(np.percentile(midi_notes, 5)))
        high_note = librosa.midi_to_note(int(np.percentile(midi_notes, 95)))

        status_callback(f"Vocal range detected: {low_note} – {high_note}")
        logger.info("Vocal range: %s – %s", low_note, high_note)
        return low_note, high_note

    except Exception as e:
        logger.error("Vocal range detection failed: %s", e, exc_info=True)
        status_callback(f"Warning: vocal range detection failed: {e}")
        return None


# Loudness is measured on the stems the player plays by default: lead vocal off,
# backing vocals and instrumental at full level.
_LOUDNESS_TARGET_LUFS = -16.0
# Never boost a song so far that its loudest instant passes this level.
_LOUDNESS_PEAK_CEILING_DBTP = -1.0
# Guards against a bad measurement producing an absurd correction.
_LOUDNESS_GAIN_LIMIT_DB = 12.0
# Below this the audio is silence (EBU R128 gates out everything under -70 LUFS).
_LOUDNESS_SILENCE_LUFS = -70.0
_LOUDNESS_FFMPEG_TIMEOUT_SECONDS = 300


class LoudnessResult(NamedTuple):
    loudness_lufs: float
    true_peak_dbtp: float
    gain_db: float


def compute_normalization_gain(loudness_lufs: float, true_peak_dbtp: float) -> float:
    """Gain in dB that brings a song to the loudness target without pushing its peak past the ceiling."""
    gain = _LOUDNESS_TARGET_LUFS - loudness_lufs
    gain = min(gain, _LOUDNESS_PEAK_CEILING_DBTP - true_peak_dbtp)
    return max(-_LOUDNESS_GAIN_LIMIT_DB, min(_LOUDNESS_GAIN_LIMIT_DB, gain))


def parse_loudnorm_output(stderr: str) -> Optional[Tuple[float, float]]:
    """
    Read integrated loudness and true peak from ffmpeg's loudnorm JSON summary.

    Returns (loudness_lufs, true_peak_dbtp), or None when the audio is silent.
    Raises ValueError when the output has no readable summary.
    """
    start = stderr.rfind("{")
    end = stderr.rfind("}")
    if start == -1 or end < start:
        raise ValueError("ffmpeg loudnorm output has no JSON summary")
    summary = json.loads(stderr[start : end + 1])
    loudness_lufs = float(summary["input_i"])
    true_peak_dbtp = float(summary["input_tp"])
    if not math.isfinite(loudness_lufs) or loudness_lufs < _LOUDNESS_SILENCE_LUFS:
        return None
    if not math.isfinite(true_peak_dbtp):
        return None
    return loudness_lufs, true_peak_dbtp


def _loudnorm_command(stem_paths: list[Path]) -> list[str]:
    command = ["ffmpeg", "-hide_banner", "-nostats"]
    for path in stem_paths:
        command += ["-i", str(path)]
    analysis = "loudnorm=print_format=json"
    if len(stem_paths) == 1:
        command += ["-af", analysis]
    else:
        # normalize=0 sums the stems at full level, as the player does. amix's
        # default scales each input down, which would read about 6 dB low.
        command += [
            "-filter_complex",
            f"amix=inputs={len(stem_paths)}:normalize=0,{analysis}",
        ]
    return command + ["-f", "null", "-"]


def detect_loudness(song_dir: Path) -> Optional[LoudnessResult]:
    """
    Measure how loud a song plays by default and compute its normalization gain.

    Measures instrumental.mp3, summed with backing_vocals.mp3 when the song has
    one, using EBU R128 integrated loudness and true peak.

    Returns None when the audio is silent.
    Raises FileNotFoundError when there is no instrumental stem, and
    RuntimeError or ValueError when ffmpeg fails or its output can't be read.
    """
    instrumental_path = song_dir / "instrumental.mp3"
    backing_path = song_dir / "backing_vocals.mp3"
    if not instrumental_path.exists():
        raise FileNotFoundError(instrumental_path)
    stem_paths = [instrumental_path]
    if backing_path.exists():
        stem_paths.append(backing_path)

    completed = subprocess.run(
        _loudnorm_command(stem_paths),
        capture_output=True,
        text=True,
        timeout=_LOUDNESS_FFMPEG_TIMEOUT_SECONDS,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"ffmpeg loudnorm failed ({completed.returncode}): {completed.stderr[-500:]}"
        )

    measured = parse_loudnorm_output(completed.stderr)
    if measured is None:
        return None
    loudness_lufs, true_peak_dbtp = measured
    gain_db = compute_normalization_gain(loudness_lufs, true_peak_dbtp)
    logger.info(
        "Loudness: %.1f LUFS, true peak %.1f dBTP, gain %+.1f dB (%d stem(s))",
        loudness_lufs,
        true_peak_dbtp,
        gain_db,
        len(stem_paths),
    )
    return LoudnessResult(loudness_lufs, true_peak_dbtp, gain_db)


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
    logger.debug("Attempting to save %s to: %s", stem_type, path)
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
        logger.debug("Saved %s to: %s", stem_type, path)
    except Exception as e:
        logger.error("Exception occurred while saving %s: %s", stem_type, e)
        status_callback(f"** Error saving {stem_type}: {e} **")
        raise


# =============================================================================
# SHARED AUDIO ANALYSIS HELPERS
# =============================================================================

_DEFAULT_SR = 22050
_DEFAULT_HOP_LENGTH = 512


def load_vocals(path: Path) -> Tuple[np.ndarray, int]:
    """Load a vocals audio file with standard project parameters.

    Args:
        path: Path to the vocals audio file (mp3 or wav).

    Returns:
        Tuple of (audio_array, sample_rate) with sr=22050, mono=True.
    """
    y, sr = librosa.load(str(path), sr=_DEFAULT_SR, mono=True)
    return y, sr


def compute_rms_curve(
    y: np.ndarray,
    sr: int,
    hop_length: int = _DEFAULT_HOP_LENGTH,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute a per-frame RMS energy curve for an audio signal.

    Args:
        y: Audio time-series array.
        sr: Sample rate.
        hop_length: Hop size in samples between successive frames.

    Returns:
        Tuple of (rms_values, rms_times) — both 1-D arrays with the same length.
        rms_values: RMS energy per frame (float32).
        rms_times: Centre time in seconds for each frame (float64).
    """
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
    return rms, times


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
        bool: True if separation succeeded, False otherwise.

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
    except (StopProcessingError, torch.cuda.OutOfMemoryError):
        # Cancellation and a full GPU are the job's to handle (cancel / retry later).
        raise
    except Exception as e:
        logger.error(
            f"Error during separation for {input_path.name}: {e}", exc_info=True
        )
        status_callback(f"** Error during separation: {e} **")
        return False
