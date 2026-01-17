"""
Strategy 3: Tempogram with Predominant Local Pulse analysis.
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


def experiment_tempogram_plp(
    y: np.ndarray, sr: int, output_dir: Path, song_id: str
) -> StrategyResult:
    """
    Strategy 3: Tempogram with Predominant Local Pulse analysis.

    Uses the Predominant Local Pulse (PLP) method which is more robust to
    tempo variations and complex rhythmic patterns. Analyzes the tempogram
    to find the most consistent pulse across the entire track.
    """
    start_time = time.time()
    notes = []

    try:
        # Compute onset envelope
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        notes.append("Computed onset envelope")

        # Compute tempogram
        tempogram = librosa.feature.tempogram(onset_envelope=onset_env, sr=sr)
        notes.append(f"Computed tempogram: shape={tempogram.shape}")

        # Compute PLP (Predominant Local Pulse)
        plp = librosa.beat.plp(onset_envelope=onset_env, sr=sr)
        notes.append("Computed PLP")

        # Extract tempo from PLP
        tempo_plp = librosa.beat.tempo(onset_envelope=plp, sr=sr, aggregate=None)

        tempo_estimates = []
        if tempo_plp is not None and len(tempo_plp) > 0:
            tempo_estimates.extend([float(t) for t in tempo_plp[:5]])

        notes.append(f"PLP tempo estimates: {[round(t, 1) for t in tempo_estimates]}")

        # Also run standard detection for comparison
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

        # Visualization: Tempogram heatmap with PLP overlay
        plt.figure(figsize=(12, 6), dpi=300)

        # Tempogram
        plt.subplot(2, 1, 1)
        librosa.display.specshow(tempogram, sr=sr, x_axis="time", y_axis="tempo", cmap="magma")
        plt.colorbar(label="Energy")
        plt.title(f"Strategy 3: Tempogram with PLP - BPM: {bpm_rounded}")
        plt.axhline(
            y=bpm_rounded, color="cyan", linestyle="--", linewidth=2, label=f"Selected: {bpm_rounded}"
        )
        plt.legend()

        # PLP signal
        plt.subplot(2, 1, 2)
        times_plp = librosa.times_like(plp, sr=sr)
        plt.plot(times_plp, plp, label="Predominant Local Pulse", color="orange")
        plt.xlabel("Time (s)")
        plt.ylabel("PLP")
        plt.title(f"Top 3 Candidates: {[round(t, 1) for t in tempo_estimates[:3]]}")
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = output_dir / f"tempogram_plp_{song_id}.png"
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()

        execution_time = time.time() - start_time

        return StrategyResult(
            strategy_name="tempogram_plp",
            bpm_candidates=tempo_estimates,
            execution_time=execution_time,
            processing_notes=notes,
            intermediate_files={"plot": str(plot_path)},
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Tempogram PLP strategy failed: {e}", exc_info=True)
        notes.append(f"ERROR: {str(e)}")
        return StrategyResult(
            strategy_name="tempogram_plp",
            bpm_candidates=[120.0],
            execution_time=execution_time,
            processing_notes=notes,
        )
