# demucs_processor.py
"""Handles audio separation using the Demucs API."""

import sys
import traceback
from pathlib import Path
import torch  # Keep torch import here for tensor math

# Attempt to import Demucs components
try:
    from demucs.api import Separator, save_audio

    DEMUCS_AVAILABLE = True
except ImportError as e:
    print(f"Error importing Demucs or PyTorch: {e}", file=sys.stderr)
    print(
        "Please ensure Demucs and PyTorch are installed correctly in your venv.",
        file=sys.stderr,
    )
    print(
        "Try running: pip install git+https://github.com/adefossez/demucs",
        file=sys.stderr,
    )
    DEMUCS_AVAILABLE = False
except Exception as e:
    print(f"An unexpected error occurred during Demucs import: {e}", file=sys.stderr)
    traceback.print_exc()
    DEMUCS_AVAILABLE = False

import config  # Import settings
import file_manager  # To get save paths


def is_available():
    """Checks if Demucs was imported successfully."""
    return DEMUCS_AVAILABLE


def separate_audio(input_path: Path, song_dir: Path, status_callback):
    """
    Separates the audio file into vocals and instrumental tracks.

    Args:
        input_path: Path to the input audio file.
        song_dir: The directory dedicated to this song's files.
        status_callback: A function to call with status updates (e.g., lambda msg: print(msg)).
    """
    if not is_available():
        status_callback("** Error: Demucs is not available! Check installation. **")
        return False

    try:
        # --- Initialization ---
        device = "cuda" if torch.cuda.is_available() else "cpu"
        status_callback(
            f"Initializing Demucs (Model: {config.DEFAULT_MODEL}, Device: {device})..."
        )
        separator = Separator(model=config.DEFAULT_MODEL, device=device)

        # --- Separation ---
        status_callback(f"Loading and separating: {input_path.name}...")
        origin, separated = separator.separate_audio_file(str(input_path))
        # 'separated' is a dict like {'vocals': tensor, 'drums': tensor, 'bass': tensor, 'other': tensor}

        # --- Calculate Instrumental ---
        status_callback("Calculating instrumental track...")
        instrumental_tensor = None
        # Sum all stems EXCEPT vocals
        instrumental_stems = [
            stem_name for stem_name in separated if stem_name != "vocals"
        ]

        if not instrumental_stems:
            status_callback("** Error: No non-vocal stems found in model output! **")
            return False  # Cannot create instrumental

        # Initialize instrumental tensor with the shape of the first non-vocal stem
        first_stem_name = instrumental_stems[0]
        instrumental_tensor = torch.zeros_like(separated[first_stem_name])

        for stem_name in instrumental_stems:
            instrumental_tensor += separated[stem_name]

        # --- Save Files ---
        vocals_path = file_manager.get_vocals_path(song_dir)
        instrumental_path = file_manager.get_instrumental_path(song_dir)
        vocals_tensor = separated.get("vocals")

        # Save Vocals
        if vocals_tensor is not None:
            status_callback(f"Saving vocals to {config.VOCALS_FILENAME}...")
            save_audio(vocals_tensor, str(vocals_path), separator.samplerate)
        else:
            status_callback("** Warning: Vocals stem not found in model output. **")

        # Save Instrumental
        status_callback(f"Saving instrumental to {config.INSTRUMENTAL_FILENAME}...")
        save_audio(instrumental_tensor, str(instrumental_path), separator.samplerate)

        status_callback(f"Separation complete for {input_path.name}!")
        return True  # Indicate success

    except Exception as e:
        print(f"Error during separation for {input_path.name}: {e}", file=sys.stderr)
        traceback.print_exc()  # Print full traceback to console
        status_callback(f"** Error during separation: {e} **")
        return False  # Indicate failure
