import logging
from pathlib import Path

import librosa
import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

MAJOR_TEMPLATE = np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0], dtype=float)
MINOR_TEMPLATE = np.array([1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0], dtype=float)


def _build_chord_templates() -> tuple[list[str], NDArray]:
    """Build 24 chord templates (12 major + 12 minor) and their names."""
    names: list[str] = []
    templates: list[NDArray] = []

    for semitone, note in enumerate(NOTE_NAMES):
        names.append(note)
        templates.append(np.roll(MAJOR_TEMPLATE, semitone))

        names.append(f"{note}m")
        templates.append(np.roll(MINOR_TEMPLATE, semitone))

    return names, np.array(templates)


def _cosine_similarity(vector: NDArray, matrix: NDArray) -> NDArray:
    """Compute cosine similarity between a vector and each row of a matrix."""
    dot_products = matrix @ vector
    vector_norm = np.linalg.norm(vector)
    matrix_norms = np.linalg.norm(matrix, axis=1)

    denominator = vector_norm * matrix_norms
    denominator = np.where(denominator == 0, 1e-10, denominator)

    return dot_products / denominator


def detect_chords(instrumental_path: str) -> list[dict] | None:
    """Detect chords from an audio file using chromagram analysis.

    Extracts beat-synced chroma features, matches each beat against
    major and minor triad templates, and merges consecutive duplicates.

    Args:
        instrumental_path: Path to the audio file.

    Returns:
        List of {"time": float, "chord": str} dicts, or None on failure.
    """
    try:
        if not Path(instrumental_path).is_file():
            logger.error("Audio file not found: %s", instrumental_path)
            return None

        logger.info("Detecting chords for: %s", instrumental_path)

        y, sr = librosa.load(instrumental_path)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)

        _tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

        if len(beat_frames) == 0:
            logger.info("No beats detected for %s", instrumental_path)
            return []

        # Use pad=False so the number of synchronized frames aligns with
        # detected beat frames (avoids an extra trailing segment).
        beat_chroma = librosa.util.sync(chroma, beat_frames, pad=False)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)

        chord_names, chord_templates = _build_chord_templates()

        chords: list[dict] = []
        previous_chord = None

        frame_count = min(beat_chroma.shape[1], len(beat_times))

        for i in range(frame_count):
            frame = beat_chroma[:, i]
            similarities = _cosine_similarity(frame, chord_templates)
            best_chord = chord_names[int(np.argmax(similarities))]

            if best_chord != previous_chord:
                chords.append(
                    {"time": round(float(beat_times[i]), 3), "chord": best_chord}
                )
                previous_chord = best_chord

        logger.info("Detected %d chord changes in %s", len(chords), instrumental_path)
        return chords

    except Exception:
        logger.error(
            "Failed to detect chords for: %s", instrumental_path, exc_info=True
        )
        return None
