"""
Strategy 1: Aggressive low-pass filtering to isolate kick/sub-bass.
"""

import logging
import time
from pathlib import Path

import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
from scipy import signal

from ..helpers import filter_harmonic_duplicates, select_best_tempo
from ..models import StrategyResult

logger = logging.getLogger(__name__)


def experiment_lowpass_filter(
    y: np.ndarray, sr: int, output_dir: Path, song_id: str
) -> StrategyResult:
    """
    Strategy 1: Aggressive low-pass filtering to isolate kick/sub-bass.

    Uses a Butterworth filter to remove high-frequency content that can
    confuse beat tracking algorithms. Focuses on the fundamental rhythm
    section (kick drum, bass).
    """
    start_time = time.time()
    notes = []

    try:
        # Apply 4th order Butterworth low-pass filter at 150Hz
        nyquist = sr / 2
        cutoff = 150
        order = 4

        b, a = signal.butter(order, cutoff / nyquist, btype="low")
        y_filtered = signal.filtfilt(b, a, y)

        notes.append(f"Applied Butterworth low-pass filter (order={order}, cutoff={cutoff}Hz)")

        # Save filtered audio
        filtered_path = output_dir / f"lowpass_filtered_{song_id}.wav"
        sf.write(filtered_path, y_filtered, sr)
        notes.append(f"Saved filtered audio to {filtered_path.name}")

        # Detect BPM on filtered signal with multiple priors
        tempo_estimates = []
        for prior in [80, 120, 140, 170]:
            tempo, _ = librosa.beat.beat_track(y=y_filtered, sr=sr, start_bpm=prior)
            tempo_estimates.append(float(tempo))

        # Onset-based detection on filtered signal
        onset_env_filtered = librosa.onset.onset_strength(y=y_filtered, sr=sr)
        tempo_onset = librosa.beat.tempo(
            onset_envelope=onset_env_filtered, sr=sr, aggregate=None
        )

        if tempo_onset is not None and len(tempo_onset) > 0:
            tempo_estimates.extend([float(t) for t in tempo_onset[:3]])

        notes.append(f"Raw estimates: {[round(t, 1) for t in tempo_estimates]}")

        # Filter harmonics and select best
        filtered_tempos = filter_harmonic_duplicates(tempo_estimates)
        notes.append(f"Filtered: {[round(t, 1) for t in filtered_tempos]}")

        bpm = select_best_tempo(filtered_tempos)
        bpm_rounded = round(bpm, 1)
        notes.append(f"Final: {bpm_rounded}")

        # Visualization: Compare original vs filtered onset envelopes
        plt.figure(figsize=(12, 6), dpi=300)

        # Original onset envelope
        onset_env_original = librosa.onset.onset_strength(y=y, sr=sr)
        times_orig = librosa.times_like(onset_env_original, sr=sr)

        plt.subplot(2, 1, 1)
        plt.plot(times_orig, onset_env_original, label="Original Onset", alpha=0.7)
        plt.xlabel("Time (s)")
        plt.ylabel("Onset Strength")
        plt.title(f"Strategy 1: Low-Pass Filter - BPM: {bpm_rounded}")
        plt.legend()
        plt.grid(True, alpha=0.3)

        # Filtered onset envelope
        times_filt = librosa.times_like(onset_env_filtered, sr=sr)
        plt.subplot(2, 1, 2)
        plt.plot(
            times_filt,
            onset_env_filtered,
            label="Filtered Onset (150Hz LP)",
            color="orange",
            alpha=0.7,
        )
        plt.xlabel("Time (s)")
        plt.ylabel("Onset Strength")
        plt.title(f"Top 3 Candidates: {[round(t, 1) for t in tempo_estimates[:3]]}")
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = output_dir / f"lowpass_filter_{song_id}.png"
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()

        execution_time = time.time() - start_time

        return StrategyResult(
            strategy_name="lowpass_filter",
            bpm_candidates=tempo_estimates,
            execution_time=execution_time,
            processing_notes=notes,
            intermediate_files={"filtered_audio": str(filtered_path), "plot": str(plot_path)},
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Low-pass filter strategy failed: {e}", exc_info=True)
        notes.append(f"ERROR: {str(e)}")
        return StrategyResult(
            strategy_name="lowpass_filter",
            bpm_candidates=[120.0],
            execution_time=execution_time,
            processing_notes=notes,
        )
