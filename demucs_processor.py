# demucs_processor.py
"""Handles audio separation using the Demucs API"""

import sys
import traceback
from pathlib import Path
import time
import torch

import file_manager
import config

try:
    from demucs.api import Separator, save_audio

    DEMUCS_AVAILABLE = True
except ImportError as e:
    print(f"Error importing Demucs or PyTorch: {e}", file=sys.stderr)
    DEMUCS_AVAILABLE = False
except Exception as e:
    print(f"An unexpected error occurred during Demucs import: {e}", file=sys.stderr)
    traceback.print_exc()
    DEMUCS_AVAILABLE = False

def is_available():
    """Checks if Demucs was imported successfully."""
    return DEMUCS_AVAILABLE


def separate_audio(input_path: Path, song_dir: Path, status_callback):
    """
    Separates the audio file into vocals and instrumental tracks,
    matching the input file format and reporting progress.
    """
    if not is_available():
        status_callback("** Error: Demucs is not available! Check installation. **")
        return False

    # --- Define the Progress Callback ---
    # This function will be called by the Demucs Separator during processing
    last_update_time = 0

    def _demucs_progress_callback(data):
        nonlocal last_update_time
        current_time = time.time()
        # Throttle GUI updates slightly (e.g., max once per 0.5 seconds)
        # to avoid overwhelming the event queue, adjust as needed.
        if current_time - last_update_time < 0.5 and data["state"] != "end":
            return  # Skip update if too frequent, unless it's the final segment update

        total_segments = data["audio_length"]
        processed_segments = data[
            "segment_offset"
        ]
        model_idx = data["model_idx_in_bag"]
        models_count = data[
            "models"
        ]

        progress_current_model = (
            (processed_segments / total_segments) if total_segments > 0 else 0
        )
        overall_progress = (
            ((model_idx + progress_current_model) / models_count)
            if models_count > 0
            else 0
        )

        if data["state"] == "end":
            progress_percent = overall_progress * 100
            # Example: "Separating: Model 2/4 (Overall 35.7%)"
            status_msg = (
                f"Separating: Model {model_idx + 1}/{models_count} "
                f"(Overall {progress_percent:.1f}%)"
            )
            status_callback(status_msg)  # Use the main callback to update GUI
            last_update_time = current_time

    try:
        # --- Determine Device ---
        actual_device = "cuda" if torch.cuda.is_available() else "cpu"
        status_callback(f"Using device: {actual_device}")

        # --- Initialization ---
        model_name = config.DEFAULT_MODEL
        status_callback(
            f"Initializing Demucs (Model: {model_name}, Device: {actual_device})..."
        )
        # Pass the progress callback function to the Separator
        separator = Separator(
            model=model_name, device=actual_device, callback=_demucs_progress_callback
        )

        # --- Determine Output Format ---
        input_extension = input_path.suffix.lower()
        output_extension = (
            input_extension if input_extension in [".wav", ".mp3"] else ".wav"
        )
        output_format_str = "MP3" if output_extension == ".mp3" else "WAV"
        status_callback(f"Input: {input_extension}, Output: {output_format_str}")

        # --- Separation (This is the long part) ---
        status_callback(
            f"Loading audio file: {input_path.name}..."
        )  # Add loading step msg
        # The _demucs_progress_callback will be called during this next line
        _, separated = separator.separate_audio_file(str(input_path))
        status_callback("Separation models finished.")  # Signal end of core separation

        # --- Calculate Instrumental ---
        status_callback("Calculating instrumental track...")
        instrumental_tensor = None
        instrumental_stems = [s_name for s_name in separated if s_name != "vocals"]
        if not instrumental_stems:
            status_callback("** Error: No non-vocal stems found! **")
            return False
        first_stem_name = instrumental_stems[0]
        instrumental_tensor = torch.zeros_like(separated[first_stem_name])
        for stem_name in instrumental_stems:
            instrumental_tensor += separated[stem_name]

        # --- Prepare for Saving ---
        vocals_path = file_manager.get_vocals_path_stem(song_dir).with_suffix(
            output_extension
        )
        instrumental_path = file_manager.get_instrumental_path_stem(
            song_dir
        ).with_suffix(output_extension)
        vocals_tensor = separated.get("vocals")

        save_kwargs = {"samplerate": separator.samplerate}
        if output_extension == ".mp3":
            save_kwargs["bitrate"] = int(config.DEFAULT_MP3_BITRATE)
            save_kwargs["preset"] = 2
        elif output_extension == ".wav":
            save_kwargs["bits_per_sample"] = 16
            save_kwargs["as_float"] = False

        # --- Save Vocals ---
        if vocals_tensor is not None:
            status_callback(f"Saving vocals ({output_format_str})...")
            save_audio(vocals_tensor, str(vocals_path), **save_kwargs)
        else:
            status_callback("** Warning: Vocals stem not found in model output. **")

        # --- Save Instrumental ---
        status_callback(f"Saving instrumental ({output_format_str})...")
        save_audio(instrumental_tensor, str(instrumental_path), **save_kwargs)

        status_callback(
            f"Processing complete for {input_path.name}!"
        )  # Change final message
        return True

    except Exception as e:
        print(f"Error during separation for {input_path.name}: {e}", file=sys.stderr)
        traceback.print_exc()
        status_callback(f"** Error during separation: {e} **")
        return False
