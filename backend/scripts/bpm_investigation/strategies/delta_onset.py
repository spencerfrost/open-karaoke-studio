"""
Strategy 5: Delta-Onset Features.
"""

import logging
import time
from pathlib import Path

import librosa
import matplotlib.pyplot as plt
import numpy as np

from ..models import StrategyResult

logger = logging.getLogger(__name__)


def experiment_delta_onset(
    y: np.ndarray, sr: int, output_dir: Path, song_id: str
) -> StrategyResult:
    """
    STRATEGY 5: Delta-Onset Features

    First derivative of onset envelope to emphasize sharp starts.

    The idea is that sudden increases in onset strength may better capture drum hits
    compared to the raw onset envelope which includes sustained energy.

    Args:
        y: Audio time series
        sr: Sample rate
        output_dir: Directory to save intermediate files
        song_id: Identifier for this song (used in filenames)

    Returns:
        StrategyResult with all candidates and visualizations
    """
    start_time = time.time()

    try:
        logger.info("Strategy 5: Computing delta-onset features...")

        # Compute onset envelope
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)

        # Compute first derivative (emphasizes sudden increases)
        delta_onset = np.diff(onset_env, prepend=onset_env[0])

        # Keep only increases (positive derivatives)
        delta_onset = np.maximum(0, delta_onset)

        # Detect tempo from delta onset
        tempo_delta = librosa.beat.tempo(onset_envelope=delta_onset, sr=sr, aggregate=None)
        candidates = (
            [float(t) for t in tempo_delta] if tempo_delta is not None and len(tempo_delta) > 0 else []
        )

        # Also get tempo from original onset for comparison
        tempo_original = librosa.beat.tempo(onset_envelope=onset_env, sr=sr, aggregate=None)
        candidates_original = (
            [float(t) for t in tempo_original]
            if tempo_original is not None and len(tempo_original) > 0
            else []
        )

        # Create comparison plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

        time_frames = np.arange(len(onset_env))

        ax1.plot(time_frames, onset_env, color="blue", linewidth=1)
        ax1.set_ylabel("Onset Strength")
        ax1.set_title(f"Original Onset Envelope (BPMs: {[round(t, 1) for t in candidates_original[:5]]})")
        ax1.grid(True, alpha=0.3)

        ax2.plot(time_frames, delta_onset, color="red", linewidth=1)
        ax2.set_ylabel("Delta Onset (1st derivative)")
        ax2.set_xlabel("Frame")
        ax2.set_title(f"Delta-Onset Envelope (BPMs: {[round(t, 1) for t in candidates[:5]]})")
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = output_dir / f"delta_onset_{song_id}.png"
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()

        # Build processing notes
        notes = [
            f"Delta-onset candidates: {[round(t, 1) for t in candidates[:10]]}",
            f"Original onset candidates: {[round(t, 1) for t in candidates_original[:10]]}",
            "Strategy emphasizes sudden increases in onset strength (drum hits).",
        ]

        logger.info(f"  Delta-onset detected: {[round(t, 1) for t in candidates[:5]]}")

        execution_time = time.time() - start_time

        return StrategyResult(
            strategy_name="delta_onset",
            bpm_candidates=candidates,
            execution_time=execution_time,
            processing_notes=notes,
            intermediate_files={"plot": str(plot_path)},
        )

    except Exception as e:
        logger.error(f"Strategy 5 (delta-onset) failed: {e}", exc_info=True)
        execution_time = time.time() - start_time
        return StrategyResult(
            strategy_name="delta_onset",
            bpm_candidates=[],
            execution_time=execution_time,
            processing_notes=[f"Error: {e}"],
            intermediate_files={},
        )
