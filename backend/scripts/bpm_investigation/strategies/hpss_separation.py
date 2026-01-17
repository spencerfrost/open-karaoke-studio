"""
Strategy 2: Harmonic-Percussive Source Separation.
"""

import logging
import time
from pathlib import Path

import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf

from ..helpers import filter_harmonic_duplicates, select_best_tempo
from ..models import StrategyResult

logger = logging.getLogger(__name__)


def experiment_hpss_separation(
    y: np.ndarray, sr: int, output_dir: Path, song_id: str
) -> StrategyResult:
    """
    Strategy 2: Harmonic-Percussive Source Separation.

    Separates audio into harmonic (tonal) and percussive (rhythmic) components.
    Performs BPM detection primarily on the percussive component which should
    contain cleaner beat information.
    """
    start_time = time.time()
    notes = []

    try:
        # Apply HPSS with margin=8.0 (stronger separation)
        y_harmonic, y_percussive = librosa.effects.hpss(y, margin=8.0)
        notes.append("Applied HPSS with margin=8.0")

        # Save both components
        harmonic_path = output_dir / f"hpss_harmonic_{song_id}.wav"
        percussive_path = output_dir / f"hpss_percussive_{song_id}.wav"

        sf.write(harmonic_path, y_harmonic, sr)
        sf.write(percussive_path, y_percussive, sr)
        notes.append(f"Saved harmonic to {harmonic_path.name}")
        notes.append(f"Saved percussive to {percussive_path.name}")

        # Detect BPM on percussive component (primary)
        tempo_estimates_perc = []
        for prior in [80, 120, 140, 170]:
            tempo, _ = librosa.beat.beat_track(y=y_percussive, sr=sr, start_bpm=prior)
            tempo_estimates_perc.append(float(tempo))

        onset_env_perc = librosa.onset.onset_strength(y=y_percussive, sr=sr)
        tempo_onset_perc = librosa.beat.tempo(
            onset_envelope=onset_env_perc, sr=sr, aggregate=None
        )

        if tempo_onset_perc is not None and len(tempo_onset_perc) > 0:
            tempo_estimates_perc.extend([float(t) for t in tempo_onset_perc[:3]])

        notes.append(f"Percussive raw estimates: {[round(t, 1) for t in tempo_estimates_perc]}")

        # Also detect on harmonic for comparison
        tempo_estimates_harm = []
        for prior in [80, 120, 140, 170]:
            tempo, _ = librosa.beat.beat_track(y=y_harmonic, sr=sr, start_bpm=prior)
            tempo_estimates_harm.append(float(tempo))

        onset_env_harm = librosa.onset.onset_strength(y=y_harmonic, sr=sr)
        tempo_onset_harm = librosa.beat.tempo(
            onset_envelope=onset_env_harm, sr=sr, aggregate=None
        )

        if tempo_onset_harm is not None and len(tempo_onset_harm) > 0:
            tempo_estimates_harm.extend([float(t) for t in tempo_onset_harm[:3]])

        notes.append(f"Harmonic raw estimates: {[round(t, 1) for t in tempo_estimates_harm]}")

        # Use percussive component for final BPM
        filtered_tempos = filter_harmonic_duplicates(tempo_estimates_perc)
        notes.append(f"Filtered (percussive): {[round(t, 1) for t in filtered_tempos]}")

        bpm = select_best_tempo(filtered_tempos)
        bpm_rounded = round(bpm, 1)
        notes.append(f"Final: {bpm_rounded}")

        # Visualization: Spectrograms of both components
        plt.figure(figsize=(12, 6), dpi=300)

        # Harmonic spectrogram
        plt.subplot(2, 1, 1)
        D_harm = librosa.amplitude_to_db(np.abs(librosa.stft(y_harmonic)), ref=np.max)
        librosa.display.specshow(D_harm, sr=sr, x_axis="time", y_axis="hz")
        plt.colorbar(format="%+2.0f dB")
        plt.title(f"Strategy 2: HPSS - Harmonic Component - BPM: {bpm_rounded}")
        plt.ylim(0, 4000)

        # Percussive spectrogram
        plt.subplot(2, 1, 2)
        D_perc = librosa.amplitude_to_db(np.abs(librosa.stft(y_percussive)), ref=np.max)
        librosa.display.specshow(D_perc, sr=sr, x_axis="time", y_axis="hz")
        plt.colorbar(format="%+2.0f dB")
        plt.title(f"Percussive Component - Top 3: {[round(t, 1) for t in tempo_estimates_perc[:3]]}")
        plt.ylim(0, 4000)

        plt.tight_layout()
        plot_path = output_dir / f"hpss_separation_{song_id}.png"
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()

        execution_time = time.time() - start_time

        return StrategyResult(
            strategy_name="hpss_separation",
            bpm_candidates=tempo_estimates_perc,
            execution_time=execution_time,
            processing_notes=notes,
            intermediate_files={
                "harmonic_audio": str(harmonic_path),
                "percussive_audio": str(percussive_path),
                "plot": str(plot_path),
            },
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"HPSS separation strategy failed: {e}", exc_info=True)
        notes.append(f"ERROR: {str(e)}")
        return StrategyResult(
            strategy_name="hpss_separation",
            bpm_candidates=[120.0],
            execution_time=execution_time,
            processing_notes=notes,
        )
