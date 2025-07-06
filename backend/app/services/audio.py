import logging
import os
import threading
import time
from pathlib import Path

import torch
from demucs.api import Separator, save_audio

from ..config import get_config

# Use relative imports
from . import file_management

logger = logging.getLogger(__name__)


class StopProcessingError(Exception):
    """Custom exception raised when processing is stopped by user."""


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
    if status_callback is None:
        status_callback = lambda msg: logger.info(msg)

    if stop_event is None:
        stop_event = threading.Event()

    try:
        # First check if CUDA is available
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
            status_callback(
                "Looking for CUDA: No GPU detected. Using CPU for processing."
            )

        # --- Define the Progress Callback ---
        last_update_time = 0

        def _demucs_progress_callback(data):
            if stop_event and stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")
            nonlocal last_update_time
            current_time = time.time()
            if current_time - last_update_time < 0.5 and data["state"] != "end":
                return
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
                status_msg = (
                    f"Separating: Model {model_idx + 1}/{models_count} "
                    f"(Overall {progress_percent:.1f}%)"
                )
                if status_callback:
                    status_callback(status_msg)
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
            logger.info(device_msg)
            if status_callback:
                status_callback(device_msg)

            # --- Initialization ---
            config = get_config()
            model_name = config.DEFAULT_MODEL
            init_msg = (
                f"Initializing Demucs (Model: {model_name}, Device: {device_str})..."
            )
            logger.info(init_msg)
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
            logger.info(format_msg)
            if status_callback:
                status_callback(format_msg)

            if stop_event and stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")

            # --- Separation (This is the long part) ---
            loading_msg = f"Loading audio file: {input_path.name}..."
            logger.info(loading_msg)
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
            logger.info(sep_msg)
            if status_callback:
                status_callback(sep_msg)

            # --- Calculate Instrumental ---
            instr_msg = "Calculating instrumental track..."
            logger.info(instr_msg)
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
                config = get_config()
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
                logger.info(vocal_msg)
                if status_callback:
                    status_callback(vocal_msg)
                logger.info(
                    f"[AUDIO DEBUG] Attempting to save vocals to: {vocals_path}"
                )
                save_audio(vocals_tensor, str(vocals_path), **save_kwargs)
                logger.info(f"[AUDIO DEBUG] Saved vocals to: {vocals_path}")
            else:
                warning_msg = "** Warning: Vocals stem not found in model output. **"
                logger.warning(warning_msg)
                if status_callback:
                    status_callback(warning_msg)

            if stop_event and stop_event.is_set():
                raise StopProcessingError("Processing stopped by user")

            # --- Save Instrumental ---
            instr_save_msg = f"Saving instrumental ({output_format_str})..."
            logger.info(instr_save_msg)
            if status_callback:
                status_callback(instr_save_msg)

            logger.info(
                f"[AUDIO DEBUG] Attempting to save instrumental to: {instrumental_path}"
            )
            try:
                save_audio(instrumental_tensor, str(instrumental_path), **save_kwargs)
                logger.info(f"[AUDIO DEBUG] Saved instrumental to: {instrumental_path}")
            except Exception as e:
                logger.error(
                    f"[AUDIO DEBUG] Exception occurred while saving audio: {e}"
                )
                if status_callback:
                    status_callback(f"** Error during separation: {e} **")
                raise

            complete_msg = f"Processing complete for {input_path.name}!"
            logger.info(complete_msg)
            if status_callback:
                status_callback(complete_msg)
            return True

        except StopProcessingError:
            raise  # Re-raise
        except Exception as e:
            logger.error(
                f"Error during separation for %s: %s", input_path.name, e, exc_info=True
            )
            if status_callback:
                status_callback(f"** Error during separation: {e} **")
            raise
    except Exception as e:
        status_callback(f"Error during separation: {str(e)}")
        return False
