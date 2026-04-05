import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

import librosa
import numpy as np
import torch
from app.config import get_config
from demucs.api import Separator
from demucs.audio import save_audio
from pydub import AudioSegment

from . import file_management

logger = logging.getLogger(__name__)


class StopProcessingError(Exception):
    """Custom exception raised when processing is stopped by user."""


# --- Progress Tracking Helper ---
def create_audio_progress_mapper(engine_type: str, base_start: int, base_end: int, update_fn):
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
        match = re.search(r'\(Overall (\d+(?:\.\d+)?)\%\)', msg)
        if match:
            engine_progress = float(match.group(1))
            job_progress = int(base_start + (engine_progress / 100.0) * progress_range)
            update_fn(job_progress, msg)
            return

        # three_track stage markers: "Progress: 50% - Step 2/4 ..." — use value directly
        match2 = re.search(r'\bProgress:\s*(\d+(?:\.\d+)?)\s*%', msg, re.IGNORECASE)
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


def _filter_harmonic_duplicates(tempos: list[float]) -> list[float]:
    """
    Filter out harmonic multiples/divisors (2x, 1/2, 3/2, 2/3, 4/3, 3/4).
    Groups tempos that are harmonically related and keeps representative values.

    Args:
        tempos: List of tempo estimates

    Returns:
        List of filtered tempos with harmonics removed
    """
    if not tempos:
        return []

    # Common harmonic ratios to check
    harmonic_ratios = [0.5, 2.0, 0.667, 1.5, 0.75, 1.333]
    tolerance = 0.05  # 5% tolerance for matching

    clusters = []
    for tempo in tempos:
        # Find if this tempo belongs to existing cluster
        matched = False
        for cluster in clusters:
            for existing_tempo in cluster:
                # Check if harmonically related
                ratio = tempo / existing_tempo
                if any(abs(ratio - hr) < tolerance for hr in harmonic_ratios) or abs(ratio - 1.0) < tolerance:
                    cluster.append(tempo)
                    matched = True
                    break
            if matched:
                break

        if not matched:
            clusters.append([tempo])

    # Return the tempo from each cluster (prefer values in 80-180 range)
    filtered = []
    for cluster in clusters:
        # Prefer tempos in typical range
        in_range = [t for t in cluster if 80 <= t <= 180]
        if in_range:
            filtered.append(sum(in_range) / len(in_range))
        else:
            filtered.append(sum(cluster) / len(cluster))

    return filtered


def _select_best_tempo(tempos: list[float]) -> float:
    """
    Select the most likely tempo from filtered estimates using median.

    Args:
        tempos: List of tempo estimates

    Returns:
        The selected BPM value
    """
    if not tempos:
        return 120.0  # Fallback

    # Use median for robustness against outliers
    tempos_sorted = sorted(tempos)
    n = len(tempos_sorted)
    if n % 2 == 0:
        return (tempos_sorted[n // 2 - 1] + tempos_sorted[n // 2]) / 2
    else:
        return tempos_sorted[n // 2]


def detect_bpm(
    audio_path: Path,
    status_callback: Callable[[str], None],
    instrumental_path: Optional[Path] = None
) -> Optional[float]:
    """
    Detect the BPM (beats per minute) of an audio file using improved multi-pass
    detection with harmonic filtering.

    Args:
        audio_path: Path to the audio file
        status_callback: Function to call with status updates
        instrumental_path: Optional path to instrumental track (preferred for cleaner detection)

    Returns:
        Detected BPM as float, or None if detection fails
    """
    try:
        status_callback("Detecting BPM (improved algorithm)...")

        # Prefer instrumental track for cleaner beat detection
        analysis_path = instrumental_path if instrumental_path and instrumental_path.exists() else audio_path
        logger.info(f"BPM detection using: {analysis_path} ({'instrumental' if analysis_path == instrumental_path else 'original'})")

        # Load audio with reduced sample rate for faster processing (limit to 90 seconds)
        y, sr = librosa.load(str(analysis_path), sr=22050, duration=90)

        # Strategy 1: Multi-pass tempo detection with different prior estimates
        tempo_estimates = []

        # Pass with common tempo priors to reduce bias
        for prior in [80, 120, 140, 170]:
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr, start_bpm=prior)
            tempo_estimates.append(float(tempo))

        # Strategy 2: Use onset-based tempo detection for additional robustness
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo_onset = librosa.beat.tempo(onset_envelope=onset_env, sr=sr, aggregate=None)

        if tempo_onset is not None and len(tempo_onset) > 0:
            # Add top 3 tempo estimates from onset detection
            tempo_estimates.extend([float(t) for t in tempo_onset[:3]])

        logger.info(f"Raw tempo estimates: {tempo_estimates}")

        # Filter out harmonic multiples/divisors
        filtered_tempos = _filter_harmonic_duplicates(tempo_estimates)
        logger.info(f"Filtered tempo estimates (harmonics removed): {filtered_tempos}")

        # Choose best tempo from filtered estimates
        bpm = _select_best_tempo(filtered_tempos)
        bpm_rounded = round(bpm, 1)

        status_callback(f"BPM detected: {bpm_rounded}")
        logger.info(
            f"BPM detection complete: {bpm_rounded} BPM "
            f"(from {len(tempo_estimates)} estimates, {len(filtered_tempos)} after filtering)"
        )

        return bpm_rounded

    except Exception as e:
        error_msg = f"BPM detection failed: {e}"
        logger.error(error_msg, exc_info=True)
        status_callback(f"Warning: {error_msg}")
        return None


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
            status_callback("Warning: insufficient voiced frames for vocal range detection")
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


_LOUDNESS_TARGET_DBFS = -14.0
_LOUDNESS_GAIN_MAX_DB = 12.0


def detect_loudness(
    audio_path: Path,
    status_callback: Callable[[str], None],
) -> Optional[Tuple[float, float]]:
    """
    Measure the RMS loudness of an audio file and compute a normalization gain.

    Args:
        audio_path: Path to the audio file (MP3 or WAV)
        status_callback: Function to call with status updates

    Returns:
        Tuple of (loudness_dbfs, gain_db) or None if detection fails.
        loudness_dbfs: RMS loudness relative to full scale (e.g. -20.0)
        gain_db: dB gain needed to reach -14 dBFS target, clamped to ±12 dB
    """
    try:
        status_callback("Detecting loudness...")
        audio = AudioSegment.from_file(str(audio_path))
        loudness_dbfs = audio.dBFS
        if loudness_dbfs == float("-inf"):
            # Silent file — skip normalization
            status_callback("Warning: Silent audio file, skipping loudness detection")
            return None
        raw_gain = _LOUDNESS_TARGET_DBFS - loudness_dbfs
        gain_db = max(-_LOUDNESS_GAIN_MAX_DB, min(_LOUDNESS_GAIN_MAX_DB, raw_gain))
        status_callback(f"Loudness detected: {loudness_dbfs:.1f} dBFS (gain: {gain_db:+.1f} dB)")
        logger.info(
            "Loudness detection complete: %.1f dBFS, gain correction: %+.1f dB",
            loudness_dbfs,
            gain_db,
        )
        return loudness_dbfs, gain_db
    except Exception as e:
        error_msg = f"Loudness detection failed: {e}"
        logger.error(error_msg, exc_info=True)
        status_callback(f"Warning: {error_msg}")
        return None


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
        Tuple of (success: bool, bpm: Optional[float])

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

        # Start BPM detection in background — runs while stems are saved
        _bpm_log = lambda msg: logger.debug("BPM: %s", msg)
        bpm_executor = ThreadPoolExecutor(max_workers=1)
        bpm_future = bpm_executor.submit(detect_bpm, input_path, _bpm_log)
        logger.info("BPM detection started in background thread")

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

        # Collect BPM result (started before stem saves, should already be done)
        try:
            detected_bpm = bpm_future.result(timeout=30)
            logger.info("BPM detection complete: %s BPM", detected_bpm)
        except Exception as e:
            logger.warning("BPM detection failed or timed out: %s", e)
            detected_bpm = None
        finally:
            bpm_executor.shutdown(wait=False)
        complete_msg = f"Processing complete for {input_path.name}!"
        logger.info(complete_msg)
        status_callback(complete_msg)
        return True, detected_bpm
    except StopProcessingError:
        raise
    except Exception as e:
        logger.error(
            f"Error during separation for {input_path.name}: {e}", exc_info=True
        )
        status_callback(f"** Error during separation: {e} **")
        return False, None
