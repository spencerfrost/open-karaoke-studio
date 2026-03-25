"""
Baseline strategy: Current production implementation.
"""

import logging
import time
from pathlib import Path

import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np

from ..helpers import filter_harmonic_duplicates, select_best_tempo
from ..models import StrategyResult

logger = logging.getLogger(__name__)


def baseline_current_implementation(
    y: np.ndarray, sr: int, output_dir: Path, song_id: str
) -> StrategyResult:
    """
    Exact replication of current audio.py detect_bpm logic.

    This is the baseline strategy against which all others are compared.
    Replicates the multi-pass detection with onset-based candidates and
    harmonic filtering used in production.
    """
    start_time = time.time()
    notes = []

    try:
        # Strategy 1: Multi-pass tempo detection with different prior estimates
        tempo_estimates = []

        # Pass with common tempo priors to reduce bias
        for prior in [80, 120, 140, 170]:
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr, start_bpm=prior)
            tempo_estimates.append(float(tempo))

        # Strategy 2: Use onset-based tempo detection for additional robustness
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo_onset = librosa.beat.tempo(onset_envelope=onset_env, sr=sr, aggregate=None)

        if tempo_onset is not None and len(tempo_onset) > 0:
            # Add top 3 tempo estimates from onset detection
            tempo_estimates.extend([float(t) for t in tempo_onset[:3]])

        notes.append(f"Raw estimates: {[round(t, 1) for t in tempo_estimates]}")
        logger.info(f"Raw tempo estimates: {tempo_estimates}")

        # Filter out harmonic multiples/divisors
        filtered_tempos = filter_harmonic_duplicates(tempo_estimates)
        notes.append(f"Filtered: {[round(t, 1) for t in filtered_tempos]}")
        logger.info(f"Filtered tempo estimates (harmonics removed): {filtered_tempos}")

        # Choose best tempo from filtered estimates
        bpm = select_best_tempo(filtered_tempos)
        bpm_rounded = round(bpm, 1)
        notes.append(f"Final: {bpm_rounded}")

        # Generate visualization: onset envelope with detected beats
        plt.figure(figsize=(12, 6), dpi=300)

        # Plot onset envelope
        times = librosa.times_like(onset_env, sr=sr)
        plt.subplot(2, 1, 1)
        plt.plot(times, onset_env, label="Onset Strength")
        plt.xlabel("Time (s)")
        plt.ylabel("Onset Strength")
        plt.title(f"Baseline: Current Implementation - BPM: {bpm_rounded}")
        plt.legend()
        plt.grid(True, alpha=0.3)

        # Plot beat tracking for the final selected BPM
        plt.subplot(2, 1, 2)
        tempo_final, beats_final = librosa.beat.beat_track(y=y, sr=sr, start_bpm=bpm_rounded)
        beat_times = librosa.frames_to_time(beats_final, sr=sr)
        plt.vlines(beat_times, 0, 1, color="r", alpha=0.6, linestyle="--", label="Detected Beats")
        plt.xlabel("Time (s)")
        plt.ylabel("Beat Markers")
        plt.title(f"Top 3 Candidates: {[round(t, 1) for t in tempo_estimates[:3]]}")
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = output_dir / f"baseline_{song_id}.png"
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()

        execution_time = time.time() - start_time

        return StrategyResult(
            strategy_name="baseline",
            bpm_candidates=tempo_estimates,
            execution_time=execution_time,
            processing_notes=notes,
            intermediate_files={"plot": str(plot_path)},
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Baseline strategy failed: {e}", exc_info=True)
        notes.append(f"ERROR: {str(e)}")
        return StrategyResult(
            strategy_name="baseline",
            bpm_candidates=[120.0],
            execution_time=execution_time,
            processing_notes=notes,
        )
