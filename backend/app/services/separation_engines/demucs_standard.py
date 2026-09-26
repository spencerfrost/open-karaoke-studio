"""
Experiment 1: Baseline Demucs Separation Engine

This is the standard 2/4-stem Demucs separation - the current production approach.
Separates audio into vocals and instrumental using Demucs only.
"""

import logging
import threading
from pathlib import Path
from typing import Callable, Optional, Tuple

from app.services.audio import separate_audio as demucs_separate_audio

logger = logging.getLogger(__name__)


def separate_with_demucs(
    input_path: Path,
    song_dir: Path,
    status_callback: Callable[[str], None],
    stop_event: Optional[threading.Event] = None,
) -> bool:
    """
    Baseline separation using standard Demucs approach.

    This engine produces:
    - vocals.mp3: Lead + backing vocals combined
    - instrumental.mp3: All non-vocal stems (bass, drums, other)

    Args:
        input_path: Path to the input audio file
        song_dir: Path to the directory where processed files will be saved
        status_callback: Function to call with status updates
        stop_event: A threading.Event to check for stop requests

    Returns:
        True if separation succeeded, False otherwise.
    """
    logger.info("Starting Demucs Standard separation for: %s", input_path.name)
    status_callback("Engine: Demucs Standard (Baseline)")

    # Delegate to the existing separate_audio implementation
    success = demucs_separate_audio(
        input_path=input_path,
        song_dir=song_dir,
        status_callback=status_callback,
        stop_event=stop_event,
    )

    if success:
        logger.info("Demucs Standard separation completed successfully")
    else:
        logger.error("Demucs Standard separation failed")

    return success
