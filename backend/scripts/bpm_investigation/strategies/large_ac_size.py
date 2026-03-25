"""
Strategy 7: Large Autocorrelation Window.
"""

import logging
import time
from pathlib import Path

import librosa
import matplotlib.pyplot as plt
import numpy as np

from ..models import StrategyResult

logger = logging.getLogger(__name__)


def experiment_large_ac_size(
    y: np.ndarray, sr: int, output_dir: Path, song_id: str
) -> StrategyResult:
    """
    STRATEGY 7: Large Autocorrelation Window

    Test larger ac_size parameters to capture long-term patterns.

    The autocorrelation window size affects how far back the algorithm looks
    for repeating patterns. Larger windows may catch slower tempos.

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
        logger.info("Strategy 7: Testing large autocorrelation windows...")

        # Compute onset envelope once
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)

        # Test different ac_size values
        ac_sizes = [8, 16, 32, 64]  # 8 is librosa default
        all_candidates = []
        ac_results = {}

        for ac_size in ac_sizes:
            logger.info(f"  Testing ac_size={ac_size}...")

            try:
                tempo = librosa.beat.tempo(
                    onset_envelope=onset_env, sr=sr, aggregate=None, ac_size=ac_size
                )

                if tempo is not None and len(tempo) > 0:
                    candidates = [float(t) for t in tempo]
                    ac_results[ac_size] = candidates[:5]  # Keep top 5
                    all_candidates.extend(candidates)
                    logger.info(f"    ac_size={ac_size}: {[round(t, 1) for t in candidates[:5]]}")
                else:
                    ac_results[ac_size] = []

            except Exception as e:
                logger.warning(f"    ac_size={ac_size} failed: {e}")
                ac_results[ac_size] = []

        # Create visualization: BPM candidates vs ac_size
        fig, ax = plt.subplots(figsize=(12, 6))

        # Plot candidates for each ac_size
        for ac_size, candidates in ac_results.items():
            if candidates:
                x_positions = [ac_size] * len(candidates)
                ax.scatter(x_positions, candidates, s=100, alpha=0.6, label=f"ac_size={ac_size}")

                # Add text labels for top 3 candidates
                for i, bpm in enumerate(candidates[:3]):
                    ax.text(ac_size, bpm, f"{round(bpm, 1)}", fontsize=8, ha="right", va="bottom")

        ax.set_xlabel("Autocorrelation Window Size (ac_size)", fontsize=12)
        ax.set_ylabel("BPM Candidates", fontsize=12)
        ax.set_title("BPM Detection vs Autocorrelation Window Size", fontsize=14)
        ax.set_xticks(ac_sizes)
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.tight_layout()
        plot_path = output_dir / f"large_ac_size_{song_id}.png"
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()

        # Build processing notes
        notes = ["Autocorrelation window size experiments:"]
        for ac_size, candidates in ac_results.items():
            notes.append(f"  ac_size={ac_size}: {[round(c, 1) for c in candidates]}")

        notes.append(f"All candidates: {[round(c, 1) for c in all_candidates[:20]]}")
        notes.append("Larger ac_size values look further back for patterns (better for slow tempos).")

        execution_time = time.time() - start_time

        return StrategyResult(
            strategy_name="large_ac_size",
            bpm_candidates=all_candidates,
            execution_time=execution_time,
            processing_notes=notes,
            intermediate_files={"plot": str(plot_path)},
        )

    except Exception as e:
        logger.error(f"Strategy 7 (large ac_size) failed: {e}", exc_info=True)
        execution_time = time.time() - start_time
        return StrategyResult(
            strategy_name="large_ac_size",
            bpm_candidates=[],
            execution_time=execution_time,
            processing_notes=[f"Error: {e}"],
            intermediate_files={},
        )
