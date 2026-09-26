"""
Experiment 2: Karaoke-First Roformer Separation Engine

Single-pass separation using the Mel-Band Roformer with ViperX model.
This is the state-of-the-art model specifically trained for karaoke separation.

Model: mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt
Pros: Fastest approach, clean vocal extraction with minimal artifacts
Cons: High peak VRAM usage
"""

import logging
import threading
from pathlib import Path
from typing import Callable, Optional, Tuple

from audio_separator.separator import Separator
from app.services import file_management

logger = logging.getLogger(__name__)


def separate_with_roformer(
    input_path: Path,
    song_dir: Path,
    status_callback: Callable[[str], None],
    stop_event: Optional[threading.Event] = None,
) -> bool:
    """
    Single-pass separation using Roformer karaoke model.

    This engine produces:
    - vocals.mp3: Lead vocals only (backing vocals removed)
    - instrumental.mp3: Instrumental + backing vocals

    Args:
        input_path: Path to the input audio file
        song_dir: Path to the directory where processed files will be saved
        status_callback: Function to call with status updates
        stop_event: A threading.Event to check for stop requests

    Returns:
        True if separation succeeded, False otherwise.
    """
    logger.info("Starting Roformer Karaoke-First separation for: %s", input_path.name)
    status_callback("Engine: Roformer ViperX (Karaoke-First)")

    try:
        # Check for stop request
        if stop_event and stop_event.is_set():
            from app.services.audio import StopProcessingError
            raise StopProcessingError("Processing stopped by user")

        # Initialize audio-separator with song_dir as output directory
        status_callback("Progress: 35% - Initializing Roformer model...")
        separator = Separator(
            output_dir=str(song_dir),
            output_format="mp3",
        )

        # Load the Mel-Band Roformer ViperX model
        # This model auto-downloads on first use
        model_name = "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt"
        status_callback(f"Loading model: {model_name}")
        separator.load_model(model_filename=model_name)

        # Check for stop request
        if stop_event and stop_event.is_set():
            from app.services.audio import StopProcessingError
            raise StopProcessingError("Processing stopped by user")

        # Perform separation
        status_callback("Progress: 50% - Separating audio with Roformer...")
        logger.info("Running Roformer separation on: %s", input_path)

        output_files = separator.separate(str(input_path))
        logger.info("Roformer produced output files: %s", output_files)

        # Check for stop request
        if stop_event and stop_event.is_set():
            from app.services.audio import StopProcessingError
            raise StopProcessingError("Processing stopped by user")

        # The Roformer karaoke model typically outputs:
        # - (Instrumental) - instrumental + backing vocals
        # - (Vocals) - lead vocals only
        # We need to rename these to match our expected names

        status_callback("Progress: 70% - Organizing output files...")

        # Find the generated files
        # Note: audio-separator returns relative filenames, actual files are in song_dir
        vocals_file = None
        instrumental_file = None

        for file_path in output_files:
            file_obj = Path(file_path)
            # If the path is relative, it's in the output directory (song_dir)
            if not file_obj.is_absolute():
                file_obj = song_dir / file_obj.name

            if "(Vocals)" in file_obj.name:
                vocals_file = file_obj
            elif "(Instrumental)" in file_obj.name:
                instrumental_file = file_obj

        if not vocals_file or not instrumental_file:
            raise Exception(f"Expected output files not found. Got: {output_files}")

        logger.info("Found vocals file: %s", vocals_file)
        logger.info("Found instrumental file: %s", instrumental_file)

        # Move to standard names in song_dir
        vocals_path = file_management.get_vocals_path_stem(song_dir).with_suffix(".mp3")
        instrumental_path = file_management.get_instrumental_path_stem(song_dir).with_suffix(".mp3")

        # Use shutil.move instead of rename to handle cross-filesystem moves
        import shutil
        shutil.move(str(vocals_file), str(vocals_path))
        shutil.move(str(instrumental_file), str(instrumental_path))

        logger.info("Renamed outputs to: %s, %s", vocals_path, instrumental_path)
        status_callback("Progress: 85% - Output files organized")

        status_callback(f"Roformer separation complete for {input_path.name}!")
        logger.info("Roformer Karaoke-First separation completed successfully")

        return True

    except Exception as e:
        logger.error("Roformer separation failed: %s", e, exc_info=True)
        status_callback(f"** Error during Roformer separation: {e} **")
        return False
