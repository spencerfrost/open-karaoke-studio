import shutil
import sys
import traceback
from pathlib import Path
import time
import torch

import file_management
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

class StopProcessingError(Exception):
    """Custom exception raised when processing is stopped by user."""

    pass

def separate_audio(input_path: Path, song_dir: Path, status_callback, stop_event):
    """
    Separates the audio file into vocals and instrumental tracks,
    matching the input file format and reporting progress.

    Args:
        input_path: Path to the input audio file.
        song_dir: Path to the directory where processed files will be saved.
        status_callback:  (Removed - not used in backend)
        stop_event:  A threading.Event to check for stop requests.

    Returns:
        True on success, False on failure.  (But now, exceptions are preferred for errors)

    Raises:
        StopProcessingError: If processing is stopped by the user.
        Exception: For other errors during processing.
    """
    if not is_available():
        raise Exception("Demucs is not available! Check installation.")

    # --- Define the Progress Callback ---
    # This function will be called by the Demucs Separator during processing
    last_update_time = 0

    def _demucs_progress_callback(data):
        # Check if stop was requested
        if stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")
        nonlocal last_update_time
        current_time = time.time()
        # Throttle updates slightly (e.g., max once per 0.5 seconds)
        if current_time - last_update_time < 0.5 and data["state"] != "end":
            return  # Skip update if too frequent

        # (Progress reporting removed - not relevant for backend)

    try:
        # --- Determine Device ---
        if stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        actual_device = "cuda" if torch.cuda.is_available() else "cpu"
        if actual_device == "cuda":
            device_name = torch.cuda.get_device_name(0)  # Get GPU name
            device_str = f"cuda:0 ({device_name})"
        else:
            device_str = "cpu"
        print(f"Using device: {device_str}")  # Log to console instead of GUI

        # --- Initialization ---
        model_name = config.DEFAULT_MODEL
        print(f"Initializing Demucs (Model: {model_name}, Device: {device_str})...")
        try:
            separator = Separator(
                model=model_name,
                device=actual_device,
                callback=_demucs_progress_callback,
            )
        except (torch.cuda.CudaError, RuntimeError) as e:
            raise Exception(f"Error initializing Demucs: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error during Demucs init: {e}")

        # --- Determine Output Format ---
        input_extension = input_path.suffix.lower()
        output_extension = (
            input_extension if input_extension in [".wav", ".mp3"] else ".wav"
        )
        output_format_str = "MP3" if output_extension == ".mp3" else "WAV"
        print(f"Input: {input_extension}, Output: {output_format_str}")

        if stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # --- Separation (This is the long part) ---
        print(f"Loading audio file: {input_path.name}...")  # Log loading
        try:
            _, separated = separator.separate_audio_file(str(input_path))
            if stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")
        except StopProcessingError:
            raise
        except (torch.cuda.CudaError, RuntimeError) as e:
            raise Exception(f"Error during separation: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error during separation: {e}")
        print("Separation models finished.")

        # --- Calculate Instrumental ---
        print("Calculating instrumental track...")
        instrumental_tensor = None
        instrumental_stems = [s_name for s_name in separated if s_name != "vocals"]
        if not instrumental_stems:
            raise Exception("No non-vocal stems found!")
        first_stem_name = instrumental_stems[0]
        if stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        instrumental_tensor = torch.zeros_like(separated[first_stem_name])
        for stem_name in instrumental_stems:
            instrumental_tensor += separated[stem_name]

        # --- Prepare for Saving ---
        vocals_path = file_management.get_vocals_path_stem(song_dir).with_suffix(
            output_extension
        )
        instrumental_path = file_management.get_instrumental_path_stem(
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

        if stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # --- Save Vocals ---
        if vocals_tensor is not None:
            print(f"Saving vocals ({output_format_str})...")
            save_audio(vocals_tensor, str(vocals_path), **save_kwargs)
        else:
            print("** Warning: Vocals stem not found in model output. **")

        if stop_event.is_set():
            raise StopProcessingError("Processing stopped by user")

        # --- Save Instrumental ---
        print(f"Saving instrumental ({output_format_str})...")
        save_audio(instrumental_tensor, str(instrumental_path), **save_kwargs)

        print(f"Processing complete for {input_path.name}!")
        return True

    except StopProcessingError:
        raise  # Re-raise
    except Exception as e:
        print(f"Error during separation for {input_path.name}: {e}", file=sys.stderr)
        traceback.print_exc()
        raise