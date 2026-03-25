"""
Strategy 8: Median Aggregation.
"""

import logging
import time
from pathlib import Path

import librosa
import matplotlib.pyplot as plt
import numpy as np

from ..models import StrategyResult

logger = logging.getLogger(__name__)


def experiment_median_aggregation(
    y: np.ndarray, sr: int, output_dir: Path, song_id: str
) -> StrategyResult:
    """
    STRATEGY 8: Median Aggregation

    Take median across frequency bands instead of sum.

    Standard onset detection sums energy across all frequencies.
    Using median may be more robust to outliers and sparse patterns.

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
        logger.info("Strategy 8: Median aggregation across frequency bands...")

        # Compute STFT
        S = np.abs(librosa.stft(y))

        # Divide into frequency bands
        n_bands = 10
        n_freq_bins = S.shape[0]
        band_size = n_freq_bins // n_bands

        band_onsets = []

        logger.info(f"  Computing onset strength for {n_bands} frequency bands...")

        for i in range(n_bands):
            band_start = i * band_size
            band_end = (i + 1) * band_size if i < n_bands - 1 else n_freq_bins

            # Extract this frequency band
            band_mag = S[band_start:band_end, :]

            # Compute onset strength for this band
            band_onset = librosa.onset.onset_strength(S=band_mag, sr=sr)
            band_onsets.append(band_onset)

        # Stack all band onsets
        band_onsets = np.array(band_onsets)

        # Compute median across bands (axis=0)
        median_onset = np.median(band_onsets, axis=0)

        # Also compute traditional sum for comparison
        sum_onset = librosa.onset.onset_strength(y=y, sr=sr)

        # Detect tempo from median onset
        tempo_median = librosa.beat.tempo(onset_envelope=median_onset, sr=sr, aggregate=None)
        candidates_median = (
            [float(t) for t in tempo_median] if tempo_median is not None and len(tempo_median) > 0 else []
        )

        # Detect tempo from sum onset for comparison
        tempo_sum = librosa.beat.tempo(onset_envelope=sum_onset, sr=sr, aggregate=None)
        candidates_sum = (
            [float(t) for t in tempo_sum] if tempo_sum is not None and len(tempo_sum) > 0 else []
        )

        # Create heatmap visualization
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 8))

        # Heatmap of all band onsets
        im1 = ax1.imshow(
            band_onsets, aspect="auto", origin="lower", cmap="viridis", interpolation="nearest"
        )
        ax1.set_ylabel("Frequency Band")
        ax1.set_xlabel("Frame")
        ax1.set_title(f"Onset Strength per Frequency Band ({n_bands} bands)")
        fig.colorbar(im1, ax=ax1)

        # Median onset
        time_frames = np.arange(len(median_onset))
        ax2.plot(time_frames, median_onset, color="red", linewidth=1)
        ax2.set_ylabel("Onset Strength")
        ax2.set_xlabel("Frame")
        ax2.set_title(f"Median Onset (BPMs: {[round(t, 1) for t in candidates_median[:5]]})")
        ax2.grid(True, alpha=0.3)

        # Sum onset (traditional)
        ax3.plot(time_frames[: len(sum_onset)], sum_onset, color="blue", linewidth=1)
        ax3.set_ylabel("Onset Strength")
        ax3.set_xlabel("Frame")
        ax3.set_title(f"Sum Onset - Traditional (BPMs: {[round(t, 1) for t in candidates_sum[:5]]})")
        ax3.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = output_dir / f"median_aggregation_{song_id}.png"
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()

        # Build processing notes
        notes = [
            f"Median aggregation results (across {n_bands} frequency bands):",
            f"  Median-onset candidates: {[round(t, 1) for t in candidates_median[:10]]}",
            f"  Sum-onset candidates: {[round(t, 1) for t in candidates_sum[:10]]}",
            "Median aggregation is more robust to sparse/outlier frequency content.",
        ]

        logger.info(f"  Median aggregation: {[round(t, 1) for t in candidates_median[:5]]}")
        logger.info(f"  Traditional sum: {[round(t, 1) for t in candidates_sum[:5]]}")

        execution_time = time.time() - start_time

        return StrategyResult(
            strategy_name="median_aggregation",
            bpm_candidates=candidates_median,
            execution_time=execution_time,
            processing_notes=notes,
            intermediate_files={"plot": str(plot_path)},
        )

    except Exception as e:
        logger.error(f"Strategy 8 (median aggregation) failed: {e}", exc_info=True)
        execution_time = time.time() - start_time
        return StrategyResult(
            strategy_name="median_aggregation",
            bpm_candidates=[],
            execution_time=execution_time,
            processing_notes=[f"Error: {e}"],
            intermediate_files={},
        )
