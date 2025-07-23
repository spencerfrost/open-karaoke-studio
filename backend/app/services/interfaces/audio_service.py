# pylint: disable=unnecessary-ellipsis
"""
Audio Service Interface for dependency injection and testing
"""

from pathlib import Path
from threading import Event
from typing import Callable, Optional, Protocol, runtime_checkable


@runtime_checkable
class AudioServiceInterface(Protocol):
    """Interface for audio processing services"""

    def separate_audio(
        self,
        input_path: Path,
        song_dir: Path,
        status_callback: Callable[[str], None],
        stop_event: Optional[Event] = None,
    ) -> bool:
        """
        Separates the audio file into vocals and instrumental tracks.

        Args:
            input_path: Path to the input audio file
            song_dir: Path to the directory where processed files will be saved
            status_callback: Function to call with status updates
            stop_event: Threading event to check for stop requests

        Returns:
            True on success, False on failure

        Raises:
            StopProcessingError: If processing is stopped by the user
            Exception: For other errors during processing
        """
        ...
