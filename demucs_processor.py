# demucs_processor.py
"""Handles audio separation using the Demucs API - Reverted State."""

import sys
import traceback
from pathlib import Path
import torch

try:
    from demucs.api import Separator, save_audio
    DEMUCS_AVAILABLE = True
except ImportError as e:
    print(f"Error importing Demucs or PyTorch: {e}", file=sys.stderr)
    # ... (rest of error handling) ...
    DEMUCS_AVAILABLE = False
except Exception as e:
    print(f"An unexpected error occurred during Demucs import: {e}", file=sys.stderr)
    # ... (rest of error handling) ...
    DEMUCS_AVAILABLE = False

import config
import file_manager

def is_available():
    """Checks if Demucs was imported successfully."""
    return DEMUCS_AVAILABLE

def separate_audio(input_path: Path, song_dir: Path, status_callback): # Simpler signature
    """
    Separates the audio file into vocals and instrumental tracks (WAV format).
    """
    if not is_available():
        status_callback("** Error: Demucs is not available! Check installation. **")
        return False

    try:
        # --- Determine Device (Hardcoded logic) ---
        actual_device = 'cuda' if torch.cuda.is_available() else 'cpu'
        status_callback(f"Using device: {actual_device}")

        # --- Initialization (Hardcoded model) ---
        model_name = config.DEFAULT_MODEL
        status_callback(f"Initializing Demucs (Model: {model_name}, Device: {actual_device})...")
        separator = Separator(model=model_name, device=actual_device)

        # --- Separation ---
        status_callback(f"Loading and separating: {input_path.name}...")
        _, separated = separator.separate_audio_file(str(input_path)) # Ignore origin

        # --- Calculate Instrumental ---
        status_callback("Calculating instrumental track...")
        instrumental_tensor = None
        instrumental_stems = [s_name for s_name in separated if s_name != 'vocals']
        if not instrumental_stems:
            status_callback("** Error: No non-vocal stems found! **")
            return False
        first_stem_name = instrumental_stems[0]
        instrumental_tensor = torch.zeros_like(separated[first_stem_name])
        for stem_name in instrumental_stems:
            instrumental_tensor += separated[stem_name]

        # --- Prepare for Saving (Fixed WAV format) ---
        vocals_path = file_manager.get_vocals_path(song_dir) # Gets path with .wav
        instrumental_path = file_manager.get_instrumental_path(song_dir) # Gets path with .wav
        vocals_tensor = separated.get('vocals')

        # --- Prepare save_audio kwargs for standard WAV ---
        save_kwargs = {'samplerate': separator.samplerate}
        # Add default WAV settings if needed by save_audio (often unnecessary for basic int16)
        # save_kwargs['bits_per_sample'] = 16
        # save_kwargs['as_float'] = False

        # --- Save Vocals ---
        if vocals_tensor is not None:
            status_callback(f"Saving {config.VOCALS_FILENAME}...")
            save_audio(vocals_tensor, str(vocals_path), **save_kwargs)
        else:
            status_callback("** Warning: Vocals stem not found in model output. **")

        # --- Save Instrumental ---
        status_callback(f"Saving {config.INSTRUMENTAL_FILENAME}...")
        save_audio(instrumental_tensor, str(instrumental_path), **save_kwargs)

        status_callback(f"Separation complete for {input_path.name}!")
        return True # Indicate success

    except Exception as e:
        print(f"Error during separation for {input_path.name}: {e}", file=sys.stderr)
        traceback.print_exc()
        status_callback(f"** Error during separation: {e} **")
        return False # Indicate failure