"""
Strategy 4: Log-amplitude scaling of onset envelope.
"""

import logging
import time
from pathlib import Path

import librosa
import matplotlib.pyplot as plt
import numpy as np

from ..helpers import filter_harmonic_duplicates, select_best_tempo
from ..models import StrategyResult

logger = logging.getLogger(__name__)


def experiment_log_amplitude(
    y: np.ndarray, sr: int, output_dir: Path, song_id: str
) -> StrategyResult:
    """
    Strategy 4: Log-amplitude scaling of onset envelope.

    Applies logarithmic scaling to the onset envelope to balance the contribution
    of loud and quiet events. This can help reduce the influence of high-frequency
    noise and outlier peaks that may confuse beat tracking.
    """
    start_time = time.time()
    notes = []

    try:
        # Compute onset envelope
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        notes.append("Computed onset envelope")

        # Apply log scaling (convert to dB)
        onset_env_log = librosa.amplitude_to_db(onset_env, ref=np.max)
        # Normalize to 0-1 range for detection
        onset_env_log = (onset_env_log - onset_env_log.min()) / (
            onset_env_log.max() - onset_env_log.min()
        )
        notes.append("Applied log-amplitude scaling (dB)")

        # Detect tempo from log-scaled envelope
        tempo_estimates = []

        # Use log-scaled envelope for tempo detection
        tempo_log = librosa.beat.tempo(onset_envelope=onset_env_log, sr=sr, aggregate=None)
        if tempo_log is not None and len(tempo_log) > 0:
            tempo_estimates.extend([float(t) for t in tempo_log[:5]])

        notes.append(f"Log-scaled tempo estimates: {[round(t, 1) for t in tempo_estimates]}")

        # Also run multi-pass with beat_track
        for prior in [80, 120, 140, 170]:
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr, start_bpm=prior)
            tempo_estimates.append(float(tempo))

        notes.append(f"All raw estimates: {[round(t, 1) for t in tempo_estimates]}")

        # Filter and select
        filtered_tempos = filter_harmonic_duplicates(tempo_estimates)
        notes.append(f"Filtered: {[round(t, 1) for t in filtered_tempos]}")

        bpm = select_best_tempo(filtered_tempos)
        bpm_rounded = round(bpm, 1)
        notes.append(f"Final: {bpm_rounded}")

        # Visualization: Compare linear vs log onset envelopes
        plt.figure(figsize=(12, 6), dpi=300)

        times = librosa.times_like(onset_env, sr=sr)

        # Linear onset envelope
        plt.subplot(2, 1, 1)
        plt.plot(times, onset_env, label="Linear Onset Envelope", color="blue", alpha=0.7)
        plt.xlabel("Time (s)")
        plt.ylabel("Onset Strength")
        plt.title(f"Strategy 4: Log-Amplitude Scaling - BPM: {bpm_rounded}")
        plt.legend()
        plt.grid(True, alpha=0.3)

        # Log-scaled onset envelope
        plt.subplot(2, 1, 2)
        plt.plot(times, onset_env_log, label="Log-Scaled Onset Envelope", color="orange", alpha=0.7)
        plt.xlabel("Time (s)")
        plt.ylabel("Normalized Strength")
        plt.title(f"Top 3 Candidates: {[round(t, 1) for t in tempo_estimates[:3]]}")
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = output_dir / f"log_amplitude_{song_id}.png"
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()

        execution_time = time.time() - start_time

        return StrategyResult(
            strategy_name="log_amplitude",
            bpm_candidates=tempo_estimates,
            execution_time=execution_time,
            processing_notes=notes,
            intermediate_files={"plot": str(plot_path)},
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Log-amplitude strategy failed: {e}", exc_info=True)
        notes.append(f"ERROR: {str(e)}")
        return StrategyResult(
            strategy_name="log_amplitude",
            bpm_candidates=[120.0],
            execution_time=execution_time,
            processing_notes=notes,
        )
