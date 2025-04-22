import os
import sys
import traceback
from pathlib import Path
import time

# Use relative imports
from . import file_management
from . import config

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

def separate_audio(input_path: Path, song_dir: Path, status_callback, stop_event=None):
    """
    Separates the audio file into vocals and instrumental tracks,
    matching the input file format and reporting progress.

    Args:
        input_path: Path to the input audio file.
        song_dir: Path to the directory where processed files will be saved.
        status_callback: Function to call with status updates.
        stop_event: A threading.Event to check for stop requests. Can be None.

    Returns:
        True on success, False on failure.

    Raises:
        StopProcessingError: If processing is stopped by the user.
        Exception: For other errors during processing.
    """
    if not is_available():
        raise Exception("Demucs is not available! Check installation.")

    if status_callback is None:
        def status_callback(msg): print(msg)

    if stop_event is None:
        import threading
        stop_event = threading.Event()

    try:
        # First check if CUDA is available
        import torch
        use_cuda = torch.cuda.is_available()

        if use_cuda:
            try:
                device_name = torch.cuda.get_device_name(0)
                status_callback(f"Looking for CUDA: Found GPU: {device_name}")
            except RuntimeError as e:
                status_callback(f"CUDA initialization error: {e}")
                status_callback("Falling back to CPU processing...")
                # Force CPU mode
                os.environ["CUDA_VISIBLE_DEVICES"] = ""
                use_cuda = False
        else:
            status_callback("Looking for CUDA: No GPU detected. Using CPU for processing.")

        # --- Define the Progress Callback ---
        # This function will be called by the Demucs Separator during processing
        last_update_time = 0

        def _demucs_progress_callback(data):
            # Check if stop was requested
            if stop_event and stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")

            nonlocal last_update_time
            current_time = time.time()
            # Throttle updates slightly (e.g., max once per 0.5 seconds)
            if current_time - last_update_time < 0.5 and data["state"] != "end":
                return  # Skip update if too frequent

            total_segments = data.get("audio_length", 0)
            processed_segments = data.get("segment_offset", 0)
            model_idx = data.get("model_idx_in_bag", 0)
            models_count = data.get("models", 1)

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

                if status_callback:
                    status_callback(status_msg)  # Use the callback if provided

                last_update_time = current_time

        try:
            # --- Determine Device ---
            if stop_event and stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")

            actual_device = "cuda" if torch.cuda.is_available() else "cpu"
            if actual_device == "cuda":
                device_name = torch.cuda.get_device_name(0)  # Get GPU name
                device_str = f"cuda:0 ({device_name})"
            else:
                device_str = "cpu"
            
            device_msg = f"Using device: {device_str}"
            print(device_msg)
            if status_callback:
                status_callback(device_msg)

            # --- Initialization ---
            model_name = config.DEFAULT_MODEL
            init_msg = f"Initializing Demucs (Model: {model_name}, Device: {device_str})..."
            print(init_msg)
            if status_callback:
                status_callback(init_msg)

            try:
                separator = Separator(
                    model=model_name,
                    device=actual_device,
                    callback=_demucs_progress_callback,
                )
            except (torch.cuda.CudaError, RuntimeError) as e:
                error_msg = f"Error initializing Demucs: {e}"
                if status_callback:
                    status_callback(error_msg)
                raise Exception(error_msg)
            except Exception as e:
                error_msg = f"Unexpected error during Demucs init: {e}"
                if status_callback:
                    status_callback(error_msg)
                raise Exception(error_msg)

            # --- Determine Output Format ---
            input_extension = input_path.suffix.lower()
            output_extension = (
                input_extension if input_extension in [".wav", ".mp3"] else ".wav"
            )
            output_format_str = "MP3" if output_extension == ".mp3" else "WAV"
            format_msg = f"Input: {input_extension}, Output: {output_format_str}"
            print(format_msg)
            if status_callback:
                status_callback(format_msg)

            if stop_event and stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")

            # --- Separation (This is the long part) ---
            loading_msg = f"Loading audio file: {input_path.name}..."
            print(loading_msg)
            if status_callback:
                status_callback(loading_msg)

            try:
                _, separated = separator.separate_audio_file(str(input_path))
                if stop_event and stop_event.is_set():
                    raise StopProcessingError("Processing stopped by user")
            except StopProcessingError:
                raise
            except (torch.cuda.CudaError, RuntimeError) as e:
                error_msg = f"Error during separation: {e}"
                if status_callback:
                    status_callback(error_msg)
                raise Exception(error_msg)
            except Exception as e:
                error_msg = f"Unexpected error during separation: {e}"
                if status_callback:
                    status_callback(error_msg)
                raise Exception(error_msg)

            sep_msg = "Separation models finished."
            print(sep_msg)
            if status_callback:
                status_callback(sep_msg)

            # --- Calculate Instrumental ---
            instr_msg = "Calculating instrumental track..."
            print(instr_msg)
            if status_callback:
                status_callback(instr_msg)

            instrumental_tensor = None
            instrumental_stems = [s_name for s_name in separated if s_name != "vocals"]
            if not instrumental_stems:
                error_msg = "No non-vocal stems found!"
                if status_callback:
                    status_callback(error_msg)
                raise Exception(error_msg)

            first_stem_name = instrumental_stems[0]
            if stop_event and stop_event.is_set():
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

            if stop_event and stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")

            # --- Save Vocals ---
            if vocals_tensor is not None:
                vocal_msg = f"Saving vocals ({output_format_str})..."
                print(vocal_msg)
                if status_callback:
                    status_callback(vocal_msg)
                save_audio(vocals_tensor, str(vocals_path), **save_kwargs)
            else:
                warning_msg = "** Warning: Vocals stem not found in model output. **"
                print(warning_msg)
                if status_callback:
                    status_callback(warning_msg)

            if stop_event and stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")

            # --- Save Instrumental ---
            instr_save_msg = f"Saving instrumental ({output_format_str})..."
            print(instr_save_msg)
            if status_callback:
                status_callback(instr_save_msg)
            save_audio(instrumental_tensor, str(instrumental_path), **save_kwargs)

            complete_msg = f"Processing complete for {input_path.name}!"
            print(complete_msg)
            if status_callback:
                status_callback(complete_msg)
            return True

        except StopProcessingError:
            raise  # Re-raise
        except Exception as e:
            print(f"Error during separation for {input_path.name}: {e}", file=sys.stderr)
            traceback.print_exc()
            if status_callback:
                status_callback(f"** Error during separation: {e} **")
            raise

        return True

    except Exception as e:
        status_callback(f"Error during separation: {str(e)}")
        return False