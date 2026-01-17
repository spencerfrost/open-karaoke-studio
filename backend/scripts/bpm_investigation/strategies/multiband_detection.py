"""
Strategy 6: Multi-Band Detection.
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

from ..models import StrategyResult

logger = logging.getLogger(__name__)


def experiment_multiband_detection(
    y: np.ndarray, sr: int, output_dir: Path, song_id: str
) -> StrategyResult:
    """
    STRATEGY 6: Multi-Band Detection

    Split into frequency bands and detect BPM separately.

    Different frequency ranges may have different rhythmic patterns.
    Bass might have kick drums, mids have snares, highs have hi-hats.

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
        logger.info("Strategy 6: Multi-band BPM detection...")

        def bandpass_filter(audio, lowcut, highcut, fs, order=5):
            """Apply bandpass filter using Butterworth filter."""
            nyquist = fs / 2
            low = lowcut / nyquist
            high = highcut / nyquist
            # Ensure frequencies are in valid range
            low = max(0.001, min(low, 0.999))
            high = max(0.001, min(high, 0.999))
            if low >= high:
                high = min(low + 0.01, 0.999)
            b, a = signal.butter(order, [low, high], btype="band")
            return signal.filtfilt(b, a, audio)

        # Define frequency bands
        bands = {"bass": (20, 250), "mid": (250, 4000), "high": (4000, 11025)}

        band_results = {}
        all_candidates = []

        # Process each band
        for band_name, (lowcut, highcut) in bands.items():
            logger.info(f"  Processing {band_name} band ({lowcut}-{highcut} Hz)...")

            # Filter audio
            y_band = bandpass_filter(y, lowcut, highcut, sr)

            # Save band audio
            band_path = output_dir / f"multiband_{band_name}_{song_id}.wav"
            sf.write(band_path, y_band, sr)

            # Detect BPM on this band
            try:
                tempo_band, beats_band = librosa.beat.beat_track(y=y_band, sr=sr)
                tempo_band = float(tempo_band)
            except Exception as e:
                logger.warning(f"    Beat tracking failed for {band_name}: {e}")
                tempo_band = None

            band_results[band_name] = {"bpm": tempo_band, "audio_path": band_path}

            if tempo_band:
                all_candidates.append(tempo_band)
                logger.info(f"    {band_name.capitalize()} band BPM: {round(tempo_band, 1)}")

        # Create 3-panel spectrogram visualization
        fig, axes = plt.subplots(3, 1, figsize=(12, 8))

        for idx, (band_name, (lowcut, highcut)) in enumerate(bands.items()):
            ax = axes[idx]

            # Load band audio
            y_band, _ = sf.read(band_results[band_name]["audio_path"])

            # Compute spectrogram
            D = librosa.amplitude_to_db(np.abs(librosa.stft(y_band)), ref=np.max)
            img = librosa.display.specshow(D, sr=sr, x_axis="time", y_axis="hz", ax=ax)

            # Get BPM for this band
            bpm = band_results[band_name]["bpm"]
            bpm_str = f"{round(bpm, 1)} BPM" if bpm else "N/A"

            ax.set_title(f"{band_name.capitalize()} Band ({lowcut}-{highcut} Hz): {bpm_str}")
            ax.set_ylim(lowcut, highcut)
            fig.colorbar(img, ax=ax, format="%+2.0f dB")

        plt.tight_layout()
        plot_path = output_dir / f"multiband_detection_{song_id}.png"
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()

        # Build processing notes
        notes = ["Multi-band BPM detection results:"]
        for band_name, result in band_results.items():
            bpm = result["bpm"]
            bpm_str = f"{round(bpm, 1)}" if bpm else "N/A"
            notes.append(f"  {band_name.upper()}: {bpm_str} BPM")

        notes.append(f"All candidates: {[round(c, 1) for c in all_candidates]}")

        if len(set([round(c, 1) for c in all_candidates if c])) > 1:
            notes.append("Note: Bands show different BPMs - complex rhythmic structure detected.")
        else:
            notes.append("Note: Bands agree on BPM - consistent rhythm across frequencies.")

        # Add intermediate files
        intermediate_files = {"plot": str(plot_path)}
        for band_name, result in band_results.items():
            intermediate_files[f"{band_name}_audio"] = str(result["audio_path"])

        execution_time = time.time() - start_time

        return StrategyResult(
            strategy_name="multiband_detection",
            bpm_candidates=all_candidates,
            execution_time=execution_time,
            processing_notes=notes,
            intermediate_files=intermediate_files,
        )

    except Exception as e:
        logger.error(f"Strategy 6 (multiband) failed: {e}", exc_info=True)
        execution_time = time.time() - start_time
        return StrategyResult(
            strategy_name="multiband_detection",
            bpm_candidates=[],
            execution_time=execution_time,
            processing_notes=[f"Error: {e}"],
            intermediate_files={},
        )
